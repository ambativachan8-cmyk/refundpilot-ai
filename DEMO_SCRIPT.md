# RefundPilot AI — Loom Demo Script (7–10 minutes)

A controlled walkthrough for the Workpodd assessment video. Keep it calm and
confident — the story is "policy-grounded agent with an audit trail, not a
chatbot."

## Before you hit record

1. Start the backend: `cd backend` → activate `.venv` → `uvicorn app.main:app --port 8000`.
2. Start the frontend: `cd frontend` → `npm run dev`.
3. Open two tabs: http://localhost:3000 (chat) and http://localhost:3000/admin (logs).
4. (Optional) confirm http://localhost:8000/health shows `"orchestrator":"langgraph"`.
5. Have the code editor open at `backend/app/agent/graph.py` and `backend/app/policy.py`.

---

## 1. Intro (~0:30)

> "Hi, this is RefundPilot AI — a **controlled** AI customer-support agent for
> e-commerce refund decisions. The key idea: the agent can't approve a refund
> just because the customer asks. It has to verify CRM data, load the order,
> check our strict refund policy, and then produce a decision with a full,
> auditable reasoning trail. It's an agent, not a generic chatbot."

## 2. Architecture overview (~1:00)

> "The frontend is Next.js with a customer chat and an admin reasoning dashboard.
> It talks to a FastAPI backend. The backend runs a **LangGraph state machine** —
> ten explicit nodes: receive request, identify customer, fetch customer, fetch
> order, read policy, run policy checks, decide, generate response, persist logs,
> plus an error-handling branch.
>
> The most important design decision: the **refund decision is deterministic** —
> a policy rule engine is the single source of truth. The LLM is optional and
> only *phrases* the final reply. So the agent can never talk itself into breaking
> policy, and the whole thing runs even with no API key. Data is in SQLite —
> fifteen CRM customers and their orders."

## 3. Demo 1 — standard approval (~2:00)

- On the chat page, make sure the customer is **CUST-001 (Aarav Sharma)**, or click
  the **"Eligible refund"** quick demo button.
- Send (exact message):

  > **Hi, I want to return my headphones. They were delivered 5 days ago and I haven't used them.**

> "Watch the agent. It identifies Aarav, pulls the wireless headphones order, and
> runs the policy checks — delivered 5 days ago, well inside the 30-day window;
> condition unused; not final sale. Decision: **Approved**. And on the right you
> can see every policy check it evaluated, each with a pass/warning/fail status."

Point at: the **Approved** badge, the reply, and the **Live Policy Checks** panel.

## 4. Demo 2 — policy violation / holding the line (~2:00)

- Click the **"Policy violation"** quick demo button (switches to **CUST-002, Meera Iyer**).
- Send (exact message):

  > **I bought a smartwatch 45 days ago. I used it for a month but now I want a full refund.**

> "Now the edge case. This is a smartwatch — electronics — so the window is 15
> days, not 30. It was delivered 45 days ago and it's been used. The agent
> **holds the line**: decision is **Denied**, and instead of just saying no, it
> offers warranty support as the alternative. This is the whole point — the agent
> stays grounded in policy even when the customer asks directly for a full refund."

(Optional 20s) Click **"High-value escalation"** (CUST-008, ₹84,999 laptop) to show
an **Escalated** decision and a `warning` log on the high-value rule.

## 5. Admin logs walkthrough (~1:00)

- Switch to the **/admin** tab.

> "Here's the operational view. Logs are grouped by session, newest first, and it
> polls live every three seconds. For each request you can see the ordered tool
> calls — identify customer, fetch order, read policy — then every individual
> policy check, the high-value or abuse warnings in amber, and the final decision
> snapshot on the session header. You can filter by session. This is the
> auditability story: anyone can see exactly why the agent decided what it did."

## 6. Code tour (~2:00)

- **`backend/app/agent/graph.py`** — "The LangGraph `StateGraph`: the nodes and
  the conditional edges, including the error branch. If LangGraph isn't available
  it falls back to the same node functions sequentially."
- **`backend/app/policy.py`** — "The deterministic decision ladder — this is the
  source of truth. Cancelled, then final-sale, missing package, refund abuse,
  damaged-with-proof, refund window, used, high-value, gift, international."
- **`backend/app/agent/tools.py`** — "Each tool logs to the reasoning trail."
- **`backend/app/data/refund_policy.md`** — "The strict policy in plain English."
- **`backend/app/seed.py`** — "Fifteen customers mapped to the fifteen required cases."
- **`frontend/components/ChatPanel.tsx` / `AdminLogs.tsx`** — quick look at the UI.
- (Optional) **`backend/app/agent/decisions.py`** — "Where the LLM only rephrases,
  and silently falls back to a template on any error."

## 7. Closing (~0:30)

> "So the goal was a policy-grounded AI agent with transparent operational logs —
> not just a chatbot. The decision is deterministic and auditable, the LLM is an
> optional narration layer, and the admin dashboard makes every step inspectable.
> Thanks for watching."

---

## Quick reference — exact demo inputs

| Demo | Customer | Message | Expected |
|---|---|---|---|
| Approval | **CUST-001** | Hi, I want to return my headphones. They were delivered 5 days ago and I haven't used them. | **approved** |
| Holding the line | **CUST-002** | I bought a smartwatch 45 days ago. I used it for a month but now I want a full refund. | **denied** (warranty offered) |
| (Optional) Escalation | **CUST-008** | I'd like to return the laptop I ordered. It's unused. | **escalated** |
