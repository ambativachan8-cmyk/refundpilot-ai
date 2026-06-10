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


def _followup_response(
    name: str, product: str, stage: str, followup: str, mi: str,
    order: dict[str, Any] | None = None,
    customer: dict[str, Any] | None = None,
) -> str:
    """Answer a follow-up question on an already-decided/in-progress case.

    `followup` is the message intent that triggered this (timeline/status/pressure/
    next_step/thanks/general) or "repeat_defect". The decision/stage do NOT change.
    """
    intent = followup if followup != mi else mi  # both carry the message intent
    order = order or {}
    customer = customer or {}

    # Window facts (used by the policy-question answers below).
    days = int(order.get("delivered_days_ago", 0) or 0)
    electronics = order.get("category") == "electronics"
    window = 15 if electronics else 30
    inside = days <= window
    side = "inside" if inside else "outside"

    # --- Universal policy questions (same answer regardless of stage) --------
    if intent == "refund_window_question":
        kind = "an electronics item (15-day window)" if electronics else "a standard item (30-day window)"
        return (f"Hi {name}, our refund window is 30 days from delivery for standard items and "
                f"15 days for electronics. The {product} is {kind} and was delivered {days} days "
                f"ago, so this order is {side} its refund window.")

    if intent == "claim_deadline_question":
        kind = "electronics" if electronics else "standard items"
        base = (f"Hi {name}, for {kind} a refund or damage claim should be raised within "
                f"{window} days of delivery. The {product} was delivered {days} days ago, so ")
        if inside:
            return base + ("this request is still inside the eligible reporting window. Since the "
                           "claim needs verification, final approval still depends on the review.")
        return base + ("this order is outside the reporting window — a verified defect would be "
                       "handled through warranty support rather than a refund.")

    if intent == "email_notification_question":
        email = customer.get("email") or "the registered email on your CRM profile"
        return (f"Hi {name}, yes — once the review is complete, the support team will send the "
                f"case update to {email}. In this prototype the email is simulated rather than "
                "actually sent, and the update is recorded in the admin dashboard.")

    if intent == "refund_vs_warranty_question":
        if inside:
            return (f"Hi {name}, the {product} is still within its {window}-day refund window, so a "
                    "verified damaged-on-arrival issue may be eligible for a refund or replacement. "
                    "If the review treats it as an internal defect rather than delivery damage, it "
                    "may be routed to warranty support instead. The review team decides after validation.")
        return (f"Hi {name}, this order is outside its {window}-day refund window, so I can't "
                "promise a direct refund. If the issue is verified as a defect, it will be handled "
                "through warranty support, which may offer a repair or replacement after validation.")

    if intent == "eligibility_question":
        if stage == "approved":
            return (f"Hi {name}, yes — your refund for the {product} is approved and will be "
                    "processed after pickup and inspection.")
        if stage == "denied":
            return (f"Hi {name}, based on the refund policy this request isn't eligible for a "
                    f"refund. If the {product} has a genuine defect, warranty support may still "
                    "cover a repair or replacement.")
        if stage == "warranty_support":
            return (f"Hi {name}, a direct refund isn't available because the {product} is outside "
                    "its refund window. If the warranty team validates the defect, you may be "
                    "eligible for a repair or replacement under warranty.")
        if stage == "escalated":
            return (f"Hi {name}, eligibility depends on manual approval — your {product} request "
                    "is already with the support team, and they'll confirm the decision.")
        return (f"Hi {name}, the {product} is {side} its {window}-day refund window ({days} days "
                "since delivery). If the review verifies the reported issue and the policy "
                "conditions are met, you may be eligible for a refund, replacement, or warranty "
                "resolution. I can't approve it before verification — the team will confirm after "
                "reviewing your case.")

    if stage == "under_manual_review":
        if intent == "proof_received":
            return (f"Hi {name}, thanks — I've received your proof for the {product}. The case is "
                    "under manual review, and the support team will validate the issue and follow up.")
        if intent == "proof_already_received":
            return (f"Hi {name}, I've noted the issue may be internal/software-related. Since proof is "
                    "already attached, the review team will consider both your explanation and the proof.")
        if intent == "proof_unavailable":
            return (f"Hi {name}, I understand the issue with the {product} may not be visible in a photo. "
                    "I can't approve an immediate refund without verification, so it's under manual "
                    "review / warranty support — the team will validate the issue and get back to you.")
        if intent == "timeline_question":
            return (f"Hi {name}, manual review usually takes 24–48 hours. Your case for the "
                    f"{product} is already under review, and the support team will validate "
                    "the issue and follow up.")
        if intent == "status_question":
            return (f"Hi {name}, your case is currently under manual review. No refund has been "
                    "approved yet — the support team will validate the issue and update you.")
        if intent == "pressure_or_manipulation":
            return (f"Hi {name}, I understand you want this resolved quickly, but I can't approve "
                    f"a defect-related refund for the {product} without verification. The case is "
                    "already under manual review.")
        if intent == "next_step_question":
            return (f"Hi {name}, next, the support team reviews the issue details and any proof, "
                    "validates the product condition, and then decides whether the resolution is a "
                    "refund, a replacement, warranty support, or denial under policy.")
        if intent == "approval_owner_question":
            return (f"Hi {name}, a support specialist / refund review team will validate the case. "
                    "The AI agent can't approve defect-related refunds without verification.")
        if intent == "process_explanation_question":
            return (f"Hi {name}, here's the process: the support team reviews the issue and any proof, "
                    "validates the product condition, and decides between refund, replacement, "
                    "warranty support, or denial under policy — usually within 24–48 hours.")
        if intent in ("refund_or_replacement_question", "replacement_question"):
            return (f"Hi {name}, that depends on verification and policy. The team may offer a refund, "
                    "a replacement, or warranty support depending on the issue and product condition.")
        if intent == "warranty_question":
            return (f"Hi {name}, yes — this can be handled under warranty if it's a genuine defect. "
                    "The review team will confirm whether the resolution is warranty, replacement, or refund.")
        if intent == "human_agent_request":
            return (f"Hi {name}, I can route this to a human support specialist — the case is already "
                    "marked for manual review, so a person will pick it up.")
        if intent == "frustration_or_complaint":
            return (f"Hi {name}, I'm sorry for the trouble. Your case for the {product} is under manual "
                    "review and the team will validate the issue and follow up within 24–48 hours.")
        if intent == "repeat_defect":
            return (f"Hi {name}, I've already logged this as a defect/damage claim for the "
                    f"{product} and moved it to manual review. No refund is approved yet; the team "
                    "will verify the issue and update you.")
        if intent == "thanks_or_acknowledgement":
            return (f"Hi {name}, you're welcome! Your case stays under manual review and the team "
                    "will follow up after validating the issue.")
        return (f"Hi {name}, your case for the {product} is under manual review. I can help with "
                "timeline, status, or next steps for this order.")

    if stage == "waiting_for_proof":
        if intent == "timeline_question":
            return (f"Hi {name}, once proof is attached — or you choose “I can't show this in a "
                    "photo” — the case moves to manual review, which usually takes 24–48 hours.")
        if intent == "pressure_or_manipulation":
            return (f"Hi {name}, I can't approve a defect refund without verification. Please attach "
                    "proof or let me know it can't be shown in a photo, and I'll move it to manual review.")
        if intent in ("status_question", "next_step_question"):
            return (f"Hi {name}, I'm waiting on proof for the reported defect. You can attach a "
                    "photo/video below, or choose “I can't show this in a photo” and I'll route it "
                    "to manual review.")
        return (f"Hi {name}, to move forward with the {product}, please attach proof below or choose "
                "“I can't show this in a photo”.")

    if stage == "approved":
        if intent == "timeline_question":
            return (f"Hi {name}, your refund for the {product} is approved. After pickup and "
                    "inspection, it's usually processed to your original payment method within "
                    "3–5 business days.")
        if intent == "status_question":
            return (f"Hi {name}, good news — your refund for the {product} is approved. After pickup "
                    "and inspection it'll be processed to your original payment method.")
        if intent in ("next_step_question", "process_explanation_question"):
            return (f"Hi {name}, next we'll arrange pickup and inspection of the {product}; the refund "
                    "then follows to your original payment method.")
        if intent == "approval_owner_question":
            return (f"Hi {name}, your refund is approved. The returns team arranges pickup and the "
                    "payment processor issues the refund to your original payment method.")
        if intent in ("replacement_question", "refund_or_replacement_question"):
            return (f"Hi {name}, your refund for the {product} is already approved. If you'd prefer a "
                    "replacement instead, let me know and I'll note it for the returns team.")
        if intent == "human_agent_request":
            return (f"Hi {name}, of course — your refund is already approved, and a human from the "
                    "returns team can help with pickup or any details.")
        return (f"Hi {name}, your refund is approved and will process after pickup and inspection.")

    if stage == "denied":
        if intent in ("replacement_question", "refund_or_replacement_question", "warranty_question"):
            return (f"Hi {name}, this didn't qualify for a refund under policy, but if the {product} has "
                    "a genuine defect I can route you to warranty support, which may cover repair or replacement.")
        if intent == "human_agent_request":
            return (f"Hi {name}, I can connect you with a human specialist. This request was denied under "
                    "policy, but they can review warranty options if there's a defect.")
        if intent in ("status_question", "next_step_question", "approval_owner_question",
                      "process_explanation_question"):
            return (f"Hi {name}, the refund for the {product} was denied because it falls outside our "
                    "refund policy. If the item has a genuine defect, I can route you to warranty support.")
        if intent in ("pressure_or_manipulation", "frustration_or_complaint"):
            return (f"Hi {name}, I understand the frustration, but I can't override the policy. This "
                    f"request for the {product} doesn't qualify for a refund — I can help with warranty "
                    "support if there's a defect.")
        if intent == "timeline_question":
            return (f"Hi {name}, this request was denied under policy, so there's no refund timeline. "
                    "If there's a defect, I can set up warranty support.")
        return (f"Hi {name}, this request was denied under our refund policy. I can help with warranty "
                "support if the item has a defect.")

    if stage == "escalated":
        if intent == "timeline_question":
            return (f"Hi {name}, a human agent typically reviews escalated requests within about "
                    "24 hours and will confirm the decision.")
        if intent in ("status_question", "pressure_or_manipulation", "frustration_or_complaint"):
            return (f"Hi {name}, I can't approve this directly — the {product} needs manual approval "
                    "(e.g. a high-value order above our auto-approval threshold). It's already escalated, "
                    "and the support team will review and confirm, usually within 24 hours.")
        if intent in ("approval_owner_question", "process_explanation_question", "next_step_question"):
            return (f"Hi {name}, a human support agent / approval team will review the escalated case and "
                    "confirm the decision — the AI agent can't approve this one automatically.")
        if intent in ("replacement_question", "refund_or_replacement_question", "warranty_question"):
            return (f"Hi {name}, the review team will decide the resolution (refund, replacement, or "
                    "warranty) once they've checked the {product}. It's already escalated for review.")
        if intent == "human_agent_request":
            return (f"Hi {name}, this is already escalated to a human support agent, who will review and "
                    "confirm the decision.")
        return (f"Hi {name}, your request for the {product} is escalated for manual review; the support "
                "team will confirm the decision, usually within 24 hours.")

    if stage == "warranty_support":
        if intent in ("timeline_question", "status_question", "next_step_question",
                      "process_explanation_question"):
            return (f"Hi {name}, warranty validation usually takes 2–5 business days depending on service "
                    "centre availability. The warranty team will inspect the issue and update you with "
                    "repair or replacement options.")
        if intent in ("replacement_question", "refund_or_replacement_question"):
            return (f"Hi {name}, the warranty team will determine whether a repair or a replacement is "
                    "appropriate after inspecting the {product}. I can't promise a replacement before validation.")
        if intent == "approval_owner_question":
            return (f"Hi {name}, the warranty / service team validates the defect and decides on repair or "
                    "replacement — this isn't something the AI agent approves automatically.")
        if intent == "human_agent_request":
            return (f"Hi {name}, I've routed this to the warranty support team — a specialist will handle "
                    "the inspection and follow up.")
        if intent in ("pressure_or_manipulation", "frustration_or_complaint"):
            return (f"Hi {name}, I understand, but the {product} is outside the refund window so I can't "
                    "issue a direct refund. Warranty support can evaluate a repair or replacement.")
        return (f"Hi {name}, the {product} is being handled as a warranty case since it's outside the "
                "refund window. The warranty team will validate the issue and update you with repair or "
                "replacement options.")

    if stage in ("store_credit", "already_cancelled"):
        return (f"Hi {name}, your case for the {product} is settled as noted. Let me know if you have "
                "any other questions about this order.")

    # Generic fallback (Rule 11): keep it on-topic.
    return (f"Hi {name}, I can help with refund, return, warranty, or order-status questions for the "
            f"{product}. Could you tell me what you need?")


