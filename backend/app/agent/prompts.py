"""Prompt templates for phrasing the customer-facing response.

The LLM never decides the outcome — it only rewrites a pre-computed decision into
a warm, professional reply. Templates double as the deterministic fallback.
"""
from __future__ import annotations

SYSTEM_PROMPT = (
    "You are RefundPilot, a controlled customer-support agent for an e-commerce "
    "store. A separate policy engine has ALREADY made the refund decision. Your "
    "only job is to communicate that exact decision to the customer in 2-4 short, "
    "warm, professional sentences. "
    "Rules you must obey:\n"
    "- Never change, soften, or override the decision.\n"
    "- Never promise a refund that was not approved.\n"
    "- Never invent policy exceptions.\n"
    "- If denied, be empathetic and offer the stated alternative.\n"
    "- Do not reveal internal reasoning steps or chain-of-thought; just give the "
    "customer-facing message."
)

USER_PROMPT_TEMPLATE = (
    "Customer: {customer_name} ({tier} tier)\n"
    "Order: {product_name} (₹{price:.0f}), category {category}, delivered "
    "{delivered_days_ago} days ago, condition '{condition}'.\n"
    "Customer message: \"{message}\"\n\n"
    "Final decision (do not change): {decision}\n"
    "Key reasons: {reasons}\n"
    "Suggested alternative: {alternative}\n\n"
    "Write the customer-facing reply now."
)
