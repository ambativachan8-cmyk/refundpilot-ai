"""Unit tests for the deterministic policy engine."""
from app import policy
from app.seed import CUSTOMERS, ORDERS

C = {c["customer_id"]: c for c in CUSTOMERS}
# first order per customer (primary scenario order)
O = {}
for o in ORDERS:
    O.setdefault(o["customer_id"], o)


def decide(cid, message=""):
    return policy.decide_refund(C[cid], O[cid], message)[0]


def test_standard_refund_approved():
    assert decide("CUST-001", "return my unused headphones delivered 5 days ago") == "approved"


def test_defect_claim_in_window_not_auto_approved():
    # The regression: "not working" on an in-window unused order must NOT approve.
    decision = decide("CUST-001", "my product is not working i want refund")
    assert decision == "escalated"
    assert decision != "approved"


def test_defect_claim_outside_window_routes_to_warranty():
    # CUST-002 smartwatch is 45 days old (electronics window 15).
    assert decide("CUST-002", "my smartwatch is not working anymore") == "warranty_support"


def test_defect_check_logged_as_warning_without_proof():
    _, checks = policy.decide_refund(
        C["CUST-001"], O["CUST-001"], "the headphones are defective"
    )
    defect_checks = [c for c in checks if "Defect" in c["rule"]]
    assert defect_checks and defect_checks[0]["status"] == "warning"


def test_intent_aware_defect_via_structured_intent():
    # Even with a benign-looking message, a structured defect intent blocks approval.
    intent = {"reason": "defective_or_not_working", "product_condition_claimed": "defective"}
    decision, _ = policy.decide_refund(C["CUST-001"], O["CUST-001"], "please help", intent)
    assert decision == "escalated"


def test_electronics_after_45_days_denied():
    assert decide("CUST-002", "I used my smartwatch for a month, want a refund") == "denied"


def test_non_electronics_outside_window_denied():
    assert decide("CUST-003") == "denied"


def test_used_product_denied():
    assert decide("CUST-004", "I wore the shoes a few times") == "denied"


def test_damaged_with_proof_approved():
    assert decide("CUST-005", "arrived broken, here are photos") == "approved"


def test_damaged_without_proof_escalated():
    assert decide("CUST-006", "it arrived damaged") == "escalated"


def test_final_sale_denied():
    assert decide("CUST-007") == "denied"


def test_high_value_escalated():
    assert decide("CUST-008", "return my new laptop") == "escalated"


def test_refund_abuse_escalated():
    assert decide("CUST-009") == "escalated"


def test_missing_package_escalated():
    assert decide("CUST-010", "my package never arrived") == "escalated"


def test_gift_store_credit():
    assert decide("CUST-011") == "store_credit"


def test_international_escalated():
    assert decide("CUST-012") == "escalated"


def test_cancelled_order():
    assert decide("CUST-013") == "already_cancelled"


def test_warranty_support_for_defect_after_window():
    assert decide("CUST-014", "the coffee machine is defective and not working") == "warranty_support"


def test_partial_refund_approved():
    assert decide("CUST-015", "return one of the three bedsheets") == "approved"


def test_policy_rules_parsed():
    rules = policy.get_policy_rules()
    assert len(rules) >= 12
