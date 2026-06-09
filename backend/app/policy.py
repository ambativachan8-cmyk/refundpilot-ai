"""Deterministic refund-policy rule engine.

This module is the **single source of truth** for refund decisions. The LangGraph
agent calls these functions as tools; the LLM (when enabled) only phrases the
final customer-facing message. This guarantees the demo behaves identically with
or without an API key, and that the agent can never "talk itself" into approving
a refund that violates policy.

Each check returns a dict matching schemas.PolicyCheck.
"""
from __future__ import annotations

import re
from typing import Any

from . import config

# Keywords that signal a defect/"not working" claim rather than a plain return.
# Kept deliberately broad: this is a SAFETY guard so a defect claim is never
# silently auto-approved even if upstream intent extraction missed it.
_DEFECT_PATTERNS = re.compile(
    r"\b(defect(ive)?|faulty|broken|malfunction(ing)?|warranty|"
    r"won'?t\s+(turn\s+on|start|charge)|not\s+turning\s+on|dead|no\s+power|"
    r"cracked|shattered|screen\s+issue|battery\s+issue|audio\s+issue|"
    r"software|bluetooth|firmware|internal|product\s+issue|"
    r"having\s+(an?\s+)?(issue|problem))\b"
    r"|(not|isn'?t|aren'?t|does\s*n'?t|do\s*n'?t|won'?t|stopped?)\s+(\w+\s+){0,3}work\w*",
    re.IGNORECASE,
)
# Keywords that signal a missing / undelivered package.
_MISSING_PATTERNS = re.compile(
    r"\b(missing|never (arrived|received)|not received|didn'?t (arrive|receive)|"
    r"package.*(lost|gone)|lost package)\b",
    re.IGNORECASE,
)


def read_policy_text() -> str:
    return config.POLICY_PATH.read_text(encoding="utf-8")


def get_policy_rules() -> list[str]:
    """Extract the numbered rule lines from the policy markdown."""
    rules: list[str] = []
    for line in read_policy_text().splitlines():
        m = re.match(r"^\d+\.\s+\*\*(.+?)\*\*\s*(.*)$", line.strip())
        if m:
            label, rest = m.group(1), m.group(2)
            rules.append(f"{label} {rest}".strip())
    return rules


def window_days_for(order: dict[str, Any]) -> int:
    return (
        config.ELECTRONICS_WINDOW_DAYS
        if order.get("category") == "electronics"
        else config.STANDARD_WINDOW_DAYS
    )


def _check(rule: str, passed: bool | None, status: str, detail: str) -> dict[str, Any]:
    return {"rule": rule, "passed": passed, "status": status, "detail": detail}


# --- Individual policy checks ---------------------------------------------
def check_cancelled(order: dict[str, Any]) -> dict[str, Any]:
    cancelled = order.get("status") == "cancelled"
    return _check(
        "Cancelled orders are not refunded again",
        passed=not cancelled,
        status="warning" if cancelled else "success",
        detail="Order is cancelled — already handled." if cancelled else "Order is active.",
    )


def check_final_sale(order: dict[str, Any]) -> dict[str, Any]:
    final = bool(order.get("final_sale"))
    return _check(
        "Final-sale items are non-refundable",
        passed=not final,
        status="failed" if final else "success",
        detail="Item is marked final sale." if final else "Item is not final sale.",
    )


def check_refund_window(order: dict[str, Any]) -> dict[str, Any]:
    days = order.get("delivered_days_ago", 0)
    limit = window_days_for(order)
    within = days <= limit
    label = "Electronics" if order.get("category") == "electronics" else "Standard"
    return _check(
        f"{label} refund window is {limit} days",
        passed=within,
        status="success" if within else "failed",
        detail=f"Delivered {days} days ago (limit {limit}).",
    )


def check_product_condition(order: dict[str, Any], message: str) -> dict[str, Any]:
    cond = order.get("condition_claimed", "unused")
    used = cond == "used"
    return _check(
        "Product must be unused unless damaged on arrival",
        passed=not used,
        status="failed" if used else "success",
        detail=f"Claimed condition: {cond}.",
    )


def check_photo_proof(order: dict[str, Any]) -> dict[str, Any]:
    if not order.get("damaged_claim"):
        return _check(
            "Damaged-on-arrival requires photo proof",
            passed=None,
            status="success",
            detail="No damage claimed — proof not required.",
        )
    has_proof = bool(order.get("photo_proof_available"))
    return _check(
        "Damaged-on-arrival requires photo proof",
        passed=has_proof,
        status="success" if has_proof else "warning",
        detail="Photo proof provided." if has_proof else "Damage claimed but no photo proof.",
    )


def check_refund_abuse(customer: dict[str, Any]) -> dict[str, Any]:
    count = customer.get("refund_count_90d", 0)
    abusing = count > config.REFUND_ABUSE_THRESHOLD
    return _check(
        f"More than {config.REFUND_ABUSE_THRESHOLD} refunds in 90 days triggers review",
        passed=not abusing,
        status="warning" if abusing else "success",
        detail=f"{count} refunds in last 90 days.",
    )


def check_high_value(order: dict[str, Any]) -> dict[str, Any]:
    high = order.get("price", 0) > config.HIGH_VALUE_THRESHOLD
    return _check(
        f"Orders above ₹{config.HIGH_VALUE_THRESHOLD:,} need manual approval",
        passed=not high,
        status="warning" if high else "success",
        detail=f"Order value ₹{order.get('price', 0):,.0f}.",
    )


