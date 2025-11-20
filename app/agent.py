# app/agent.py
import json
import re
from typing import List

from .prompts import TRIAGE_AGENT_PROMPT
from .models import Ticket, TriageResult
from .kb import KnowledgeBase
from .config import CATEGORY_TEAM_MAP, PRIORITY_KEYWORDS, GROQ_API_KEY, GROQ_MODEL
from .utils import build_triage_prompt, logger, rule_based_category, rule_based_priority
from groq import Groq

client = Groq(api_key=GROQ_API_KEY)
kb = KnowledgeBase()



async def call_openai_chat(prompt: str) -> str:
    """
    Minimal OpenAI chat completion call using the openai client.
    Note: this call is synchronous/blocking under the hood (openai.ChatCompletion.create),
    but it's wrapped in an async function for API consistency. For production convert to
    an async HTTP client or use openai's async client if available.
    """

    if not GROQ_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")

    
    logger.info("Starting triage for query=%s", (prompt or "<no-subject>"))
    gen_res = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=400,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "Triage_Result",
                "schema": TriageResult.model_json_schema()
            }
        }, 
    )
    resp = TriageResult.model_validate(json.loads(gen_res.choices[0].message.content))
    resp= resp.model_dump()

    # The response structure: resp.choices[0].message.content
    try:
        content = resp.choices[0].message.content
        logger.debug("LLM response received (preview): %s", (content[:200] + "...") if content and len(content) > 200 else content)
    except Exception:
        logger.debug("LLM response received but could not extract preview.")
        content = resp
    return content


async def llm_triage(ticket: Ticket, kb_entries: List) -> dict:
    """
    Build a prompt and call the LLM. If no OPENAI_API_KEY, fall back to rules.
    Returns a dict with the keys needed to construct a TriageResult.
    """
    logger.info("Starting triage for ticket subject=%s", (ticket.subject or "<no-subject>"))

    # Fallback deterministic behavior when no API key is available:
    if not GROQ_API_KEY:
        logger.info("GROQ_API_KEY not configured — using rule-based triage")
        
        category = rule_based_category(ticket)
        priority = rule_based_priority(ticket)
        matched_ids = [e.id for e in kb_entries]
        suggested_team = CATEGORY_TEAM_MAP.get(category, "support-general")
        suggested_response = (
            f"Hi — thanks for reporting. We've classified this as {category}. "
            f"Our {suggested_team} will follow up."
        )
        logger.debug("Rule-based triage result category=%s priority=%s matched_kb=%s", category, priority, matched_ids)
        
        return {
            "category": category,
            "priority": priority,
            "suggested_team": suggested_team,
            "matched_kb_article_ids": matched_ids,
            "suggested_response": suggested_response,
            "needs_human_review": True,
        }

    # Build the KB text (small; safe for 10-15 KB entries)
    kb_text = "\n\n".join([f"[{e.id}] {e.title}: {e.content}" for e in kb_entries])
    prompt = build_triage_prompt(ticket, kb_text)
    logger.debug("Built triage prompt length=%d kb_entries=%d", len(prompt), len(kb_entries))
    
    try:
        logger.info("Calling LLM for triage")
        raw = await call_openai_chat(prompt)
        logger.debug("Raw LLM output length=%d", len(raw) if raw else 0)
        
        # Extract the first JSON object from the model output
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            raise ValueError("No JSON found in LLM output.")
        parsed = json.loads(m.group(0))
        logger.debug("Parsed LLM JSON: %s", parsed)

        # Ensure expected keys and types exist
        parsed["matched_kb_article_ids"] = parsed.get("matched_kb_article_ids", [])
        parsed["category"] = parsed.get("category", "other")
        parsed["priority"] = parsed.get("priority", "medium")
        parsed["suggested_team"] = parsed.get(
            "suggested_team", CATEGORY_TEAM_MAP.get(parsed.get("category", "other"), "support-general")
        )
        parsed["suggested_response"] = parsed.get("suggested_response", "We will investigate and get back to you.")
        parsed["needs_human_review"] = bool(parsed.get("needs_human_review", True))

        logger.info("LLM triage completed category=%s priority=%s needs_human_review=%s",
                    parsed["category"], parsed["priority"], parsed["needs_human_review"])
        
        return parsed

    except Exception as exc:
        # On any LLM failure, fallback to rules and log the error
        logger.exception("LLM triage failed, falling back to rule-based triage: %s", exc)
        category = rule_based_category(ticket)
        priority = rule_based_priority(ticket)
        matched_ids = [e.id for e in kb_entries]
        suggested_team = CATEGORY_TEAM_MAP.get(category, "support-general")
        suggested_response = (
            f"Hi — thanks for reporting. We've classified this as {category}. "
            f"Our {suggested_team} will follow up."
        )
        logger.debug("Fallback rule-based triage result category=%s priority=%s matched_kb=%s", category, priority, matched_ids)
        return {
            "category": category,
            "priority": priority,
            "suggested_team": suggested_team,
            "matched_kb_article_ids": matched_ids,
            "suggested_response": suggested_response,
            "needs_human_review": True,
        }


async def triage_ticket(ticket: Ticket) -> TriageResult:
    """
    High-level triage flow:
    1. Retrieve top-k KB entries for the ticket.
    2. Ask the LLM (or fallback to rules) for structured triage output.
    3. Return a validated TriageResult object.
    """
    logger.info("triage_ticket invoked for ticket subject=%s", (ticket.subject or "<no-subject>"))
    
    # 1) retrieve KB
    query = (ticket.subject or "") + " " + (ticket.description or "")
    logger.debug("KB query: %s", query)
    kb_entries = kb.search(query, top_k=3)
    logger.info("KB search returned %d entries", len(kb_entries))


    # 2) ask LLM or fallback
    parsed = await llm_triage(ticket, kb_entries)

    # 3) build TriageResult (ensure graceful defaults)
    suggested_team = parsed.get("suggested_team") or CATEGORY_TEAM_MAP.get(parsed.get("category"), "support-general")
    matched_ids = parsed.get("matched_kb_article_ids", [e.id for e in kb_entries])

    tr = TriageResult(
        category=parsed.get("category", "other"),
        priority=parsed.get("priority", "medium"),
        suggested_team=suggested_team,
        matched_kb_article_ids=matched_ids,
        suggested_response=parsed.get("suggested_response", "We will investigate and get back to you."),
        needs_human_review=parsed.get("needs_human_review", True),
    )
    logger.info("TriageResult ready category=%s priority=%s suggested_team=%s", tr.category, tr.priority, tr.suggested_team)
    
    return tr
