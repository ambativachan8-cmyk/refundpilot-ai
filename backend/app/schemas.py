"""Pydantic v2 schemas for the RefundPilot AI API."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Decision = Literal[
    "approved",
    "denied",
    "escalated",
    "store_credit",
    "warranty_support",
    "already_cancelled",
]

CheckStatus = Literal["success", "warning", "failed"]

# Conversation stage (multi-turn support state). Richer than `Decision`; the API
# still returns one of the 6 Decisions, with `stage` carrying the nuance.
Stage = Literal[
    "new_request",
    "needs_clarification",
    "waiting_for_proof",
    "proof_received",
    "under_manual_review",
    "approved",
    "denied",
    "escalated",
    "warranty_support",
    "store_credit",
    "already_cancelled",
]

PendingRequirement = Literal[
    "clarify_order",
    "clarify_condition",
    "provide_photo_or_video_proof",
    "manual_review",
    "none",
]

IntentType = Literal[
    "refund_request",
    "warranty_support",
    "missing_package",
    "cancellation_status",
    "exchange_request",
    "unknown",
]

IntentReason = Literal[
    "clean_return",
    "defective_or_not_working",
    "damaged_on_arrival",
    "changed_mind",
    "late_delivery",
    "wrong_item",
    "missing_package",
    "final_sale_dispute",
    "duplicate_refund",
    "unknown",
]


class RefundIntent(BaseModel):
    """Structured intent extracted from the customer's message.

    Produced by the LLM when OPENAI_API_KEY is set, otherwise by a deterministic
    keyword extractor. This NEVER decides the refund outcome — it only describes
    what the customer is asking for so the policy engine can validate it.
    """
    intent_type: IntentType = "refund_request"
    reason: IntentReason = "unknown"
    product_condition_claimed: Literal["unused", "used", "damaged", "defective", "unknown"] = "unknown"
    proof_mentioned: bool = False
    proof_unavailable: bool = False  # customer says they CANNOT provide proof
    issue_category: str = "unknown"  # product-issue category (see agent/category.py)
    order_id_mentioned: Optional[str] = None
    urgency_or_sentiment: Literal["calm", "frustrated", "angry", "unknown"] = "unknown"
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    confidence: float = 0.5
    evidence_phrases: list[str] = []


class Customer(BaseModel):
    customer_id: str
    name: str
    email: str
    tier: str
    refund_count_90d: int
    risk_flag: bool
    notes: str


class Order(BaseModel):
    order_id: str
    customer_id: str
    product_name: str
    category: str
    price: float
    delivered_days_ago: int
    status: str
    condition_claimed: str
    final_sale: bool
    damaged_claim: bool
    photo_proof_available: bool
    payment_method: str
    country: str
    scenario_label: str = ""
    expected_decision: str = ""


class PolicyCheck(BaseModel):
    """One audited policy rule evaluation."""
    rule: str
    passed: Optional[bool] = None  # None = not strictly pass/fail (informational)
    status: CheckStatus = "success"
    detail: str = ""


class LogEntry(BaseModel):
    id: Optional[int] = None
    timestamp: str
    session_id: str
    step: str
    tool_name: str
    input_summary: str
    output_summary: str
    status: CheckStatus
    decision_snapshot: Optional[str] = None


class ChatRequest(BaseModel):
    customer_id: str = Field(..., examples=["CUST-001"])
    message: str = Field(..., examples=["I want to return my headphones, delivered 5 days ago, unused."])
    order_id: Optional[str] = None  # optional explicit order selection
    session_id: Optional[str] = None  # reuse to continue a conversation
    # Simulated proof workflow (the UI exposes these via buttons, not a real upload).
    proof_attached: bool = False
    proof_unavailable: bool = False
    attachment_type: Literal["photo", "video", "none", "simulated"] = "none"
    attachment_note: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    decision: Decision
    stage: Stage = "new_request"
    pending_requirement: PendingRequirement = "none"
    turn_count: int = 1
    response: str
    intent: Optional[RefundIntent] = None
    intent_method: str = "fallback"  # "llm" or "fallback"
    message_intent: str = "unknown"
    issue_category: str = "unknown"
    customer: Optional[Customer] = None
    order: Optional[Order] = None
    policy_checks: list[PolicyCheck] = []
    logs: list[LogEntry] = []
    llm_mode: str  # "llm" or "deterministic"


class HealthResponse(BaseModel):
    status: str
    app: str
    llm_enabled: bool
    llm_provider: str = "none"
    llm_model: Optional[str] = None
    ollama_reachable: Optional[bool] = None
    orchestrator: str
    customers: int
    orders: int


class PolicyResponse(BaseModel):
    markdown: str
    rules: list[str]
