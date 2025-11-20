from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
    description: str

class KBEntry(BaseModel):
    id: int
    category: str
    title: str
    content: str

class TriageResult(BaseModel):
    summary: str
    category: str
    severity: str
    is_known_issue: bool
    matched_kb_ids: Optional[List[int]]
    suggested_next_step: str