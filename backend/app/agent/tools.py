"""Agent tools.

These are the concrete actions the agent can take. Every tool logs to the admin
reasoning trail via save_reasoning_log so the dashboard can show exactly what the
agent did, in order, with pass/warning/fail status.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from .. import database, policy
from . import intent as intent_mod


def save_reasoning_log(
    session_id: str,
    step: str,
    tool: str,
    input_summary: str,
    output_summary: str,
    status: str = "success",
    decision_snapshot: Optional[str] = None,
) -> dict[str, Any]:
    return database.add_log(
        session_id=session_id,
        step=step,
        tool_name=tool,
        input_summary=input_summary,
        output_summary=output_summary,
        status=status,
        decision_snapshot=decision_snapshot,
    )


def fetch_customer_profile(customer_id: str) -> Optional[dict[str, Any]]:
    return database.get_customer(customer_id)


def identify_customer(customer_id: str, message: str = "") -> Optional[dict[str, Any]]:
    """Resolve the customer. Currently customer_id is provided by the UI."""
    return fetch_customer_profile(customer_id)


def _detect_order(orders: list[dict[str, Any]], message: str) -> tuple[Optional[dict[str, Any]], bool]:
    """Pick the relevant order. Returns (order, ambiguous_warning).

    - 0 orders -> (None, False)
    - 1 order  -> (that order, False)
    - many     -> keyword-match product/category against the message; if no match,
                  fall back to most recently delivered and flag a warning.
    """
    if not orders:
        return None, False
    if len(orders) == 1:
        return orders[0], False

    msg = (message or "").lower()
    for o in orders:
        words = re.findall(r"[a-z]+", o["product_name"].lower()) + [o["category"].lower()]
        if any(w in msg for w in words if len(w) > 3):
            return o, False
    # ambiguous: most recently delivered (smallest delivered_days_ago)
    most_recent = min(orders, key=lambda o: o.get("delivered_days_ago", 9999))
    return most_recent, True


def fetch_order(
    customer_id: str, message: str = "", order_id: Optional[str] = None
) -> tuple[Optional[dict[str, Any]], bool]:
    """Return (order, ambiguous_warning)."""
    if order_id:
        return database.get_order(order_id), False
    orders = database.get_orders(customer_id)
    return _detect_order(orders, message)


def read_refund_policy() -> str:
    return policy.read_policy_text()


def extract_intent(message: str) -> tuple[dict[str, Any], str, str]:
    """Extract structured customer intent. Returns (intent_dict, method, note)."""
    return intent_mod.extract_intent(message)


def run_decision(
    customer: dict[str, Any],
    order: dict[str, Any],
    message: str,
    intent: Optional[dict[str, Any]] = None,
) -> tuple[str, list[dict[str, Any]]]:
    """Run the full policy battery + precedence ladder (intent is an input only)."""
    return policy.decide_refund(customer, order, message, intent)
