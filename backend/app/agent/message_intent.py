"""Classify the *kind* of message a customer sent (separate from refund intent).

After a refund decision is made, follow-up messages are usually NOT new refund
requests — they're timeline/status/next-step questions, pressure, acknowledgements,
or repeated claims. Classifying these lets the agent answer naturally instead of
repeating the same decision text.

Keyword classifier is authoritative and deterministic (used in tests and when no
LLM is configured). When an LLM is available and the keyword pass is unsure, the
LLM may refine the label — but never changes a refund decision.
"""
from __future__ import annotations

import re
from typing import Optional

from .. import llm
from ..policy import is_defect_claim

MESSAGE_INTENTS = (
    "refund_request",
    "defect_claim",
    "proof_attached",
    "proof_unavailable",
    "timeline_question",
    "status_question",
    "next_step_question",
    "pressure_or_manipulation",
    "clarification_answer",
    "thanks_or_acknowledgement",
    "general_question",
    "unknown",
)

_PRESSURE = re.compile(
    r"(approve\s+(it|this|the\s+refund)?\s*(now|immediately|right\s+now|asap)|"
    r"just\s+approve|approve\s+now|policy\s+(does\s*n'?t|doesn'?t|does\s+not)\s+matter|"
    r"i('?ll| will)\s+complain|refund\s+me\s+(now|immediately)|do\s+it\s+now|"
    r"i\s+demand|stop\s+wasting\s+my\s+time)",
    re.IGNORECASE,
)
_TIMELINE = re.compile(
    r"(how\s+(much\s+time|long)|how\s+many\s+days|when\s+will|how\s+soon|by\s+when|"
    r"time\s+(will\s+)?it\s+take|eta|turnaround|how\s+much\s+longer)",
    re.IGNORECASE,
)
_STATUS = re.compile(
    r"(is\s+(my|the)\s+refund\s+(approved|done|processed)|any\s+update|"
    r"what'?s?\s+(the\s+)?status|status\s+of|approved\s+yet|is\s+it\s+approved|"
    r"where\s+is\s+my\s+refund|what\s+is\s+happening|whats\s+happening)",
    re.IGNORECASE,
)
_NEXT_STEP = re.compile(
    r"(what\s+(happens\s+)?next|next\s+step|what\s+(do|should)\s+i\s+do|"
    r"how\s+does\s+this\s+work|what\s+now)",
    re.IGNORECASE,
)
_THANKS = re.compile(
    r"^\s*(thanks|thank\s+you|thx|ty|got\s+it|okay\s*,?\s*thanks|ok\s+thanks|"
    r"appreciate\s+it|great,?\s*thanks|cool|alright)\b",
    re.IGNORECASE,
)
_PROOF_ATTACHED = re.compile(
    r"(attach(ed|ing)?|uploaded|shar(ed|ing)|sent)\s+(a\s+|the\s+|my\s+)?"
    r"(photo|picture|video|proof|screenshot)|i\s+have\s+proof|proof\s+(is\s+)?attached",
    re.IGNORECASE,
)
_PROOF_UNAVAIL = re.compile(
    r"(can'?t|cannot|can\s+not|unable\s+to)\s+(show|upload|provide|capture)"
    r"|cannot\s+come\s+in\s+photos?|not\s+visible|no\s+visible\s+(damage|defect)"
    r"|software|bluetooth|internal|firmware",
    re.IGNORECASE,
)
_REFUND = re.compile(r"\b(refund|return|money\s+back|reimburse)\b", re.IGNORECASE)
_CONDITION = re.compile(
    r"\b(un-?used|haven'?t\s+used|not\s+used|never\s+used|delivered|days\s+ago|"
    r"brand\s+new|unopened|i\s+used|wore|opened)\b",
    re.IGNORECASE,
)


def classify_keyword(
    message: str,
    proof_attached: bool = False,
    proof_unavailable: bool = False,
    prior_stage: Optional[str] = None,
) -> str:
    if proof_attached:
        return "proof_attached"
    if proof_unavailable:
        return "proof_unavailable"
    m = message or ""
    if _PRESSURE.search(m):
        return "pressure_or_manipulation"
    if _TIMELINE.search(m):
        return "timeline_question"
    if _STATUS.search(m):
        return "status_question"
    if _NEXT_STEP.search(m):
        return "next_step_question"
    if _THANKS.search(m):
        return "thanks_or_acknowledgement"
    if _PROOF_ATTACHED.search(m):
        return "proof_attached"
    if _PROOF_UNAVAIL.search(m):
        return "proof_unavailable"
    if is_defect_claim(m):
        return "defect_claim"
    # A condition statement during clarification is an answer, not a new request.
    if prior_stage == "needs_clarification" and _CONDITION.search(m):
        return "clarification_answer"
    if _REFUND.search(m):
        return "refund_request"
    if _CONDITION.search(m):
        return "clarification_answer"
    if "?" in m:
        return "general_question"
    return "unknown"


_LLM_SYSTEM = (
    "Classify the customer's support message into exactly one label. Return JSON "
    '{"message_intent": "<label>"}. Labels: refund_request, defect_claim, '
    "proof_attached, proof_unavailable, timeline_question, status_question, "
    "next_step_question, pressure_or_manipulation, clarification_answer, "
    "thanks_or_acknowledgement, general_question, unknown. You only classify; you "
    "do not decide refunds."
)


def classify_message_intent(
    message: str,
    proof_attached: bool = False,
    proof_unavailable: bool = False,
    prior_stage: Optional[str] = None,
) -> tuple[str, str]:
    """Return (message_intent, method). Keyword result is authoritative unless it
    is 'unknown' and an LLM is available to refine it."""
    kw = classify_keyword(message, proof_attached, proof_unavailable, prior_stage)
    if kw != "unknown" or not llm.is_enabled():
        return kw, "keyword"
    data = llm.call_json(_LLM_SYSTEM, f'Message: "{message}"', max_tokens=40)
    if data and data.get("message_intent") in MESSAGE_INTENTS:
        return data["message_intent"], "llm"
    return kw, "keyword"
