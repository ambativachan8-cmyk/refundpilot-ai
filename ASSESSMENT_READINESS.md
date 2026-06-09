# Assessment Readiness — RefundPilot AI vs Workpodd Requirements

Status as of the latest verified build. ✅ pass · ⚠️ partial/optional · ❌ fail.

## A. Mock data
- ✅ 15 CRM profiles (`backend/app/seed.py`).
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
| 14 | Ambiguous message | escalated (clarify) | `test_intent`, ladder |
| 15 | Unknown order id | escalated (error path) | `test_agent` |

**Verification:** `pytest` → 33 passed · `npx tsc --noEmit` clean · `npm run build`
clean · live HTTP smoke confirms scenarios 1–3 + admin intent/defect logs.
