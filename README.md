# Support Triage Agent

A small FastAPI service that uses an LLM + a local knowledge base to triage incoming support tickets. Given a free-text ticket description, the agent returns a summary, category, severity, whether it's a known issue (with matching KB IDs), and a suggested next step.

---

## Quickstart (local)

Prereqs
- Python 3.11+
- Docker (optional)
- Set LLM API key via env vars (or run without a key to use rule-based fallback)

Install
```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

Environment example
```env
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=your_model_name
```

Run locally
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Run via Docker (Dockerfile included)
```bash
# build
docker build -t support-triage-agent .

# run (example with env vars)
docker run -e GROQ_API_KEY="$GROQ_API_KEY" -p 8000:8000 support-triage-agent

```

---

## API

POST /triage
- Body: `{ "description": "free text of the ticket" }`
- Response: JSON (TriageResult)

Testing curl:
```bash
curl -sS -X POST https://triage-agent-task-production.up.railway.app/triage \
  -H "Content-Type: application/json" \
  -d '{"description":"Checkout fails with 500 on mobile app."}'
```

---

## Testing
- Add tests under `tests/` and run with:
```bash
pytest -q
```
Suggested tests: basic request/response, empty description, long description, KB search unit tests.

---

## Design notes
- Clear separation:
  - Orchestration: `agent.py`
  - Tools: `kb.search(...)`, `utils.build_triage_prompt(...)`, `call_openai_chat(...)`
- LLM is used to produce a single JSON object; the agent validates/parses and falls back to deterministic rules on failure.
- KB uses ChromaDB for semantic retrieval (small KB: 10–15 entries).

---

## Production Considerations (concise)
- Deployment: containerize (Docker) and run behind a load balancer on Kubernetes (EKS/GKE/AKS) or as containers on ECS/Fargate. Use horizontal autoscaling based on CPU/latency.
- Logging & monitoring: ship structured logs to a central system (CloudWatch/ELK/GCP Logging), capture metrics (request rate, LLM latency, errors) and use alerts. Add OpenTelemetry for traces.
- Config & secrets: store secrets in a secrets manager (AWS Secrets Manager / GCP Secret Manager / Azure Key Vault). Load non-sensitive config from env vars and include a `.env.example`.
- Latency & cost: LLM calls dominate cost/latency — cache repeated queries, use smaller models for quick triage, and apply rate limits + request quotas. Add retries with exponential backoff and circuit-breaker for LLM failures.

---

## Next steps / Improvements
- Add CI and unit/integration tests.
- Add request rate limiting and authentication.
- Add retry/backoff and configurable timeouts for LLM calls.
- Provide Kubernetes manifests and a `.env.example`.

---

## Contact / Contribution
Create PRs for bugfixes or feature requests. Open an issue if behavior differs from expectations.