"""Structured intent extraction.

Turns a free-text customer message into a `RefundIntent` (see schemas.py).

- If OPENAI_API_KEY is set, an LLM extracts the intent as JSON.
- Otherwise (or on any LLM error), a deterministic keyword extractor runs.

The intent describes WHAT the customer wants. It NEVER decides the refund
outcome — the deterministic policy engine does that. The intent is one input to
the policy engine (e.g. to detect a defect/not-working claim).
"""
from __future__ import annotations

import json
import re
from typing import Any

from .. import config
from ..schemas import RefundIntent
from . import category as _category
from . import prompts

# --- Keyword sets for the deterministic fallback ---------------------------
# Defect / "not working" language (NOT damaged-on-arrival — see below).
_DEFECT = re.compile(
    r"\b(not\s+working|does\s*n'?t\s+work|do\s+not\s+work|stopped?\s+working|"
    r"defect(ive)?|faulty|malfunction(ing)?|won'?t\s+(turn\s+on|start|charge)|"
    r"not\s+turning\s+on|dead|no\s+power|screen\s+issue|battery\s+issue|"
    r"audio\s+issue|product\s+issue|having\s+(an?\s+)?(issue|problem)|"
    r"there'?s\s+(an?\s+)?(issue|problem))\b",
    re.IGNORECASE,
)
# Damaged-on-arrival language.
_DAMAGED_ARRIVAL = re.compile(
    r"\b(arrived\s+(broken|damaged|cracked|shattered)|came\s+(broken|damaged)|"
    r"damaged\s+on\s+arrival|broken\s+on\s+arrival|box\s+was\s+(crushed|damaged))\b",
    re.IGNORECASE,
)
# "not (properly) working", "isn't working", "doesn't work", "stopped working"...
_NOT_WORKING = re.compile(
    r"(not|isn'?t|aren'?t|does\s*n'?t|do\s*n'?t|won'?t|stopped?)\s+(\w+\s+){0,3}work\w*",
    re.IGNORECASE,
)
# Internal / non-visible defect language (software, bluetooth, internals...).
_INTERNAL = re.compile(
    r"\b(software|bluetooth|firmware|internal|internals|connectivity|pairing|"
    r"wi-?fi|app\s+issue)\b",
    re.IGNORECASE,
)
# Customer says they CANNOT provide proof.
_PROOF_UNAVAILABLE = re.compile(
    r"(can'?t|cannot|can\s+not|unable\s+to|how\s+(can|do)\s+i)\s+"
    r"(upload|show|provide|share|send|capture|take\s+a?\s*(photo|picture|video))"
    r"|cannot\s+come\s+in\s+photos?|can'?t\s+be\s+(shown|seen|photographed)"
    r"|not\s+visible|no\s+visible\s+(damage|defect)|nothing\s+to\s+show"
    r"|no\s+proof|don'?t\s+have\s+(a\s+)?(photo|picture|proof|video)",
    re.IGNORECASE,
)
# Generic broken/damaged (defect-ish) used as a fallback signal.
_BROKEN = re.compile(r"\b(broken|damaged|cracked|shattered)\b", re.IGNORECASE)
_MISSING = re.compile(
    r"\b(missing|never\s+(arrived|received)|not\s+received|didn'?t\s+(arrive|receive)|"
    r"haven'?t\s+received|lost\s+package|package.*(lost|gone))\b",
    re.IGNORECASE,
)
_CANCEL = re.compile(r"\b(cancel(led|lation)?|is\s+my\s+order\s+cancel)", re.IGNORECASE)
_EXCHANGE = re.compile(r"\b(exchange|replace(ment)?|swap)\b", re.IGNORECASE)
_CLEAN = re.compile(
    r"\b(un-?used|haven'?t\s+used|have\s+not\s+used|not\s+used|never\s+used|"
    r"brand\s+new|unopened|still\s+sealed|did\s*n'?t\s+open)\b",
    re.IGNORECASE,
)
_USED = re.compile(
    r"\b(used\s+it|been\s+using|wore|worn|for\s+a\s+(month|week|while)|opened\s+it)\b",
    re.IGNORECASE,
)
_LATE = re.compile(r"\b(late\s+delivery|delivered\s+late|too\s+late|delayed)\b", re.IGNORECASE)
_WRONG = re.compile(r"\b(wrong\s+item|different\s+(item|product)|not\s+what\s+i\s+ordered)\b", re.IGNORECASE)
# Strong "I have actually provided proof" phrases — a bare mention of "photo" does
# NOT count. Proof only counts via an explicit attach action or a clear statement.
_PROOF = re.compile(
    r"(attach(ed|ing)?|uploaded|shar(ed|ing)|sent|sending|here\s+(is|are)|i\s+have)\s+"
    r"(a\s+|the\s+|my\s+|some\s+)?(photo|picture|pic|image|video|proof|screenshot)s?"
    r"|proof\s+(is\s+)?(attached|provided|added)|i\s+have\s+proof",
    re.IGNORECASE,
)
_REFUND = re.compile(r"\b(refund|return|money\s+back|reimburse)\b", re.IGNORECASE)
_ANGRY = re.compile(r"\b(angry|furious|ridiculous|terrible|worst|unacceptable|fed\s+up)\b", re.IGNORECASE)
_FRUSTRATED = re.compile(r"\b(frustrated|annoyed|disappointed|not\s+happy|still\s+waiting)\b", re.IGNORECASE)
_ORDER_ID = re.compile(r"\bORD-\d+\b", re.IGNORECASE)


