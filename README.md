# RefundPilot AI 🛟

> A **controlled** AI customer-support agent for e-commerce refund decisions —
> not a generic chatbot.

RefundPilot cannot approve a refund just because the customer asks. It must
**verify CRM data**, **load the order**, **read the strict refund policy**, run
**tool-based policy checks**, and only then produce a decision — with a full,
auditable reasoning trail visible in an admin dashboard.

**🎥 Loom walkthrough:** https://www.loom.com/share/0b9925b554a34fa0a8a8fee3e9388495
· **Repo:** https://github.com/ambativachan8-cmyk/refundpilot-ai
· **Runs with no API key** (deterministic fallback — see §16).

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
2. `load_session_state` — load the prior **multi-turn conversation state** for this
   `session_id` (stage, whether a defect claim is active, whether proof was
   requested, the order under discussion).
3. `extract_intent` — derive a structured `RefundIntent` from the message (intent
   type, reason, claimed condition, `proof_mentioned`, `proof_unavailable`,
   sentiment, confidence). Uses the **LLM when `OPENAI_API_KEY` is set**, otherwise
   a deterministic keyword extractor. Describes *what the customer wants*; never decides.
4. `identify_customer` → `fetch_customer` → `fetch_order` (re-uses the session's
   order across turns; keyword-matches when ambiguous; → `handle_error` if missing).
5. `read_policy` — load the strict policy document.
6. `run_policy_checks` — run the full battery (incl. the **defect / non-working**
   check); **each check is logged**.
7. `decide` — deterministic single-message precedence ladder (the base decision).
8. `evaluate_conversation_state` — apply **multi-turn rules** on top of the base
   decision. Key guard: once a defect claim is active and proof isn't verified, the
   agent can only escalate / wait-for-proof / route to warranty — **never approve**,
   even if the latest message looks clean. Can only make the outcome stricter.
9. `generate_response` — phrase the reply (stage-aware; optionally LLM-rephrased).
10. `update_session_state` — persist the new stage/flags for the next turn.
11. `persist_logs` — finalize the audit trail.
- `handle_error` — escalate + log a `failed` status when data is missing.

> If LangGraph isn't importable, an equivalent **built-in sequential runner**
> executes the *same* node functions — behaviour and logs are identical. Check
> `GET /health` → `orchestrator` to see which is active.

---

## 6. Tools

