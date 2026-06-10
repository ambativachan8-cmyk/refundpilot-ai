"""Multi-turn conversation state machine.

Runs AFTER the deterministic single-message policy decision. Its job is to make
the agent behave like a real support workflow across turns — most importantly:

    Once a defect / "not working" claim is active in a session and proof has not
    been verified, the agent can NEVER auto-approve a refund — even if a later
    message looks like a clean return.

This layer can only make an outcome *stricter* (or hold it), never looser. The
deterministic policy engine remains the source of truth; this adds memory.
"""
from __future__ import annotations

from typing import Any, Optional

from ..policy import window_days_for


def _within_window(order: dict[str, Any]) -> bool:
    return order.get("delivered_days_ago", 0) <= window_days_for(order)


SETTLED_STAGES = {
    "approved", "denied", "under_manual_review",
    "warranty_support", "store_credit", "already_cancelled",
}
FOLLOWUP_INTENTS = {
    "timeline_question", "status_question", "next_step_question",
    "pressure_or_manipulation", "thanks_or_acknowledgement", "general_question",
}


def evaluate(
    prior: Optional[dict[str, Any]],
    intent: dict[str, Any],
    order: dict[str, Any],
    base_decision: str,
    proof_attached: bool = False,
    proof_unavailable_flag: bool = False,
    message_intent: str = "unknown",
) -> dict[str, Any]:
    """Return the conversation-aware outcome.

    `proof_attached` / `proof_unavailable_flag` are the explicit signals from the
    UI proof buttons. A bare textual mention of "photo" never counts as proof —
    only an explicit attach action or a strong phrase ("I have attached proof").

    Keys: decision (one of the 6 API decisions), stage, pending_requirement,
    defect_claim_active, proof_required, proof_received, last_reason,
    clarification_question.
    """
    prior = prior or {}
    intent = intent or {}

    within = _within_window(order)
    defect_now = intent.get("reason") == "defective_or_not_working"
    proof_unavailable = proof_unavailable_flag or bool(intent.get("proof_unavailable"))
    # Proof counts only via the explicit attach button, a strong "I have attached
    # proof" phrase, or proof already on file for the order.
    proof_offered = (
        proof_attached
        or bool(intent.get("proof_mentioned"))
        or bool(order.get("photo_proof_available"))
    )
    needs_clar = bool(intent.get("needs_clarification"))

    prior_stage = prior.get("stage")
    prior_defect = bool(prior.get("defect_claim_active"))
    prior_proof_received = bool(prior.get("proof_received"))

    # A defect claim is "active" if it was raised this turn, earlier in the
    # session, or the policy engine routed to warranty (out-of-window defect).
    # Damaged-on-arrival (handled by the policy engine with photo proof) is NOT
    # treated as a defect claim, so those can still approve.
    defect_active = prior_defect or defect_now or base_decision == "warranty_support"

    def out(decision, stage, pending, *, proof_required=False,
            proof_received=False, reason="", clar=None, followup=None):
        return {
            "decision": decision,
            "stage": stage,
            "pending_requirement": pending,
            "defect_claim_active": defect_active,
            "proof_required": bool(prior.get("proof_required")) or proof_required,
            "proof_received": prior_proof_received or proof_received,
            "last_reason": reason,
            "clarification_question": clar,
            "followup": followup,
        }

    # 0) Continuation of an existing case: answer follow-ups WITHOUT re-deciding.
    #    (Skip when the customer is supplying new proof signals.)
    prior_decision = prior.get("last_decision")
    if prior_decision and not proof_attached and not proof_unavailable:
        # Conversational follow-up on a settled or waiting case -> keep state.
        if message_intent in FOLLOWUP_INTENTS and (
            prior_stage in SETTLED_STAGES or prior_stage == "waiting_for_proof"
        ):
            return out(prior_decision, prior_stage,
                       prior.get("pending_requirement", "none"),
                       proof_received=prior_proof_received,
                       reason=f"Follow-up '{message_intent}' — answered without re-deciding.",
                       followup=message_intent)
        # Repeated defect / clarification while already under review -> acknowledge.
        if message_intent in ("defect_claim", "clarification_answer") and prior_stage in (
            "under_manual_review", "warranty_support"
        ):
            return out(prior_decision, prior_stage, "manual_review",
                       proof_received=prior_proof_received,
                       reason="Repeated defect/clarification — case already under review.",
                       followup="repeat_defect")

    # 1) Terminal policy outcomes the conversation layer must not loosen.
    if base_decision == "denied":
        return out("denied", "denied", "none", reason="Policy violation — refund denied.")
    if base_decision == "store_credit":
        return out("store_credit", "store_credit", "none", reason="Gift order — store credit.")
    if base_decision == "already_cancelled":
        return out("already_cancelled", "already_cancelled", "none",
                   reason="Order already cancelled.")

    # 2) Defect / not-working claim — never auto-approve.
    if defect_active:
        if not within:
            return out("warranty_support", "warranty_support", "none",
                       reason="Defect reported outside the refund window — routed to warranty.")
        if proof_unavailable:
            return out("escalated", "under_manual_review", "manual_review",
                       reason="Defect can't be shown in a photo (internal/software) — sent to manual review.")
        if proof_offered or prior_proof_received:
            return out("escalated", "under_manual_review", "manual_review",
                       proof_received=True,
                       reason="Proof received for the defect — sent to manual review for validation.")
        # Anti-loop: ask for proof once. If we already asked last turn and still
        # have no proof, stop asking and route to manual review.
        if prior_stage == "waiting_for_proof":
            return out("escalated", "under_manual_review", "manual_review",
                       reason="Proof not provided after request — sent to manual review.")
        return out("escalated", "waiting_for_proof", "provide_photo_or_video_proof",
                   proof_required=True,
                   reason="Defect claim — photo/video proof requested before any refund.")

    # 3) Non-defect escalations / warranty from the policy engine.
    if base_decision == "warranty_support":
        return out("warranty_support", "warranty_support", "none",
                   reason="Outside refund window — routed to warranty support.")
    if base_decision == "escalated":
        if needs_clar:
            return out("escalated", "needs_clarification", "clarify_condition",
                       reason="Request is ambiguous — asked the customer to clarify.",
                       clar=intent.get("clarification_question"))
        return out("escalated", "escalated", "manual_review",
                   reason="Requires manual review (high-value / abuse / missing / international).")

    # 4) Clean, eligible return (incl. clarify-then-approve).
    if base_decision == "approved":
        return out("approved", "approved", "none", reason="Eligible return — refund approved.")

    # 5) Safety net: never silently approve.
    return out("escalated", "under_manual_review", "manual_review",
               reason="Unresolved case — sent to manual review.")
