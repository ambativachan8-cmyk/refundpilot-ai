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
    "approval_owner_question",
    "process_explanation_question",
    "warranty_question",
    "refund_window_question",
    "eligibility_question",
    "replacement_question",
    "refund_or_replacement_question",
    "human_agent_request",
    "frustration_or_complaint",
    "pressure_or_manipulation",
    "clarification_answer",
    "thanks_or_acknowledgement",
    "general_question",
    "unknown",
)

# Question types that are answered as follow-ups (never re-decide the refund).
FOLLOWUP_QUESTION_INTENTS = {
    "timeline_question", "status_question", "next_step_question",
    "approval_owner_question", "process_explanation_question", "warranty_question",
    "refund_window_question", "eligibility_question",
    "replacement_question", "refund_or_replacement_question", "human_agent_request",
    "frustration_or_complaint", "pressure_or_manipulation", "thanks_or_acknowledgement",
    "general_question",
}

_PRESSURE = re.compile(
    r"(approve\s+(it|this|the\s+refund)?\s*(now|immediately|right\s+now|asap)|"
    r"just\s+approve|approve\s+now|policy\s+(does\s*n'?t|doesn'?t|does\s+not)\s+matter|"
    r"i('?ll| will)\s+complain|refund\s+me\s+(now|immediately)|do\s+it\s+now|"
    r"i\s+demand|stop\s+wasting\s+my\s+time)",
    re.IGNORECASE,
)
_TIMELINE = re.compile(
    # Typo-tolerant: hoq/how, maany/many, wiill/will, wen/when, mny/many, dayss.
    r"(h[ouw]+[qw]?\s+(much\s+time|long|man+y\s+days?|m[ae]ny\s+days?|mny\s+days?)|"
    r"how\s+man+y\s+days?|w[ie]+ll\s+it\s+take|when?\s+will|how\s+soon|by\s+when|"
    r"days?\s+(wi+ll|to)\s+(it\s+)?(take|resolve)|time\s+(wi+ll\s+)?it\s+take|eta|"
    r"turnaround|how\s+much\s+longer|when\s+(will\s+it\s+be\s+)?resolv)",
    re.IGNORECASE,
)
# Direct "can't you just refund?" type pushback on an existing case (not a fresh
# request) — answered with current status, never re-clarified.
_DIRECT_REFUND_Q = re.compile(
    r"(can'?t|cant|cannot|can\s+(u|you)|could\s+(u|you)|cu?ld\s+you|why\s+(not|can'?t|cant))"
    r"\s+(you\s+)?(just\s+)?(refund|return|approve|do\s+it)",
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
# Only EXPLICIT inability to provide proof. A bare mention of "software/bluetooth"
# is a defect description, NOT a refusal of proof — those route via defect_claim.
_PROOF_UNAVAIL = re.compile(
    r"(can'?t|cannot|can\s+not|unable\s+to)\s+(show|upload|provide|capture|share|give)"
    r"|cannot\s+come\s+in\s+(a\s+)?photos?|can'?t\s+be\s+(shown|photographed|seen)"
    r"|not\s+visible|no\s+visible\s+(damage|defect)|nothing\s+to\s+show|no\s+proof|"
    r"internal/software-related",
    re.IGNORECASE,
)
_APPROVAL_OWNER = re.compile(
    r"who\s+(will|can|is\s+going\s+to|would)\s+(approve|process|handle|review|decide|author(i[sz]e))"
    r"|who\s+(approves|processes|handles|reviews|decides)|who'?s\s+(approving|processing)",
    re.IGNORECASE,
)
_PROCESS = re.compile(
    r"(what\s+(kind\s+of\s+)?steps|what'?s?\s+the\s+process|how\s+does\s+(the\s+|this\s+)?"
    r"(process|review)\s+work|what\s+is\s+involved|what'?s\s+involved|explain\s+the\s+process|"
    r"walk\s+me\s+through|what\s+happens\s+(during|in)\s+(the\s+)?review)",
    re.IGNORECASE,
)
_HUMAN = re.compile(
    r"(talk\s+to\s+(a\s+)?(human|person|agent|representative|someone)|human\s+(agent|support|person)|"
    r"speak\s+(to|with)\s+(a\s+)?(human|person|agent|representative|someone)|real\s+person|"
    r"live\s+agent|customer\s+care|customer\s+service\s+(rep|agent)|escalate\s+to\s+(a\s+)?human)",
    re.IGNORECASE,
)
_FRUSTRATION = re.compile(
    r"(frustrat|annoy(ed|ing)|ridiculous|fed\s+up|unacceptable|this\s+is\s+(bad|terrible|awful)|"
    r"waste\s+of\s+(my\s+)?time|so\s+(slow|bad)|disappoint)",
    re.IGNORECASE,
)
_REFUND_OR_REPLACEMENT = re.compile(
    r"(refund\s+or\s+(a\s+)?(replacement|replace|exchange)|(replacement|replace|exchange)\s+or\s+(a\s+)?refund)",
    re.IGNORECASE,
)
_REPLACEMENT = re.compile(
    r"(replacement|replace\s+it|replace\s+the|can\s+i\s+(get|have)\s+(a\s+)?(replacement|exchange)|"
    r"want\s+(a\s+)?(replacement|exchange)|send\s+(me\s+)?(a\s+)?(new|replacement)|exchange\s+it)",
    re.IGNORECASE,
)
_WARRANTY = re.compile(r"\bwarrant(y|ies)\b", re.IGNORECASE)
_DAMAGE = re.compile(r"\b(damage[sd]?|crack(s|ed)?|broke(n)?|dent(s|ed)?|scratch(ed|es)?|shatter)\b", re.IGNORECASE)
# "how many days was the refund window?" — a POLICY question, not a timeline one.
_REFUND_WINDOW = re.compile(
    r"(refund|return)\s+window|window\s+(for\s+)?(refund|return)s?"
    r"|days\s+(were|are)\s+you\s+offering|how\s+many\s+days\s+(do|did)\s+(i|we)\s+have\s+to\s+return",
    re.IGNORECASE,
)
# "am I eligible…" — answered conditionally from policy + case stage.
_ELIGIBILITY = re.compile(
    r"(am|are)\s+(i|we)\s+(still\s+)?eligible|eligib(le|ility)\s+for|do\s+(i|we)\s+qualify"
    r"|will\s+(i|we)\s+(be\s+eligible|qualify)|can\s+(i|we)\s+(still\s+)?(get|claim)\s+(a\s+|the\s+|my\s+)?refund",
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
    # Pressure / human / frustration first (highest-signal follow-ups).
    if _PRESSURE.search(m):
        return "pressure_or_manipulation"
    if _HUMAN.search(m):
        return "human_agent_request"
    if _FRUSTRATION.search(m):
        return "frustration_or_complaint"
    # Specific question types BEFORE the greedy "refund/return" keyword, so e.g.
    # "who will process the refund?" is an owner question, not a new refund request.
    if _APPROVAL_OWNER.search(m):
        return "approval_owner_question"
    if _PROCESS.search(m):
        return "process_explanation_question"
    if _REFUND_OR_REPLACEMENT.search(m):
        return "refund_or_replacement_question"
    if _REPLACEMENT.search(m):
        return "replacement_question"
    if _WARRANTY.search(m):
        return "warranty_question"
    # Policy questions outrank timeline ("how many days was the refund WINDOW?")
    # and the defect keyword ("am I eligible if it's really DEFECTIVE?").
    if _REFUND_WINDOW.search(m):
        return "refund_window_question"
    if _ELIGIBILITY.search(m):
        return "eligibility_question"
    if _TIMELINE.search(m):
        return "timeline_question"
    if _STATUS.search(m):
        return "status_question"
    if _NEXT_STEP.search(m):
        return "next_step_question"
    # "can't you just refund?" on an EXISTING case is pushback, not a fresh request.
    if prior_stage and _DIRECT_REFUND_Q.search(m):
        return "status_question"
    if _THANKS.search(m):
        return "thanks_or_acknowledgement"
    if _PROOF_ATTACHED.search(m):
        return "proof_attached"
    if _PROOF_UNAVAIL.search(m):
        return "proof_unavailable"
    if is_defect_claim(m) or _DAMAGE.search(m):
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
    allow_llm: bool = True,
) -> tuple[str, str]:
    """Return (message_intent, method). Keyword result is authoritative unless it
    is 'unknown' and an LLM is available to refine it.

    `allow_llm` is set False on the first turn of a conversation, where the message
    intent doesn't change the refund decision — this avoids a slow LLM call for a
    label that won't be used (big latency win)."""
    kw = classify_keyword(message, proof_attached, proof_unavailable, prior_stage)
    if kw != "unknown" or not allow_llm or not llm.is_enabled():
        return kw, "keyword"
    data = llm.call_json(_LLM_SYSTEM, f'Message: "{message}"', max_tokens=40)
    if data and data.get("message_intent") in MESSAGE_INTENTS:
        return data["message_intent"], "llm"
    return kw, "keyword"