def check_missing_package(order: dict[str, Any], message: str) -> dict[str, Any]:
    missing = order.get("condition_claimed") == "missing" or bool(
        _MISSING_PATTERNS.search(message or "")
    )
    return _check(
        "Missing-package claims require escalation",
        passed=not missing,
        status="warning" if missing else "success",
        detail="Missing-package claim detected." if missing else "Package was delivered.",
    )


def check_international(order: dict[str, Any]) -> dict[str, Any]:
    intl = (order.get("country") or "India").lower() != "india"
    return _check(
        "International orders may require manual review",
        passed=not intl,
        status="warning" if intl else "success",
        detail=f"Ships to {order.get('country')}.",
    )


def check_gift(order: dict[str, Any]) -> dict[str, Any]:
    gift = order.get("payment_method") == "gift"
    return _check(
        "Gift orders are refunded as store credit",
        passed=None,
        status="warning" if gift else "success",
        detail="Gift order — store credit applies." if gift else "Standard payment method.",
    )


def is_defect_claim(message: str) -> bool:
    return bool(_DEFECT_PATTERNS.search(message or ""))


def check_defect_claim(order: dict[str, Any], message: str, defect: bool) -> dict[str, Any]:
    """A defect / 'not working' claim cannot be auto-approved without proof or review."""
    if not defect:
        return _check(
            "Defect or non-working product claims require proof or manual review",
            passed=None,
            status="success",
            detail="No defect/non-working claim detected.",
        )
    has_proof = bool(order.get("photo_proof_available"))
    return _check(
        "Defect or non-working product claims require proof or manual review",
        passed=has_proof,
        status="success" if has_proof else "warning",
        detail=(
            "Customer described the product as not working; proof on file."
            if has_proof
            else "Customer described the product as not working, but no proof is available."
        ),
    )


def _defect_claimed(order: dict[str, Any], message: str, intent: dict[str, Any] | None) -> bool:
    """Defect/not-working claim from EITHER the intent layer OR the keyword guard."""
    if is_defect_claim(message):
        return True
    if intent and intent.get("reason") == "defective_or_not_working":
        return True
    if intent and intent.get("product_condition_claimed") == "defective":
        return True
    return False


def _damaged_arrival(order: dict[str, Any], intent: dict[str, Any] | None) -> bool:
    """Damaged-on-arrival from the order record OR the intent layer."""
    if bool(order.get("damaged_claim")):
        return True
    if intent and intent.get("reason") == "damaged_on_arrival":
        return True
    return False


# --- The decision ladder ---------------------------------------------------
def decide_refund(
    customer: dict[str, Any],
    order: dict[str, Any],
    message: str,
    intent: dict[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Run all checks (for the audit trail) then apply the precedence ladder.

    `intent` is the structured RefundIntent (as a dict) when available. It is one
    INPUT to the decision — it never overrides policy. The deterministic ladder
    below is the single source of truth.

    Returns (decision, ordered_policy_checks).
    """
    defect = _defect_claimed(order, message, intent)
    damaged = _damaged_arrival(order, intent)

    checks = [
        check_cancelled(order),
        check_final_sale(order),
        check_missing_package(order, message),
        check_refund_abuse(customer),
        check_photo_proof(order),
        check_defect_claim(order, message, defect),
        check_refund_window(order),
        check_product_condition(order, message),
        check_high_value(order),
        check_gift(order),
        check_international(order),
    ]

    cancelled = order.get("status") == "cancelled"
    final_sale = bool(order.get("final_sale"))
    missing = (
        order.get("condition_claimed") == "missing"
        or bool(_MISSING_PATTERNS.search(message or ""))
        or (intent or {}).get("intent_type") == "missing_package"
    )
    abusing = customer.get("refund_count_90d", 0) > config.REFUND_ABUSE_THRESHOLD
    has_proof = bool(order.get("photo_proof_available"))
    within_window = order.get("delivered_days_ago", 0) <= window_days_for(order)
    used = order.get("condition_claimed") == "used"
    high_value = order.get("price", 0) > config.HIGH_VALUE_THRESHOLD
    gift = order.get("payment_method") == "gift"
    intl = (order.get("country") or "India").lower() != "india"
    needs_clarification = bool((intent or {}).get("needs_clarification"))

    # Precedence ladder — see refund_policy.md "Decision precedence".
    if cancelled:
        decision = "already_cancelled"
    elif final_sale:
        decision = "denied"
    elif missing:
        decision = "escalated"
    elif abusing:
        decision = "escalated"
    elif damaged:
        # Damaged on arrival: refundable WITH photo proof, else escalate for review.
        decision = "approved" if has_proof else "escalated"
    elif defect:
        # Defect / "not working": never auto-approve. Out of window -> warranty;
        # in window -> escalate for proof + manual review.
        decision = "warranty_support" if not within_window else "escalated"
    elif not within_window:
        decision = "denied"
    elif used:
        decision = "denied"
    elif high_value:
        decision = "escalated"
    elif gift:
        decision = "store_credit"
    elif intl:
        decision = "escalated"
    elif needs_clarification:
        # Ambiguous request with no actionable signal — escalate (ask to clarify)
        # rather than blindly approve.
        decision = "escalated"
    else:
        decision = "approved"

    return decision, checks
