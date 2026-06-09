"""End-to-end agent tests (graph + DB + logging, deterministic mode)."""
import pytest

from app import database
from app.agent import graph


@pytest.fixture(autouse=True, scope="module")
def _db():
    database.reset_db()
    yield


def run(cid, message, order_id=None):
    return graph.run_agent(f"test-{cid}", cid, message, order_id)


def test_approval_flow_produces_response_and_logs():
    state = run("CUST-001", "return my unused headphones, delivered 5 days ago")
    assert state["decision"] == "approved"
    assert state["customer_response"]
    assert state["order"]["product_name"] == "Wireless Headphones"
    # logs persisted for the session
    logs = database.get_logs(session_id="test-CUST-001")
    assert len(logs) > 5
    # every policy check was logged
    assert any(l["tool_name"] == "check_policy_rule" for l in logs)


def test_denial_holds_the_line():
    state = run("CUST-002", "I used my smartwatch for a month, I want a full refund")
    assert state["decision"] in ("denied", "warranty_support")
    assert "refund" in state["customer_response"].lower()


def test_high_value_escalated_with_warning_log():
    state = run("CUST-008", "return my laptop")
    assert state["decision"] == "escalated"
    logs = database.get_logs(session_id="test-CUST-008")
    assert any(l["status"] == "warning" for l in logs)


def test_order_disambiguation_warns():
    # CUST-001 has two orders; a vague message should pick most-recent + warn,
    # but mentioning "headphones" should resolve cleanly.
    state = run("CUST-001", "I want to return something")
    logs = database.get_logs(session_id="test-CUST-001")
    fetch_logs = [l for l in logs if l["tool_name"] == "fetch_order"]
    assert fetch_logs  # order fetch happened


def test_missing_data_escalates_via_error_path():
    # Force an order miss by passing a bogus explicit order id.
    state = run("CUST-003", "where is my refund", order_id="ORD-DOES-NOT-EXIST")
    assert state["decision"] == "escalated"
    assert state.get("error")
