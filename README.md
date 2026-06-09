# RefundPilot AI 🛟

> A **controlled** AI customer-support agent for e-commerce refund decisions —
> not a generic chatbot.

RefundPilot cannot approve a refund just because the customer asks. It must
**verify CRM data**, **load the order**, **read the strict refund policy**, run
**tool-based policy checks**, and only then produce a decision — with a full,
auditable reasoning trail visible in an admin dashboard.

The core decision is made by a **deterministic policy engine**, so the agent can
never "talk itself" into violating policy. An LLM (optional) is used *only* to
phrase the final customer-facing message. With no API key, the app runs in a
fully deterministic fallback mode — the demo behaves identically.

---

## 1. Assessment requirement mapping

| Requirement | Where it lives |
|---|---|
| Mock CRM with 15 customer profiles | [`backend/app/seed.py`](backend/app/seed.py) |
| Strict refund policy document | [`backend/app/data/refund_policy.md`](backend/app/data/refund_policy.md) |
| Agent loop (LangGraph preferred) | [`backend/app/agent/graph.py`](backend/app/agent/graph.py) (LangGraph `StateGraph` + fallback) |
| Agent dynamically calls tools to validate policy | [`backend/app/agent/tools.py`](backend/app/agent/tools.py) + [`policy.py`](backend/app/policy.py) |
| Customer chat interface | [`frontend/app/page.tsx`](frontend/app/page.tsx) |
| Admin dashboard with real-time reasoning logs | [`frontend/app/admin/page.tsx`](frontend/app/admin/page.tsx) |
| Standard refund approval demo | Scenario 1 (CUST-001) |
| Edge case / "holds the line" demo | Scenario 2 (CUST-002) |
| Reasoning logs / failures / retries | `/admin/logs` + error/warning paths |
| Bonus: voice pipeline | Browser Web Speech API (STT mic + TTS replies) |

---

## 2. Features

- **Policy-grounded decisions** via a deterministic rule engine (single source of truth).
- **Real LangGraph `StateGraph`** with 10 explicit nodes, plus an automatic
  built-in fallback orchestrator if LangGraph can't be imported.
- **Auditable reasoning trail** — every tool call and policy check is logged with
  `success` / `warning` / `failed` status and a decision snapshot.
- **Six decision types**: approved, denied, escalated, store_credit,
  warranty_support, already_cancelled.
- **Visible failure/retry path** — missing/ambiguous orders escalate and log a warning.
- **LLM-optional** — runs with or without `OPENAI_API_KEY`.
- **Premium SaaS UI** — chat with decision badges, live customer/order/policy
  side panels, and a real-time admin log dashboard with session filtering.
- **Bonus voice** — mic dictation (speech-to-text) and spoken replies
  (text-to-speech) via browser APIs, with graceful fallback when unsupported.

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Next.js 15 Frontend (TypeScript + Tailwind)                   │
│                                                                │
│   /         Customer Chat      /admin   Reasoning Logs         │
│   ChatPanel · CustomerSelector · PolicyCard · AdminLogs        │
│   VoiceButton (Web Speech API)                                 │
└───────────────┬───────────────────────────┬──────────────────┘
                │ POST /chat                 │ GET /admin/logs (poll 3s)
                ▼                            ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI Backend (Python 3.11+)                                │
│                                                                │
│   LangGraph StateGraph  (app/agent/graph.py)                   │
│   receive → identify → fetch_customer → fetch_order →          │
│   read_policy → run_policy_checks → decide →                   │
│   generate_response → persist_logs    (handle_error branch)    │
│                                                                │
│   Tools (app/agent/tools.py) ── Policy engine (app/policy.py)  │
│   Response writer (app/agent/decisions.py) ── optional LLM     │
└───────────────┬───────────────────────────┬──────────────────┘
                ▼                            ▼
        SQLite (customers, orders, logs)   OpenAI-compatible LLM (optional)
