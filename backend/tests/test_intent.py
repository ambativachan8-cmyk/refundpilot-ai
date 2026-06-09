"""Tests for the deterministic intent extraction fallback."""
from app.agent.intent import fallback_extract


def test_not_working_is_defect():
    i = fallback_extract("my product is not working i want refund")
    assert i["reason"] == "defective_or_not_working"
    assert i["product_condition_claimed"] == "defective"
    assert i["needs_clarification"] is False


def test_clean_return_detected():
    i = fallback_extract("I haven't used the headphones, want to return them")
    assert i["reason"] == "clean_return"
    assert i["product_condition_claimed"] == "unused"


def test_damaged_on_arrival_detected():
    i = fallback_extract("the box arrived damaged and the item is cracked")
    assert i["reason"] == "damaged_on_arrival"


def test_missing_package_detected():
    i = fallback_extract("my package never arrived")
    assert i["intent_type"] == "missing_package"
    assert i["reason"] == "missing_package"


def test_proof_mentioned_flag():
    i = fallback_extract("it's defective, I have attached a photo")
    assert i["proof_mentioned"] is True


def test_vague_message_needs_clarification():
    i = fallback_extract("I want to return something")
    assert i["needs_clarification"] is True
    assert i["clarification_question"]


def test_order_id_extracted():
    i = fallback_extract("please refund ORD-1001, it's unused")
    assert i["order_id_mentioned"] == "ORD-1001"


def test_internal_software_issue_is_defect_with_proof_unavailable():
    i = fallback_extract(
        "how can i upload a picture as this is a problem of software or bluetooth which cannot come in photos"
    )
    assert i["reason"] == "defective_or_not_working"
    assert i["proof_unavailable"] is True
    assert i["needs_clarification"] is False


def test_explicit_no_proof_sets_proof_unavailable():
    i = fallback_extract("I cannot provide photo proof")
    assert i["proof_unavailable"] is True


def test_bluetooth_issue_classified_as_defect():
    i = fallback_extract("the bluetooth keeps disconnecting")
    assert i["reason"] == "defective_or_not_working"