def _evidence(message: str, *patterns: re.Pattern[str]) -> list[str]:
    found: list[str] = []
    for p in patterns:
        for m in p.finditer(message or ""):
            found.append(m.group(0))
    return found[:6]


def fallback_extract(message: str) -> dict[str, Any]:
    """Deterministic keyword-based intent extraction."""
    msg = message or ""

    order_match = _ORDER_ID.search(msg)
    order_id = order_match.group(0).upper() if order_match else None
    # Internal / software / bluetooth issues cannot be shown in a photo, so treat
    # them as "proof unavailable" rather than asking for an impossible photo.
    proof_unavailable = bool(_PROOF_UNAVAILABLE.search(msg)) or bool(_INTERNAL.search(msg))
    # "proof mentioned" means proof is actually offered — not when they say they can't.
    proof = bool(_PROOF.search(msg)) and not proof_unavailable

    sentiment = "calm"
    if _ANGRY.search(msg):
        sentiment = "angry"
    elif _FRUSTRATED.search(msg):
        sentiment = "frustrated"

    # Determine intent_type + reason + condition by priority.
    intent_type = "refund_request"
    reason = "unknown"
    condition = "unknown"
    evidence: list[str] = []

    if _MISSING.search(msg):
        intent_type, reason = "missing_package", "missing_package"
        evidence = _evidence(msg, _MISSING)
    elif _DAMAGED_ARRIVAL.search(msg):
        reason, condition = "damaged_on_arrival", "damaged"
        evidence = _evidence(msg, _DAMAGED_ARRIVAL)
    elif _DEFECT.search(msg) or _INTERNAL.search(msg) or _NOT_WORKING.search(msg):
        reason, condition = "defective_or_not_working", "defective"
        evidence = _evidence(msg, _DEFECT, _INTERNAL, _NOT_WORKING)
    elif proof_unavailable:
        # "I can't show it / it's not visible" with no other signal -> treat as a
        # (non-visible) defect claim, never a clean return.
        reason, condition = "defective_or_not_working", "defective"
        evidence = _evidence(msg, _PROOF_UNAVAILABLE)
    elif _CANCEL.search(msg):
        intent_type, reason = "cancellation_status", "duplicate_refund"
        evidence = _evidence(msg, _CANCEL)
    elif _EXCHANGE.search(msg):
        intent_type, reason = "exchange_request", "unknown"
        evidence = _evidence(msg, _EXCHANGE)
    elif _WRONG.search(msg):
        reason = "wrong_item"
        evidence = _evidence(msg, _WRONG)
    elif _LATE.search(msg):
        reason = "late_delivery"
        evidence = _evidence(msg, _LATE)
    elif _BROKEN.search(msg):
        # bare "broken"/"damaged" without "on arrival" — treat as defect claim
        reason, condition = "defective_or_not_working", "defective"
        evidence = _evidence(msg, _BROKEN)
    elif _CLEAN.search(msg):
        reason, condition = "clean_return", "unused"
        evidence = _evidence(msg, _CLEAN)
    elif _USED.search(msg):
        reason, condition = "changed_mind", "used"
        evidence = _evidence(msg, _USED)

    # Confidence + clarification.
    has_signal = reason != "unknown" or intent_type != "refund_request"
    refund_words = bool(_REFUND.search(msg))
    if not refund_words and not has_signal:
        intent_type = "unknown"
    confidence = 0.85 if has_signal else (0.55 if refund_words else 0.3)

    needs_clarification = (
        intent_type in ("refund_request", "unknown")
        and reason == "unknown"
        and condition == "unknown"
        and not proof
    )
    clarification_q = (
        "Could you tell me a bit more — is the item unused, or is there a defect or "
        "damage? And which order is this about?"
        if needs_clarification
        else None
    )

    return {
        "intent_type": intent_type,
        "reason": reason,
        "product_condition_claimed": condition,
        "proof_mentioned": proof,
        "proof_unavailable": proof_unavailable,
        "issue_category": _category.classify_issue_category(msg),
        "order_id_mentioned": order_id,
        "urgency_or_sentiment": sentiment,
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_q,
        "confidence": confidence,
        "evidence_phrases": evidence,
    }


def extract_intent(message: str) -> tuple[dict[str, Any], str, str]:
    """Return (intent_dict, method, note).

    Deterministic-FIRST: the keyword extractor is authoritative whenever it finds a
    clear signal (a known reason, a product-issue category, or a non-refund intent
    type). This is fast and far more reliable than a small local model — which was
    mislabelling clean returns and fit issues as defects. The LLM is only consulted
    for genuinely ambiguous messages, and even then its output is validated and
    falls back on any problem.
    """
    from .. import llm

    fb = fallback_extract(message)
    clear = (
        fb["reason"] != "unknown"
        or fb["intent_type"] != "refund_request"
        or fb["issue_category"] != "unknown"
        or fb.get("needs_clarification")
    )
    if clear or not llm.is_enabled():
        return fb, "fallback", "deterministic keyword extraction"

    # Ambiguous + an LLM is available -> let it try, but keep the category and
    # validate the result; fall back on any issue.
    data = llm.call_json(
        prompts.INTENT_SYSTEM_PROMPT,
        prompts.INTENT_USER_TEMPLATE.format(message=message),
        max_tokens=300,
    )
    if data is not None:
        try:
            data.setdefault("issue_category", fb["issue_category"])
            intent = RefundIntent.model_validate(data).model_dump()
            return intent, "llm", f"ambiguous — LLM refine ({llm.resolve_provider()})"
        except Exception:  # noqa: BLE001 - malformed LLM JSON -> fall back
            pass
    return fb, "fallback", "ambiguous — LLM unavailable, keyword extraction"
