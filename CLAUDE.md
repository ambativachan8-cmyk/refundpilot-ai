# RefundPilot AI — Project Instructions

Concise project context for Claude Code. Global rules still apply.

## Purpose

A **controlled** AI customer-support agent for e-commerce refund decisions (built
for the Workpodd Full-Stack AI assessment). It verifies CRM data + order data +
the strict refund policy, then returns a decision (approved / denied / escalated /
store_credit / warranty_support / already_cancelled) with a full, auditable
reasoning trail. **Not a generic chatbot.**

## Stack

- **Backend:** FastAPI · LangGraph `StateGraph` · Pydantic v2 · SQLite (stdlib
  `sqlite3`) · Uvicorn · pytest. Python 3.11+.
- **Frontend:** Next.js 15 (App Router) · React 19 · TypeScript · Tailwind CSS 3.
- **LLM:** OpenAI SDK, optional. Runs fully without a key (deterministic mode).

## Layout

- `backend/app/policy.py` — deterministic decision ladder (source of truth).
- `backend/app/agent/graph.py` — LangGraph graph (10 nodes) + built-in fallback.
- `backend/app/agent/tools.py` — tool functions (each logs to the audit trail).
- `backend/app/agent/decisions.py` — phrases the reply (templated; LLM optional).
- `backend/app/seed.py` — 15 CRM customers = the 15 required refund cases.
- `backend/app/data/refund_policy.md` — the strict policy.
- `backend/app/main.py` — FastAPI endpoints.
- `frontend/app/page.tsx` — customer chat; `frontend/app/admin/page.tsx` — logs.

## Run commands

Backend:
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm install
npm run dev                       # http://localhost:3000  (admin: /admin)
```

## Verification commands

```bash
cd backend && pytest              # 21 tests (policy + end-to-end agent)
cd frontend && npx tsc --noEmit   # typecheck
cd frontend && npm run build      # production build
```

Live smoke: start backend, then `GET /health`, `GET /customers`,
`POST /chat` (CUST-001 → approved, CUST-002 → denied), `GET /admin/logs`.

## Critical rules

1. **The deterministic policy engine (`policy.py`) is the single source of truth
   for every refund decision. The LLM only NARRATES the final reply — it must
   never change, soften, or override the decision.** Do not move decision logic
   into the LLM or prompts.
2. **Never commit secrets.** `OPENAI_API_KEY` comes from the environment only.
   `.env` is gitignored; only `.env.example` is committed. The DB (`*.db`) and
   `.venv` / `node_modules` are gitignored.
3. Keep the audit trail intact — every tool call and policy check must log to the
   admin reasoning trail (`save_reasoning_log`).
4. Voice is an optional bonus (browser Web Speech API) and must degrade
   gracefully; do not make core flows depend on it.
5. This is a one-night assessment MVP: prefer stability and demo confidence over
   new features. Do not redesign the UI or rewrite the agent architecture.
