"""Product-issue category classifier (deterministic).

Distinguishes the *kind* of product problem so the agent doesn't treat every
non-visible issue as "software/internal". Drives both response wording and, for
safety hazards, an urgent escalation. Keyword-based and fast.
"""
from __future__ import annotations

import re

ISSUE_CATEGORIES = (
    "clean_unused_return",
    "defect_electronics",
    "internal_electronics_issue",
    "visible_damage",
    "size_or_fit_issue",
    "mismatch_or_wrong_item",
    "safety_hazard",
    "missing_package",
    "final_sale_dispute",
    "unknown",
)

# Order matters — safety first, then specific categories before generic ones.
_SAFETY = re.compile(
    r"(electric\s+shock|electrical\s+shock|shock\s+when|gives?\s+(me\s+)?(a\s+)?shock|"
    r"shocked\s+me|spark(s|ing|ed)?|caught?\s+fire|catches?\s+fire|on\s+fire|"
    r"burning\s+smell|smell\s+of\s+burning|overheat(s|ing|ed)?|getting\s+too\s+hot|"
    r"smoke|smoking|short\s+circuit|electrocut)",
    re.IGNORECASE,
)
_SIZE_FIT = re.compile(
    r"(does\s*n'?t\s+fit|not\s+fitting|doesn'?t\s+fit|too\s+(big|small|tight|loose)|"
    r"size\s+(issue|problem|is\s+wrong)|one\s+(is\s+)?(big|small|tight|loose).*(other|one)|"
    r"fit(s|ting)?\s+(is\s+)?(off|wrong|loose|tight)|wrong\s+size|"
    r"tight\s+for\s+one|loose\s+for\s+(the\s+)?other)",
    re.IGNORECASE,
)
_MISMATCH = re.compile(
    r"(wrong\s+item|wrong\s+product|different\s+(item|product|colour|color|size)|"
    r"not\s+what\s+i\s+ordered|received\s+(the\s+)?wrong|mismatch|"
    r"sent\s+(me\s+)?the\s+wrong)",
    re.IGNORECASE,
)
_INTERNAL = re.compile(
    r"\b(software|bluetooth|firmware|won'?t\s+connect|not\s+connecting|pairing|"
    r"wi-?fi|app\s+issue|connectivity|won'?t\s+pair)\b",
    re.IGNORECASE,
)
_VISIBLE_DAMAGE = re.compile(
    r"\b(crack(s|ed)?|broke(n)?|shatter(ed)?|dent(s|ed)?|chip(ped|s)?|"
    r"scratch(ed|es)?|torn|ripped|leak(ing|ed)?)\b",
    re.IGNORECASE,
)
_DEFECT_ELEC = re.compile(
    r"(not\s+(\w+\s+){0,3}work\w*|stopped?\s+working|won'?t\s+(turn\s+on|start|charge)|"
    r"dead|no\s+power|defect(ive)?|faulty|malfunction)",
    re.IGNORECASE,
)
_MISSING = re.compile(
    r"(never\s+(arrived|received)|not\s+received|didn'?t\s+(arrive|receive)|"
    r"missing\s+package|package.*(lost|missing))",
    re.IGNORECASE,
)
_CLEAN = re.compile(
    r"(un-?used|haven'?t\s+used|have\s+not\s+used|not\s+used|never\s+used|"
    r"brand\s+new|unopened|still\s+sealed)",
    re.IGNORECASE,
)


def classify_issue_category(message: str) -> str:
    m = message or ""
    if _SAFETY.search(m):
        return "safety_hazard"
    if _MISMATCH.search(m):
        return "mismatch_or_wrong_item"
    if _SIZE_FIT.search(m):
        return "size_or_fit_issue"
    if _MISSING.search(m):
        return "missing_package"
    if _INTERNAL.search(m):
        return "internal_electronics_issue"
    if _VISIBLE_DAMAGE.search(m):
        return "visible_damage"
    if _DEFECT_ELEC.search(m):
        return "defect_electronics"
    if _CLEAN.search(m):
        return "clean_unused_return"
    return "unknown"


def is_safety_hazard(message: str) -> bool:
    return bool(_SAFETY.search(message or ""))
