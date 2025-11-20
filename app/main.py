from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import QueryRequest, TriageResult
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

@app.get("/")
async def health():
    return {"status": "SUPPORT TRIAGE API is running"}

@app.post("/triage", response_model=TriageResult)
async def triage(req: QueryRequest):
    query = req.description
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Description cannot be empty")
    
    logger.info("Received triage request subject=", query)
    try:
        result = await triage_ticket(query)
        logger.info("Triage completed subject=%s category=%s", query)   
        return result
    except Exception as e:
        logger.exception("Triage endpoint failed for subject=%s: %s", (query or "<no-subject>"), e)
        raise HTTPException(status_code=500, detail=str(e))
