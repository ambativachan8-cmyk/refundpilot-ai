"""Turn a decision + policy checks into a customer-facing response.

Two modes:
  * deterministic (default): templated, reliable, key-free.
  * llm: if OPENAI_API_KEY is set, the templated message is rephrased by the LLM
    while the decision itself stays locked.
"""
from __future__ import annotations

from typing import Any

from .. import config
from . import prompts

# Human-readable decision labels.
DECISION_LABELS = {
    "approved": "Approved",
    "denied": "Denied",
    "escalated": "Escalated",
    "store_credit": "Store Credit",
    "warranty_support": "Warranty Support",
    "already_cancelled": "Already Cancelled",
}


def _reasons_from_checks(checks: list[dict[str, Any]]) -> str:
    notable = [c["detail"] for c in checks if c.get("status") in ("warning", "failed")]
    if not notable:
        notable = [c["detail"] for c in checks if c.get("passed")]
    return "; ".join(notable[:3]) or "Standard eligibility checks completed."


def _alternative_for(decision: str) -> str:
    return {
        "approved": "None needed — refund is proceeding.",
        "denied": "Offer warranty support or store credit where applicable.",
        "escalated": "A human support agent will review within 24 hours.",
        "store_credit": "Store credit to the recipient's account.",
        "warranty_support": "Raise a warranty support request for the defect.",
        "already_cancelled": "No action needed — order was cancelled.",
    }.get(decision, "")


def template_response(
    decision: str,
    customer: dict[str, Any],
    order: dict[str, Any],
    intent: dict[str, Any] | None = None,
    stage: str | None = None,
    pending: str | None = None,
    proof_received: bool = False,
) -> str:
    name = customer.get("name", "there").split(" ")[0]
    product = order.get("product_name", "your item")
    partial = order.get("condition_claimed") == "partial"
    intent = intent or {}
    is_defect = intent.get("reason") == "defective_or_not_working"
    needs_clarification = bool(intent.get("needs_clarification"))

    # --- Stage-aware replies take priority (multi-turn support workflow) -----
    if stage == "waiting_for_proof":
        return (
            f"Hi {name}, I can't approve a refund for the {product} yet because it's "
            "reported as not working, and a defect claim needs verification. Please "
            "attach a photo or short video using the proof buttons below — or choose "
            "“I can't show this in a photo” if the issue is internal (e.g. "
            "software or bluetooth) and we'll route it to manual review."
        )
    if stage == "under_manual_review" and proof_received:
        return (
            f"Hi {name}, thanks — I've received your proof for the {product}. I can't "
            "auto-approve a defect refund, so I'm escalating this to manual review and "
            "our support team will validate the issue and follow up."
        )
    if stage == "under_manual_review":
        return (
            f"Hi {name}, I understand the issue with the {product} may not be visible "
            "in a photo. I can't approve an immediate refund without verification, so "
            "I'm moving this to manual review / warranty support — the team will "
            "validate the issue and get back to you."
        )
    if stage == "needs_clarification":
        return (
            f"Hi {name}, I'd like to help with the right order. Could you confirm whether "
            "the item is unused, defective, damaged, or if this is a missing-package "
            "issue — and which product it's about?"
        )

    if decision == "approved" and partial:
        return (
            f"Hi {name}, you're eligible for a partial refund on the returned "
            f"items from your {product} order. I've created the return request — "
            "once the items are picked up and inspected, the partial refund will be "
            "issued to your original payment method."
        )
    if decision == "approved":
        return (
            f"Hi {name}, your refund for the {product} is eligible. I've created a "
            "return request. Once the item is picked up and inspected, the refund "
            "will be processed to your original payment method."
        )
    if decision == "denied":
        return (
            f"Hi {name}, I'm sorry, but I can't process a refund for the {product} "
            "because it falls outside our refund policy. I'd be glad to help you "
            "explore warranty support or other options if the product has a defect."
        )
    if decision == "escalated" and is_defect:
        return (
            f"Hi {name}, I can't approve this refund immediately because it's based "
            f"on a defect claim for the {product}, and that requires proof or a "
            "manual review. Please upload a photo or short video showing the issue, "
            "and our support team will review it and follow up."
        )
    if decision == "escalated" and needs_clarification:
        return (
            f"Hi {name}, I want to make sure I help with the right order. "
            + (intent.get("clarification_question") or
               "Could you tell me which item this is about and whether it's unused, "
               "damaged, or not working?")
        )
    if decision == "escalated":
        return (
            f"Hi {name}, your request for the {product} needs a closer look, so I've "
            "escalated it to our support team. A human agent will review the details "
            "and get back to you within 24 hours."
        )
    if decision == "store_credit":
        return (
            f"Hi {name}, since the {product} was a gift order, I can refund it as "
            "store credit rather than to the original payment method. Would you like "
            "me to issue the store credit now?"
        )
    if decision == "warranty_support":
        return (
            f"Hi {name}, the {product} is outside our refund window, so I can't issue "
            "a refund. However, if it has a defect, I can raise a warranty support "
            "request to get it repaired or replaced."
        )
    if decision == "already_cancelled":
        return (
            f"Hi {name}, this {product} order was already cancelled, so there's "
            "nothing further to refund. If you were charged, the amount is "
            "automatically released. Let me know if anything looks off."
        )
    return f"Hi {name}, I've reviewed your request regarding the {product}."


def _maybe_llm_rephrase(
    base_message: str,
    decision: str,
    customer: dict[str, Any],
    order: dict[str, Any],
    checks: list[dict[str, Any]],
    message: str,
) -> tuple[str, str]:
    """Try to rephrase via OpenAI. Returns (text, mode). Falls back on any error."""
    if not config.LLM_ENABLED:
        return base_message, "deterministic"
    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
        )
        user_prompt = prompts.USER_PROMPT_TEMPLATE.format(
            customer_name=customer.get("name", ""),
            tier=customer.get("tier", ""),
            product_name=order.get("product_name", ""),
            price=order.get("price", 0),
            category=order.get("category", ""),
            delivered_days_ago=order.get("delivered_days_ago", 0),
            condition=order.get("condition_claimed", ""),
            message=message,
            decision=DECISION_LABELS.get(decision, decision),
            reasons=_reasons_from_checks(checks),
            alternative=_alternative_for(decision),
        )
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": prompts.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            max_tokens=180,
        )
        text = (resp.choices[0].message.content or "").strip()
        return (text or base_message), "llm"
    except Exception:
        # Never let an LLM failure break the demo.
        return base_message, "deterministic"


def generate_response(
    decision: str,
    customer: dict[str, Any],
    order: dict[str, Any],
    checks: list[dict[str, Any]],
    message: str,
    intent: dict[str, Any] | None = None,
    stage: str | None = None,
    pending: str | None = None,
    proof_received: bool = False,
) -> tuple[str, str]:
    """Return (customer_response, llm_mode)."""
    base = template_response(decision, customer, order, intent, stage, pending, proof_received)
    return _maybe_llm_rephrase(base, decision, customer, order, checks, message)
