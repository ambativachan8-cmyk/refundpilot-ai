# RefundPilot AI — Workpodd Assessment Submission

**GitHub repository:** https://github.com/ambativachan8-cmyk/refundpilot-ai
**Loom video:** https://www.loom.com/share/0b9925b554a34fa0a8a8fee3e9388495

## Summary

RefundPilot AI is a controlled, full-stack AI customer-support agent for
e-commerce refund decisions. It is **not** a generic chatbot: the LLM helps
understand the customer's language, but every refund decision is made by a
deterministic policy engine over CRM data, order data, the strict refund policy,
and multi-turn support-session state. **The LLM never approves a refund.**

## What's included

- 15-profile **synthetic** CRM database + orders (no real or scraped data).
- A **strict refund policy** document (`/policy` viewer).
- **FastAPI + LangGraph** agent loop that dynamically calls CRM/order/policy tools.
- **Deterministic policy engine** + support-session state machine (source of truth).
- LLM-assisted intent understanding with **OpenAI / Ollama / deterministic fallback**.
- **Next.js customer chat UI** with a compact live case-status bar.
- **Admin dashboard** with real-time structured reasoning logs (intents, tool
  calls, policy checks, stage transitions, timing).
- `/crm` viewer (15 mock profiles + scenario labels).
- **Browser speech-to-text voice input** (bonus, zero-cost, no audio stored).
- Simulated proof handling and simulated email-notification logging.
- Automated **pytest** suite, a **manual QA matrix**, and a **customer-conversation
  simulator**.

## Evaluation coverage (shown in the Loom)

- Standard refund **approval**.
- **Defect / manual-review** flow (proof request → manual review).
- **Refund-window / claim-deadline** and **notification** explanations.
- **High-value** order → manual approval (> ₹25,000).
- **Policy violation** where the agent **holds the line** (and resists pressure).
- **Warranty** routing for out-of-window defects.
- **Browser voice input** (speech-to-text).
- **Code tour:** repository architecture and tool orchestration.
- **Reasoning logs:** intents, policy checks, stage transitions, timing, and the
  simulated-notification entry in the admin dashboard.

## Run it (no API key required)

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 (chat), `/policy`, `/crm`, `/admin`, and
http://localhost:8000/health. With no `OPENAI_API_KEY` and no Ollama running, the
app falls back to deterministic keyword understanding — all demo flows still work.

## Notes / limitations (prototype)

Mock data is synthetic; proof upload and email notifications are **simulated**;
browser voice input needs Chrome/Edge + microphone permission; storage is local
SQLite; no production auth/deployment. The LLM never decides refunds.
