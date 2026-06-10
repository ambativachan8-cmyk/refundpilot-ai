# Assessment Readiness — RefundPilot AI vs Workpodd Requirements

Status as of the latest verified build. ✅ pass · ⚠️ partial/optional · ❌ fail.

## A. Mock data
- ✅ 15 CRM profiles (`backend/app/seed.py`) — **synthetic but realistic**; no real
  or scraped data, no scraping dependency. Each order carries a `scenario_label` and
  `expected_decision` (documentation only — the policy engine decides; viewable at `/crm`).
- ✅ Strict refund policy document (`backend/app/data/refund_policy.md`).
- ✅ Orders cover the required cases: standard approval, outside window, electronics
  window, used, damaged+proof, damaged no-proof, final-sale, high-value, refund
  abuse, missing package, gift, international, cancelled, warranty, partial.

## B. Agent backend
- ✅ LangGraph is actually used (`graph.py` `StateGraph`; `GET /health` →
  `orchestrator: langgraph`). Built-in sequential fallback if import fails.
- ✅ Identifiable nodes: `receive_request → extract_intent → identify_customer →
  fetch_customer → fetch_order → read_policy → run_policy_checks → decide →
  generate_response → persist_logs`, plus `handle_error`.
- ✅ Agent calls tools dynamically; tools validate policy rules (`tools.py`,
  `policy.py`).
- ✅ Logs persisted to SQLite (`logs` table); exposed via `/admin/logs`.
- ✅ **Multi-turn conversation state** persisted (`support_sessions` table). Nodes
  `load_session_state` and `evaluate_conversation_state` remember defect claims,
  proof requests, and the order across turns. Defect-no-proof claims cannot be
  approved by a later "clean" message.
- ✅ **Simulated proof workflow** — chat shows "Attach proof" / "I can't show this
  in a photo" buttons during `waiting_for_proof`; backend accepts
  `proof_attached`/`proof_unavailable`. Proof never auto-approves a defect (goes to
  manual review); anti-loop stops repeated proof requests. Only explicit signals
  count — a bare "photo" mention does not.
- ✅ **Scenario QA harness** — `scripts/manual_qa_matrix.py` (readable table) +
  `tests/test_support_workflow_matrix.py` (multi-turn flows as assertions).
- ✅ **Conversation intelligence** — `classify_message` labels follow-ups
  (timeline/status/pressure/next-step/thanks/repeat-defect). On a settled/waiting
  case the agent answers the question without re-deciding, so it no longer repeats
  the same escalation text.
- ✅ **LLM providers** — `LLM_PROVIDER` = auto/openai/**ollama**/none. Local Ollama
  works offline with no key; every call is timed and falls back safely. `/health`
  shows `llm_provider`, `llm_model`, `ollama_reachable`. The LLM never decides
  outcomes; precise operational/follow-up replies are kept verbatim.
- ✅ **Product-issue categories** (`agent/category.py`) — safety_hazard (urgent
  escalation), size/fit, mismatch/wrong-item, visible damage, internal-electronics,
  etc. Fixes the real failures: clean returns no longer become defects, shoe-fit
  isn't "software", electric-shock is a safety escalation not a generic question.
- ✅ **Rich follow-up intents** — timeline/status/next-step/approval-owner/process/
  warranty/replacement/human/frustration/pressure, answered without re-deciding.
  "Who will process the refund?" no longer repeats the proof template.
- ✅ **Latency** — deterministic-first + fast path → typical responses **~0.5s**
  (was 10–15s). LLM only for ambiguous follow-ups; rephrasing off by default. Each
  `/chat` logs a `timing` entry.
- ✅ Failures / warnings / ambiguous cases visible (missing order → `handle_error`
  failed log; ambiguous order → warning; defect-no-proof → warning).

## C. LLM behaviour
- ✅ Runtime LLM integration exists and is clearly optional.
- ✅ With `OPENAI_API_KEY`: LLM does **structured intent extraction** (JSON) and
  **response phrasing**.
