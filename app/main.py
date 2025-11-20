from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import Ticket, TriageResult
from .agent import triage_ticket
from .utils import logger

app = FastAPI(title="Support Triage Agent")

# --- CORS CONFIG ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # allow all origins (change in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/triage", response_model=TriageResult)
async def triage(ticket: Ticket):
    logger.info("Received triage request subject=%s", (ticket.subject or "<no-subject>"))
    try:
        result = await triage_ticket(ticket)
        logger.info("Triage completed subject=%s category=%s", ticket.subject or "<no-subject>", result.category)   
        return result
    except Exception as e:
        logger.exception("Triage endpoint failed for subject=%s: %s", (ticket.subject or "<no-subject>"), e)
        raise HTTPException(status_code=500, detail=str(e))
