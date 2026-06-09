"""End-to-end agent tests (graph + DB + multi-turn session state, deterministic)."""
import uuid

import pytest

from app import database
from app.agent import graph


@pytest.fixture(autouse=True, scope="module")
def _db():
    database.reset_db()
    yield


def run(cid, message, order_id=None, session=None):
    """Run one turn. Each call uses a fresh session unless `session` is given."""
    sid = session or f"test-{cid}-{uuid.uuid4().hex[:6]}"
    return graph.run_agent(sid, cid, message, order_id)


# --- Single-turn behaviour -------------------------------------------------
def test_clean_return_approved():
    s = run("CUST-001", "Hi, I want to return my headphones. They were delivered 5 days ago and I haven't used them.")
    assert s["decision"] == "approved"
    assert s["stage"] == "approved"


def test_ambiguous_return_not_approved():
    s = run("CUST-001", "I want to return my product")
    assert s["decision"] != "approved"
    assert s["stage"] == "needs_clarification"


def test_defect_claim_not_approved():
    s = run("CUST-001", "the headphones are not properly working")
    assert s["decision"] != "approved"
    assert s["stage"] in ("waiting_for_proof", "under_manual_review", "escalated")


def test_cust002_used_outside_window_denied():
    s = run("CUST-002", "I bought a smartwatch 45 days ago. I used it for a month but now I want a full refund.")
    assert s["decision"] in ("denied", "warranty_support")
    assert s["decision"] != "approved"


def test_missing_package_escalated():
    s = run("CUST-010", "my package never arrived")
    assert s["decision"] == "escalated"


def test_high_value_escalated():
    s = run("CUST-008", "I'd like to return the laptop I ordered. It's unused.")
    assert s["decision"] == "escalated"


def test_final_sale_denied():
    s = run("CUST-007", "I want to return the jacket, it's unused")
    assert s["decision"] == "denied"


def test_gift_store_credit():
    s = run("CUST-011", "I want to return this gift item, unused")
    assert s["decision"] == "store_credit"


def test_repeat_abuse_escalated():
    s = run("CUST-009", "return my speaker, unused")
    assert s["decision"] == "escalated"


def test_unknown_order_escalates_via_error_path():
    s = run("CUST-003", "where is my refund", order_id="ORD-DOES-NOT-EXIST")
    assert s["decision"] == "escalated"
    assert s.get("error")


# --- Multi-turn behaviour (the regression that was reported) ---------------
def test_defect_then_no_photo_proof_never_approves():
    sid = f"test-multiturn-{uuid.uuid4().hex[:6]}"
    # Turn 1: defect claim -> not approved, proof requested.
    s1 = run("CUST-001", "the headphones are not properly working", session=sid)
    assert s1["decision"] != "approved"
    assert s1["stage"] in ("waiting_for_proof", "under_manual_review", "escalated")

    # Turn 2: customer says the issue is internal/software/bluetooth and can't be
    # shown in a photo. THIS used to incorrectly approve.
    s2 = run("CUST-001",
             "how can i upload a picture as this is a problem of software or bluetooth which cannot come in photos",
             session=sid)
    assert s2["decision"] != "approved"
    assert s2["stage"] in ("under_manual_review", "waiting_for_proof", "warranty_support")

    # Turn 3: explicit "I cannot provide photo proof" -> still not approved.
    s3 = run("CUST-001", "I cannot provide photo proof", session=sid)
    assert s3["decision"] != "approved"

    # Session remembers the defect across turns.
    sess = database.get_session(sid)
    assert sess["defect_claim_active"] is True


def test_clarify_then_approve():
    sid = f"test-clarify-{uuid.uuid4().hex[:6]}"
    s1 = run("CUST-001", "I want to return my product", session=sid)
    assert s1["decision"] != "approved"
    assert s1["stage"] == "needs_clarification"
    # After clarifying it's a clean unused return, it can approve.
    s2 = run("CUST-001", "It is the headphones, unused, delivered 5 days ago", session=sid)
    assert s2["decision"] == "approved"


def test_session_logs_include_state_steps():
    sid = f"test-logs-{uuid.uuid4().hex[:6]}"
    run("CUST-001", "the headphones are not working", session=sid)
    steps = {l["step"] for l in database.get_logs(session_id=sid)}
    assert "load_session_state" in steps
    assert "extract_intent" in steps
    assert "evaluate_conversation_state" in steps
    assert "update_session_state" in steps
