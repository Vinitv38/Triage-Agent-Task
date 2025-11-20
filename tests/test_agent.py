import asyncio
from app.models import Ticket
from app.agent import triage_ticket


def test_triage_rule_based():
    t = Ticket(
        id="t1",
        subject="Charged twice for my subscription",
        description="I see two charges this month for the same subscription."
    )
    res = asyncio.get_event_loop().run_until_complete(triage_ticket(t))
    assert res.category == "billing"
    assert "billing" in res.suggested_team


def test_triage_technical():
    t = Ticket(
        id="t2",
        subject="App crashes on launch",
        description="The app crashes every time I open it."
    )
    res = asyncio.get_event_loop().run_until_complete(triage_ticket(t))
    assert res.category == "technical"
    assert res.priority in ["low", "medium", "high", "urgent"]
