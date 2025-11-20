# Support Triage Agent

A small FastAPI service that triages support tickets using a mock knowledge base and a lightweight agent. The agent combines a simple rule-based retriever + optional LLM prompt to produce a structured JSON triage result.

## Features
- POST `/triage` to get category, priority, suggested team, matched KB articles and a suggested response.
- Lightweight keyword-based KB retrieval (no heavy deps).
- Fallback deterministic triage if no LLM key is provided.
- Example data and simple tests.

## Tech stack
- Python 3.11+
- FastAPI
- Uvicorn

## Run locally
1. Clone repo.
2. (Optional) Create venv: `python -m venv venv && source venv/bin/activate` (or use Windows activate)
3. Install: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and set `OPENAI_API_KEY` if you want to use OpenAI. Otherwise the service will use rule-based fallback.
5. Start server: `uvicorn app.main:app --reload --port 8000`
6. Open docs: `http://localhost:8000/docs`

## Example request

```bash
curl -s -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"subject":"Charged twice for my subscription","description":"I see two charges this month for the same plan. Please refund."}'