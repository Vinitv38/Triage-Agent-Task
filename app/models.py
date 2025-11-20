from pydantic import BaseModel
from typing import List, Optional

class Ticket(BaseModel):
    id: Optional[str]
    subject: str
    description: str
    customer_tier: Optional[str] = None

class KBEntry(BaseModel):
    id: int
    category: str
    title: str
    content: str

class TriageResult(BaseModel):
    category: str
    priority: str
    suggested_team: str
    matched_kb_article_ids: List[int]
    suggested_response: str
    needs_human_review: bool