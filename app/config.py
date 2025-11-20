import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Simple mapping from category to team
CATEGORY_TEAM_MAP = {
    "billing": "billing-team",
    "technical": "engineering-support",
    "account": "account-team",
    "other": "support-general"
}

# Priority rules by keywords (simple)
PRIORITY_KEYWORDS = {
    "urgent": ["outage", "down", "data loss", "emergency", "urgent"],
    "high": ["charged twice", "duplicate charge", "refund", "crash", "security"],
    "medium": ["slow", "issue", "error", "fail"],
    "low": ["question", "how to", "help"]
}