- ✅ Without a key: deterministic keyword intent + templated replies — demo works.
- ✅ `GET /health` shows `llm_enabled` true/false; `/chat` returns `intent_method`
  and `llm_mode`.
- ✅ README explains this honestly (§16 + "Why the LLM cannot override policy").
- ✅ LLM never decides the outcome — deterministic `policy.py` is source of truth.

## D. Frontend
- ✅ **Clean customer page** (`/`): customer/order context + a wide chat with an
  in-chat Case Status bar. Internal demo shortcuts are tucked in a collapsed
  "Demo scenarios (for evaluation)" section — not customer-facing. No policy-panel
  clutter (policy detail lives in `/policy` and the admin logs).
- ✅ Four pages: `/` (chat), `/policy` (rules), `/crm` (15 mock profiles +
  scenario labels), `/admin` (reasoning logs).
- ✅ Customer chat works (`/`).
- ✅ Quick demo buttons work (eligible / policy violation / damaged / high-value).
- ✅ Admin logs show reasoning / tool traces, incl. the intent-extraction step
  (`/admin`, live 3s polling, session filter).
- ✅ Policy checks visible in the chat side panel and as log rows.
- ⚠️ Voice (browser Web Speech API) present, optional, and degrades gracefully.

## E. Demo readiness
- ✅ Clean approval scenario works (CUST-001 unused headphones → approved).
- ✅ Policy violation / holding-the-line works (CUST-002 → denied).
- ✅ **Defect claim without proof does NOT auto-approve** (CUST-001 "not working"
  → escalated, asks for proof). *(This was the hardening fix.)*
- ✅ Admin logs show why (intent reason + defect check warning + decision snapshot).
- ✅ README and `DEMO_SCRIPT.md` align with actual behaviour.

## Scenario matrix (verified by tests)
| # | Input | Expected | Covered by |
|---|---|---|---|
| 1 | CUST-001 clean unused return | approved | `test_policy`, `test_agent` |
| 2 | CUST-001 "not working" no proof | escalated (not approved) | `test_policy`, `test_agent` |
| 3 | CUST-002 used electronics, 45d | denied | `test_policy` |
| 4 | Damaged + proof (CUST-005) | approved | `test_policy` |
| 5 | Damaged no proof (CUST-006) | escalated | `test_policy` |
| 6 | Final sale (CUST-007) | denied | `test_policy` |
| 7 | High value (CUST-008) | escalated | `test_policy`, `test_agent` |
| 8 | Refund abuser (CUST-009) | escalated | `test_policy` |
| 9 | Missing package (CUST-010) | escalated | `test_policy` |
| 10 | Gift order (CUST-011) | store_credit | `test_policy` |
| 11 | Cancelled (CUST-013) | already_cancelled | `test_policy` |
| 12 | International (CUST-012) | escalated | `test_policy` |
| 13 | Warranty after window (CUST-014) | warranty_support | `test_policy` |
| 14 | Ambiguous message | escalated (clarify) | `test_intent`, `test_agent` |
| 15 | Unknown order id | escalated (error path) | `test_agent` |
| 16 | **Defect → "internal/software, no photo" (same session)** | **not approved → manual review** | `test_agent` |
| 17 | **Defect → "I cannot provide proof" (same session)** | **not approved** | `test_agent` |
| 18 | **Clarify ("return my product") → then "unused, 5 days"** | escalated → approved | `test_agent` |

**Verification:** `pytest` → 69 passed · `manual_qa_matrix.py` → 49/49 checks pass ·
`npx tsc --noEmit` clean · `npm run build` clean · live HTTP smoke (Ollama active,
`provider=ollama`, `qwen2.5:3b`) confirms: clean approval + "how much time?" →
refund timeline (not repeated); defect + proof attached + "how long?" → manual-review
timeline (24–48h); pressure → holds the line. Proof buttons route to
`under_manual_review`; CUST-002 denied. App also runs fully with `LLM_PROVIDER=none`.