def template_response(
    decision: str,
    customer: dict[str, Any],
    order: dict[str, Any],
    intent: dict[str, Any] | None = None,
    stage: str | None = None,
    pending: str | None = None,
    proof_received: bool = False,
    followup: str | None = None,
    message_intent: str | None = None,
) -> str:
    name = customer.get("name", "there").split(" ")[0]
    product = order.get("product_name", "your item")
    partial = order.get("condition_claimed") == "partial"
    intent = intent or {}
    is_defect = intent.get("reason") == "defective_or_not_working"
    needs_clarification = bool(intent.get("needs_clarification"))

    # --- Follow-up answers on an existing case (don't re-state the decision) --
    if followup:
        return _followup_response(name, product, stage or "", followup, message_intent or "",
                                  order, customer)

    issue_category = intent.get("issue_category", "unknown")

    # --- Category-specific initial replies (don't mislabel the problem) -------
    if issue_category == "safety_hazard":
        return (f"Hi {name}, please stop using the {product} and unplug it immediately — your safety "
                "comes first. Because this looks like a safety issue, I've escalated it for urgent "
                "review. I can't approve anything automatically, but the support team will prioritise "
                "your case.")
    if issue_category in ("size_or_fit_issue", "mismatch_or_wrong_item") and stage in (
        "under_manual_review", "escalated", "needs_clarification"
    ):
        return (f"Hi {name}, I understand the fit/size issue with the {product} — that's not a "
                "software or internal problem. I've checked it for return/exchange eligibility: if the "
                "item is unused and within the return window it may qualify for a return or exchange; "
                "otherwise I've routed it to the returns team for review.")

    # --- Stage-aware replies take priority (multi-turn support workflow) -----
    if stage == "waiting_for_proof" and issue_category == "visible_damage":
        # Visible damage (torn/cracked/scratched) — ask for damage photos; don't
        # offer the "internal issue" framing, which doesn't apply here.
        return (
            f"Hi {name}, I'm sorry the {product} has visible damage. To verify the claim, "
            "please attach a photo or short video of the damage using the proof button "
            "below, and I'll send it straight for review."
        )
    if stage == "waiting_for_proof":
        return (
            f"Hi {name}, I can't approve a refund for the {product} yet because the claim "
            "needs verification. Please attach a photo or short video of the issue using "
            "the proof buttons below — or choose “I can't show this in a photo” if it's an "
            "internal issue (e.g. software or bluetooth) and I'll route it to manual review."
        )
    if stage == "under_manual_review" and proof_received:
        return (
            f"Hi {name}, thanks — I've received your proof for the {product}. I can't "
            "auto-approve this, so I'm sending it to manual review and our support team "
            "will validate the issue and follow up."
        )
    if stage == "under_manual_review":
        return (
            f"Hi {name}, I can't approve an immediate refund for the {product} without "
            "verification, so I'm moving this to manual review / warranty support — the "
            "team will validate the issue and get back to you."
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
    if decision == "approved" and order.get("damaged_claim") and order.get("photo_proof_available"):
        # Be precise about WHY it's eligible — the damage record + proof on file,
        # not the customer's preference ("I didn't like it").
        return (
            f"Hi {name}, this order already has a damaged-delivery record with photo proof "
            f"on file, so the return of the {product} is eligible. I've created the return "
            "request — once the item is picked up, the refund will be processed to your "
            "original payment method."
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
    """Rephrase the pre-computed reply via the active provider (OpenAI/Ollama).

    Returns (text, mode). The decision is locked into the prompt and the LLM is
    told never to change it. Any failure falls back to the deterministic template.
    """
    from .. import llm

    if not llm.is_enabled():
        return base_message, "deterministic"
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
    text = llm.call_text(prompts.SYSTEM_PROMPT, user_prompt, max_tokens=200)
    if text:
        return text, f"llm:{llm.resolve_provider()}"
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
    followup: str | None = None,
    message_intent: str | None = None,
) -> tuple[str, str]:
    """Return (customer_response, llm_mode)."""
    base = template_response(
        decision, customer, order, intent, stage, pending,
        proof_received, followup, message_intent,
    )
    # Rephrasing is OFF by default (config.LLM_REPHRASE) for demo speed — templates
    # are already natural. Even when on, precise operational/follow-up wording is
    # kept verbatim (small models drop specifics). The LLM still powers UNDERSTANDING.
    from .. import config

    no_rephrase_stages = {"waiting_for_proof", "under_manual_review", "needs_clarification"}
    if not config.LLM_REPHRASE or followup or stage in no_rephrase_stages:
        return base, "deterministic"
    return _maybe_llm_rephrase(base, decision, customer, order, checks, message)
