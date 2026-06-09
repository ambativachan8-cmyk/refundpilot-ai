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


class ChatResponse(BaseModel):
    session_id: str
    decision: Decision
    response: str
    customer: Optional[Customer] = None
    order: Optional[Order] = None
    policy_checks: list[PolicyCheck] = []
    logs: list[LogEntry] = []
    llm_mode: str  # "llm" or "deterministic"


class HealthResponse(BaseModel):
    status: str
    app: str
    llm_enabled: bool
    orchestrator: str
    customers: int
    orders: int


class PolicyResponse(BaseModel):
    markdown: str
    rules: list[str]