```

---

## 4. Tech stack

**Backend:** FastAPI · Uvicorn · LangGraph · LangChain-core · Pydantic v2 ·
SQLite (stdlib `sqlite3`) · python-dotenv · OpenAI SDK (optional) · pytest

**Frontend:** Next.js 15 (App Router) · React 19 · TypeScript · Tailwind CSS 3

---

## 5. Agent workflow

The agent is a LangGraph `StateGraph` over a shared `AgentState` (TypedDict).
Nodes, in order:

1. `receive_request` — log the incoming message.
2. `identify_customer` — resolve the customer (→ `handle_error` if not found).
2b. `extract_intent` — derive a structured `RefundIntent` from the message (intent
   type, reason, claimed condition, proof mentioned, sentiment, confidence). Uses
   the **LLM when `OPENAI_API_KEY` is set**, otherwise a deterministic keyword
   extractor. This describes *what the customer wants*; it never decides the outcome.
3. `fetch_customer` — load CRM profile (tier, refund history, risk flag).
4. `fetch_order` — load the order; if the customer has several, **keyword-match**
   the message, else pick the most recent and **log a warning** (→ `handle_error`
   if none found).
5. `read_policy` — load the strict policy document.
6. `run_policy_checks` — run the full battery of checks (incl. the **defect /
   non-working** check); **each check is logged**.
7. `decide` — apply the precedence ladder (deterministic), using the order, CRM
   data, and the extracted intent as inputs.
8. `generate_response` — phrase the reply (templated, optionally LLM-rephrased).
9. `persist_logs` — finalize the audit trail.
- `handle_error` — escalate + log a `failed` status when data is missing.

> If LangGraph isn't importable, an equivalent **built-in sequential runner**
> executes the *same* node functions — behaviour and logs are identical. Check
> `GET /health` → `orchestrator` to see which is active.

---

## 6. Tools

`extract_intent` (LLM or keyword fallback) · `identify_customer` ·
`fetch_customer_profile` · `fetch_order` (with disambiguation) ·
`read_refund_policy` · `check_refund_window` · `check_product_condition` ·
`check_final_sale` · `check_refund_abuse` · `check_photo_proof` ·
`check_defect_claim` · `check_high_value` · `check_missing_package` ·
`check_international` · `check_gift` · `decide_refund` · `save_reasoning_log`.

---

## 7. Refund policy summary

1. Standard refund window: **30 days**. 2. Electronics: **15 days**.
3. Must be **unused** unless damaged on arrival. 4. Damaged-on-arrival needs
**photo proof** (else escalate). 5. **Final-sale** items are non-refundable.
6. **>3 refunds / 90 days** → escalate. 7. **Missing package** → escalate.
8. **> ₹25,000** → manual approval (escalate). 9. **Gift orders** → store credit.
10. **Cancelled** orders aren't re-refunded. 11. Defects after the window →
**warranty support**. 12. **International** orders → manual review.
13. Denials must offer the best alternative. 14. **No invented exceptions.**
15. **Every checked rule is logged.** 16. **Defect / "not working" claims are
never auto-approved** — in-window → escalate for proof/review, out-of-window →
warranty support.

Full text: [`backend/app/data/refund_policy.md`](backend/app/data/refund_policy.md).

---

## 8. Demo scenarios

The 15 CRM customers map 1:1 to the 15 required cases. Headline demos:

| # | Customer | Situation | Expected decision |
|---|---|---|---|
| 1 | CUST-001 Aarav Sharma | Headphones, 5 days, unused | **approved** |
| 2 | CUST-001 Aarav Sharma | Same item, but *"not working"* (no proof) | **escalated** (asks for proof) |
| 3 | CUST-002 Meera Iyer | Smartwatch, 45 days, used | **denied** (warranty offered) |
| 4 | CUST-005 Karan Mehta | Dinner set, damaged + photo proof | **approved** |
| 5 | CUST-008 Sneha Kapoor | ₹84,999 laptop | **escalated** |
| 6 | CUST-007 Vikram Singh | Final-sale jacket | **denied** |

> **Scenario 2 is the key "holds the line" case for a defect claim.** The same
> in-window, unused order that gets approved as a clean return is *not* approved
> once the customer says the product is "not working" — that's a defect claim and
> requires proof/manual review. The LLM/keyword intent layer detects this; the
> deterministic policy engine enforces it.

Others: CUST-003 outside window · CUST-004 used · CUST-006 damaged no proof
(escalate) · CUST-009 refund abuser (escalate) · CUST-010 missing package
(escalate) · CUST-011 gift (store credit) · CUST-012 international (escalate) ·
CUST-013 cancelled · CUST-014 warranty · CUST-015 partial refund.

The four **quick demo buttons** on the chat page run scenarios 1–4 with one click.

---

## 9. Setup

Prerequisites: **Python 3.11+** and **Node 18+**.

```bash
# from repo root
cp .env.example backend/.env          # optional — app runs without it
cp .env.example frontend/.env.local   # optional — defaults to localhost:8000
```

## 10. Environment variables

See [`.env.example`](.env.example). All optional. Key ones:
`OPENAI_API_KEY` (enables LLM phrasing), `OPENAI_MODEL`, `OPENAI_BASE_URL`,
`REFUNDPILOT_DB`, `NEXT_PUBLIC_API_URL`.

## 11. Run the backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Backend at http://localhost:8000 · interactive docs at http://localhost:8000/docs.
The SQLite DB is created and seeded automatically on first start.

## 12. Run the frontend

```bash
cd frontend
npm install
npm run dev
```
App at http://localhost:3000 (chat) and http://localhost:3000/admin (logs).

## 13. Run the tests

```bash
cd backend
pytest                 # 33 tests: policy engine, intent extraction, end-to-end agent
```

Frontend checks:
```bash
cd frontend
npm run typecheck      # tsc --noEmit
npm run build          # production build
```

---

## 14. API reference

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Status, LLM mode, active orchestrator, counts |
| GET | `/customers` | All 15 CRM profiles |
| GET | `/orders` | All orders (`?customer_id=` to filter) |
| GET | `/policy` | Policy markdown + parsed rules |
| POST | `/chat` | Run the agent: `{ customer_id, message }` |
| GET | `/admin/logs` | All reasoning logs, newest first |
| GET | `/admin/logs/{session_id}` | Logs for one session |
| POST | `/seed` | Dev: reset + reseed mock data |

---

## 15. Loom walkthrough guide (7–10 min script)

1. **Intro (0:30)** — "This is RefundPilot AI, a *controlled* AI customer-support
   agent for e-commerce refund decisions. It can't approve a refund just because
   the user asks — it has to verify data and policy, then leave an audit trail."
2. **Architecture (1:00)** — Show the diagram: Next.js frontend → FastAPI →
   LangGraph agent → SQLite + policy tools, with the admin log stream.
3. **Live demo — approval (2:00)** — Click **Eligible refund** (CUST-001). Show
   the approved badge, the reply, and the live policy checks panel.
4. **Live demo — denial (2:00)** — Click **Policy violation** (CUST-002). The
   agent denies the used, out-of-window electronics return and offers warranty —
   it "holds the line". Optionally try **High-value escalation**.
5. **Admin dashboard (1:00)** — Open `/admin`. Walk the per-session timeline:
   each tool call, each policy check, the `warning` on high-value, and the final
   decision snapshot. Mention it polls live every 3s.
6. **Code tour (2:00)** — `graph.py` (the StateGraph + nodes), `policy.py` (the
   decision ladder = source of truth), `tools.py`, `refund_policy.md`, `seed.py`,
   then the frontend `ChatPanel` / `AdminLogs`.
7. **Closing (0:30)** — "The goal was a policy-grounded AI agent with transparent
   operational logs — not just a chatbot."

---

## 16. LLM behaviour & fallback mode

The LLM is used in **two** places, and in neither does it decide the outcome:

1. **Intent extraction (`extract_intent`)** — interprets the customer's message into
   a structured `RefundIntent` (intent type, reason, claimed condition, proof
   mentioned, sentiment, confidence). With `OPENAI_API_KEY` set it calls an
   OpenAI-compatible model with JSON output; otherwise a deterministic keyword
   extractor runs. The admin log shows `method=llm` or `method=fallback`.
2. **Response phrasing (`generate_response`)** — rewrites the pre-computed reply
   into warmer wording. Any LLM error silently falls back to the template.

So:
- **No `OPENAI_API_KEY`** → fully deterministic (keyword intent + templated replies); the demo works end-to-end.
- **With key** → same decisions, smarter intent parsing and warmer wording.
- `GET /health` shows `llm_enabled`; `/chat` returns `intent_method` and `llm_mode`.

### Why the LLM cannot override policy

The LLM can **interpret** the customer's language and **draft** the reply, but the
**deterministic policy engine (`policy.py`) decides the refund outcome.** The
decision ladder reads only structured facts — order data, CRM data, and the
extracted intent — and returns one of the six decisions. Even if the LLM
mislabels intent or a customer writes a very persuasive message, the engine still
applies the rules: a defect claim is never auto-approved, a final-sale item is
never refunded, and so on. This is why the agent is *controlled*, not a chatbot —
and it's verifiable by running with no API key at all (identical decisions).

---

## 17. Future improvements

- Per-tool retry with backoff and richer error taxonomy in the graph.
- Streaming agent steps to the admin panel over WebSocket/SSE (instead of polling).
- Real auth + multi-tenant CRM; move SQLite → Postgres for production.
- Full realtime voice (OpenAI Realtime / LiveKit) instead of browser Web Speech.
- Human-in-the-loop approval queue for `escalated` decisions.
- Evaluation harness scoring decisions against a labelled policy dataset.
