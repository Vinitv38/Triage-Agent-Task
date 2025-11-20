from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import Ticket, TriageResult
from .agent import triage_ticket

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
    try:
        result = await triage_ticket(ticket)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
