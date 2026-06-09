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
