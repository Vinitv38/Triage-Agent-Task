# app/utils.py
import logging
import uuid

from .config import PRIORITY_KEYWORDS
from .prompts import TRIAGE_AGENT_PROMPT


# Logger Setup
logger = logging.getLogger("support-triage")

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
handler.setFormatter(formatter)

# Avoid double handlers during reload
if not logger.handlers:
    logger.addHandler(handler)

logger.setLevel(logging.INFO)


# Utility: generate request IDs (useful for logs)
def generate_request_id() -> str:
    """Return a short unique request ID."""
    return uuid.uuid4().hex[:8]


def rule_based_category(customer_query: str) -> str:
    """Very lightweight rule-based category detection."""
    text = customer_query.lower()
    if any(w in text for w in ["bill", "charge", "refund", "invoice"]):
        return "billing"
    if any(w in text for w in ["password", "login", "account", "delete account"]):
        return "account"
    if any(w in text for w in ["crash", "error", "not loading", "slow", "bug", "outage"]):
        return "technical"
    return "other"

def rule_based_priority(customer_query: str) -> str:
    """Simple priority detection using the PRIORITY_KEYWORDS map."""
    text = customer_query.lower()
    for prio, keywords in PRIORITY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return prio
    # default
    return "medium"

def build_triage_prompt(customer_query: str, kb_text: str) -> str:
    """Build the triage prompt from the template."""
    logger.debug("Building triage prompt for ticket subject: ", customer_query)
    try:
        prompt = TRIAGE_AGENT_PROMPT.format(
            kb_text=kb_text,
            ticket=type('obj', (object,), {
                'description': customer_query,
            })
        )
        logger.debug("Triage prompt built successfully, length=%d", len(prompt))
        return prompt
    except KeyError as e:
        logger.error("Missing placeholder in TRIAGE_AGENT_PROMPT: %s", e)
        raise