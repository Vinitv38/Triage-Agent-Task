# app/agent.py
import json
from typing import List
from .models import TriageResult
from .kb import KnowledgeBase
from .config import CATEGORY_TEAM_MAP, GROQ_API_KEY, GROQ_MODEL
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


async def llm_triage(customer_query, kb_entries: List) -> dict:
    """
    Build a prompt and call the LLM. If no OPENAI_API_KEY, fall back to rules.
    Returns a dict with the keys needed to construct a TriageResult.
    """
    logger.info("Starting triage for ticket subject: ", customer_query)

    # Fallback deterministic behavior when no API key is available:
    if not GROQ_API_KEY:
        logger.info("GROQ_API_KEY not configured — using rule-based triage")
        
        category = rule_based_category(customer_query)
        severity = rule_based_priority(customer_query)
        matched_ids = [e.id for e in kb_entries]
        is_known_issue = False
        # suggested_team = CATEGORY_TEAM_MAP.get(category, "support-general")
        suggested_next_step = (
            f"Hi — thanks for reporting. We've classified this as {category}. "
            f"Our {suggested_next_step} will follow up."
        )
        logger.debug(f"Rule-based triage result category: {category}, priority:{severity}, matched_kb: {matched_ids} ")
        
        return {
            "summary": customer_query,
            "category": severity,
            "severity": severity,
            "is_known_issue": is_known_issue,
            "matched_kb_ids": matched_ids,
            "suggested_next_step": suggested_next_step,
        }

    # Build the KB text (small; safe for 10-15 KB entries)
    kb_text = "\n\n".join([f"[{e.id}] {e.title}: {e.content}" for e in kb_entries])
    prompt = build_triage_prompt(customer_query, kb_text)
    logger.debug("Built triage prompt length=%d kb_entries=%d", len(prompt), len(kb_entries))
    
    try:
        logger.info("Calling LLM for triage")
        resp = await call_openai_chat(prompt)
        
        logger.debug("LLM output length=%d", len(resp) if resp else 0)
        
        # Extract the first JSON object from the model output
        logger.debug("resp LLM JSON: %s", resp)

        # Ensure expected keys and types exist
        resp["summary"] = resp.get("summary", "other")
        resp["category"] = resp.get("category", "other")
        resp["severity"] = resp.get("priority", "medium")
        resp["suggested_next_step"] = resp.get(
            "suggested_next_step", CATEGORY_TEAM_MAP.get(resp.get("category", "other"), "support-general")
        )
        
        logger.info("LLM triage completed category=%s priority=%s",
                    resp["category"], resp["severity"])
        print('=========================')
        print(resp)
        print('=========================')
        return resp

    except Exception as exc:
        # On any LLM failure, fallback to rules and log the error
        category = rule_based_category(customer_query)
        severity = rule_based_priority(customer_query)
        matched_ids = [e.id for e in kb_entries]
        is_known_issue = False
        suggested_next_step = (
            f"Hi — thanks for reporting. We've classified this as {category}. "
            f"Our {category} team will follow up."
        )
        logger.debug("Fallback rule-based triage result category=%s priority=%s matched_kb=%s", category, severity, matched_ids)
        return {
            "category": category,
            "severity": severity,
            "matched_kb_ids": matched_ids,
            "is_known_issue": is_known_issue,
            "suggested_response": suggested_next_step,
            "needs_human_review": True,
        }


async def triage_ticket(customer_query: str) -> TriageResult:
    """
    High-level triage flow:
    1. Retrieve top-k KB entries for the ticket.
    2. Ask the LLM (or fallback to rules) for structured triage output.
    3. Return a validated TriageResult object.
    """
    logger.info("triage_ticket invoked for ticket subject: ",customer_query)
    
    # 1) retrieve KB
    
    logger.debug("KB query: %s", customer_query)
    kb_entries = kb.search(customer_query, top_k=3)
    if not kb_entries:
        logger.info("No KB entries found for query.")
        is_known_issue = False

    else:
        is_known_issue = True

    logger.info("KB search returned %d entries", len(kb_entries))


    # 2) ask LLM or fallback
    resp = await llm_triage(customer_query, kb_entries)
    print(resp)

    # 3) build TriageResult (ensure graceful defaults)
    matched_ids = resp.get("matched_kb_article_ids", [e.id for e in kb_entries])

    tr = TriageResult(
        summary=resp.get("summary", customer_query),
        category=resp.get("category", "other"),
        is_known_issue=is_known_issue,
        severity=resp.get("severity", "medium"),
        matched_kb_ids=matched_ids,
        suggested_next_step=resp.get("suggested_next_step", "We will investigate and get back to you."),
    )
    logger.info("TriageResult ready category=%s priority=%s suggested_team=%s", tr.category, tr.severity, tr.suggested_next_step)
    
    return tr