`load_session_state` / `save_session` (multi-turn memory) · `extract_intent`
(LLM or keyword fallback) · `evaluate_conversation_state` · `identify_customer` ·
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
`LLM_PROVIDER` (`auto`/`openai`/`ollama`/`none`), `OPENAI_API_KEY`, `OPENAI_MODEL`,
`OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `LLM_TIMEOUT_SECONDS`, `REFUNDPILOT_DB`,
`NEXT_PUBLIC_API_URL`.

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
Four pages: **`/`** (clean customer chat — demo shortcuts are tucked into a
collapsed "Demo scenarios" section, not customer-facing), **`/policy`** (the strict
policy rules), **`/crm`** (the 15 mock profiles + their scenario labels), and
**`/admin`** (real-time reasoning logs, intents, policy checks, timing).

> **Mock data is synthetic but realistic** — hand-authored to cover the 15
> refund-policy scenarios. No real or scraped customer data is used, and no
> scraping dependency is required. `expected_decision` in the seed/CRM viewer
> documents intent for evaluators; the agent never reads it — the policy engine
> decides independently.

## 13. Run the tests

```bash
cd backend
pytest                 # 76 tests: policy, intent, multi-turn conversation, scenario matrix
```

**Scenario QA matrix** — a readable pass/fail sweep of 30+ realistic conversations
(clean return, defect+proof, defect+no-proof, manipulation, policy violations…):
```bash
cd backend
.venv\Scripts\python.exe scripts\manual_qa_matrix.py    # prints a PASS/FAIL table
```

**Customer-conversation simulator** — replays every multi-turn conversation like a
QA customer and prints per-turn message intent, decision, stage, and **latency**:
```bash
cd backend
.venv\Scripts\python.exe scripts\simulate_customer_conversations.py
```
The same scenarios run as assertions in `tests/test_support_workflow_matrix.py`.

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
| POST | `/agent/run` | Alias of `/chat` (the agent endpoint) |
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

## 16. LLM behaviour, providers & fallback mode

The LLM is used only for **language understanding and phrasing** — it never decides
the outcome:

1. **Message-intent classification (`classify_message`)** — labels each message
   (timeline_question, status_question, pressure, defect_claim, proof_attached, …)
   so follow-ups are answered naturally instead of repeating the decision.
2. **Refund-intent extraction (`extract_intent`)** — structured `RefundIntent`.
3. **Response phrasing** — adds natural variety to the *simple* initial decision
   replies. Precise operational/follow-up replies (timelines, proof steps) are kept
   verbatim so a small local model can't drop specifics.

### Providers (`LLM_PROVIDER`)

| Value | Behaviour |
|---|---|
| `auto` (default) | Use OpenAI if `OPENAI_API_KEY` is set, else local **Ollama** if reachable, else deterministic |
| `openai` | OpenAI (cloud); requires `OPENAI_API_KEY` |
| `ollama` | **Local Ollama** — no key, no internet |
| `none` | Always deterministic |

**Run with local Ollama (no key, offline):**
```bash
ollama serve              # if not already running
ollama pull qwen2.5:3b    # one-time
# backend/.env:  LLM_PROVIDER=ollama   OLLAMA_MODEL=qwen2.5:3b
```

Every LLM call is **best-effort with a timeout**: if the provider is down, slow, or
returns invalid JSON, the agent logs a fallback and continues deterministically — it
never crashes or hangs. `GET /health` reports `llm_enabled`, `llm_provider`,
`llm_model`, and `ollama_reachable`. `/chat` returns `intent_method` and `message_intent`.

So:
- **No key, no Ollama** → fully deterministic (keyword intent + templated replies); the demo works end-to-end.
- **Ollama running** → natural message understanding + phrasing, same decisions.
- **OpenAI key** → same, using the cloud model.

### Multi-turn conversation state

The agent is **not** a single-message classifier. Each conversation has a stable
`session_id` (the frontend keeps it across turns and starts a fresh one on customer
change, demo click, or "New conversation"). A `support_sessions` table in SQLite
remembers the `stage`, whether a **defect claim is active**, whether **proof was
requested/received**, and the order under discussion. The `evaluate_conversation_state`
node enforces the most important rule:

> Once a defect / "not working" claim is active and proof has not been verified,
> the agent can never auto-approve — even if a later message looks like a clean
> return. Saying *"it's a software/bluetooth issue that can't be shown in a photo"*
> moves the case to **manual review**, not approval.

Stages: `new_request`, `needs_clarification`, `waiting_for_proof`,
`under_manual_review`, `warranty_support`, plus the terminal decisions. The API
still returns one of the six `decision` values; `stage` carries the nuance.

### Proof workflow (simulated)

When a defect claim is in `waiting_for_proof`, the chat UI shows two buttons —
**“Attach photo/video proof”** and **“I can’t show this in a photo”** — which send
`proof_attached` / `proof_unavailable` on the next `/chat` call:

- **Proof attached** → `proof_received=true` → `under_manual_review` (a defect is
  never auto-approved even with proof; a human validates it).
- **Proof unavailable** (or an internal/software/bluetooth issue that can’t be
  photographed) → `under_manual_review` / warranty support.
- **Anti-loop:** the agent asks for proof *once*; if none arrives the next turn, it
  stops asking and routes to manual review.

Only an explicit button press or a strong phrase (“I have attached proof”) counts —
a bare mention of the word “photo” never does, so the agent can’t be talked into
believing proof exists. Proof storage is **simulated** for this prototype (see
*Known limitations*).

### Conversation intelligence (categories, follow-ups & speed)

- **Product-issue categories** (`agent/category.py`): the agent distinguishes
  `safety_hazard`, `size_or_fit_issue`, `mismatch_or_wrong_item`, `visible_damage`,
  `internal_electronics_issue`, `defect_electronics`, etc. — so a shoe fit problem
  isn't treated like a software bug, and an **electric-shock report triggers an
  urgent safety escalation** ("stop using it and unplug it"), not generic clarification.
- **Follow-up intents** (`agent/message_intent.py`): timeline / status / next-step /
  **approval-owner** / process / warranty / replacement / human-agent / frustration /
  pressure. On a settled, escalated, or in-review case these are answered **without
  re-deciding** (e.g. "Who will process the refund?" → returns-team / payment-processor
  answer; "cant you refund?" on a high-value case → manual-approval explanation, not a
  repeated clarification). **Warranty cases** answer their own timeline (~2–5 business
  days). **Policy questions are answered as policy questions**: "how many days was the
  refund window?" cites the 30/15-day windows and whether this order is inside or
  outside — never the review timeline; "in how many days should I report the issue?"
  gets the **claim-reporting deadline** for this order's category; "am I eligible…?"
  gets a conditional, window-aware eligibility answer; "refund or warranty?" is
  answered from the window + verification rules; "will I get an email?" cites the
  CRM email and notes that **notifications are simulated** in this prototype (the
  simulated send is recorded in the admin log). **Typo-tolerant** for demo phrases
  ("hoq maany days", "defect6ive", "warrenty").
- **Damaged-on-arrival vs defect**: a damage claim can still be refunded once verified
  (proof → manual review → possible refund), whereas a pure defect/not-working claim is
  never auto-approved. Proof state is conflict-safe: attaching proof after "can't show
  it" updates to *proof received* and stops repeating the "not visible in a photo" line.
- **Deterministic-first + fast path**: keyword extraction is authoritative for clear
  messages; the LLM is consulted **only** for genuinely ambiguous text, and reply
  rephrasing is off by default (`LLM_REPHRASE`). Result: typical responses are
  **~0.5s** even with Ollama running (the small model was previously misclassifying
  clean returns as defects *and* adding 10–15s of latency). Each `/chat` logs a
  `timing` entry with total agent time.

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

## Voice pipeline (bonus) — zero-cost, browser-native

The chat has an optional voice layer built entirely on **browser APIs** — no paid
voice service, no API keys, no audio ever stored or uploaded:

- **Speech-to-text** (`VoiceButton.tsx`): the 🎙 mic button uses the **Web Speech
  API** (`SpeechRecognition`). Click → speak → the transcript lands in the chat
  input, where you can **edit it before sending**. Visible states: idle, listening
  (pulsing), transcript captured, mic-permission denied, no microphone, and
  unsupported browser — all shown as a small inline hint, never an alert.
- **Text-to-speech**: the 🔊 toggle uses `speechSynthesis` to read the **agent's
  customer-facing reply only** (never logs or metadata). Turning it off, starting a
  new conversation, or leaving the page cancels speech immediately, and a new reply
  always cancels the previous one.
- **Voice never bypasses policy.** A spoken request becomes the *same text* sent to
  the *same* `/chat` endpoint — the LangGraph agent, CRM/order tools, deterministic
  policy engine, and session state treat it identically to typing.
- **Browser support:** Chrome/Edge recommended (Web Speech API requires it +
  microphone permission). Unsupported browsers degrade gracefully to typing.
- **Production upgrade path:** the same interface point could swap in OpenAI
  Realtime, ElevenLabs, or LiveKit for streaming voice; browser-native APIs were
  chosen here to keep the bonus zero-cost and key-free.

## Known prototype limitations

- **Proof upload is simulated.** The "Attach proof" button sends a flag
  (`proof_attached`), not a real file. Production would wire this to a secure
  file-upload/storage service and a human review queue; the agent logic and stages
  would stay the same.
- No authentication / multi-tenant CRM (single-store demo); SQLite, not Postgres.
- LLM intent extraction is optional — see §16. The demo runs fully without a key.

## 17. Future improvements

- Per-tool retry with backoff and richer error taxonomy in the graph.
- Streaming agent steps to the admin panel over WebSocket/SSE (instead of polling).
- Real auth + multi-tenant CRM; move SQLite → Postgres for production.
- Full realtime voice (OpenAI Realtime / LiveKit) instead of browser Web Speech.
- Human-in-the-loop approval queue for `escalated` decisions.
- Evaluation harness scoring decisions against a labelled policy dataset.
