"""RefundPilot AI — FastAPI application.

Endpoints:
  GET  /health
  GET  /customers
  GET  /orders
  GET  /policy
  POST /chat
  GET  /admin/logs
  GET  /admin/logs/{session_id}
  POST /seed   (dev: reset + reseed mock data)
"""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import config, database, llm, policy
from .agent import graph
from .schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    PolicyResponse,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    database.init_db()
    yield


app = FastAPI(title=config.APP_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    s = llm.get_llm_status()
    return HealthResponse(
        status="ok",
        app=config.APP_NAME,
        llm_enabled=s["enabled"],
        llm_provider=s["provider"],
        llm_model=s["model"],
        ollama_reachable=s["ollama_reachable"],
        orchestrator=graph.ORCHESTRATOR,
        customers=len(database.get_customers()),
        orders=len(database.get_orders()),
    )


@app.get("/customers")
def list_customers() -> list[dict]:
    return database.get_customers()


@app.get("/orders")
def list_orders(customer_id: str | None = None) -> list[dict]:
    return database.get_orders(customer_id)


@app.get("/policy", response_model=PolicyResponse)
def get_policy() -> PolicyResponse:
    return PolicyResponse(
        markdown=policy.read_policy_text(),
        rules=policy.get_policy_rules(),
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if not database.get_customer(req.customer_id):
        raise HTTPException(status_code=404, detail=f"Customer {req.customer_id} not found")

    # Reuse the conversation's session_id if the client sent one; else start new.
    session_id = req.session_id or f"sess-{uuid.uuid4().hex[:8]}"
    result = graph.run_agent(
        session_id=session_id,
        customer_id=req.customer_id,
        message=req.message,
        order_id=req.order_id,
        proof_attached=req.proof_attached,
        proof_unavailable=req.proof_unavailable,
    )
    return ChatResponse(
        session_id=session_id,
        decision=result.get("decision", "escalated"),
        stage=result.get("stage", "escalated"),
        pending_requirement=result.get("pending_requirement", "none"),
        turn_count=result.get("turn_count", 1),
        response=result.get("customer_response", ""),
        intent=result.get("intent"),
        intent_method=result.get("intent_method", "fallback"),
        message_intent=result.get("message_intent", "unknown"),
        issue_category=(result.get("intent") or {}).get("issue_category", "unknown"),
        customer=result.get("customer"),
        order=result.get("order"),
        policy_checks=result.get("policy_checks", []),
        logs=database.get_logs(session_id),
        llm_mode=result.get("llm_mode", "deterministic"),
    )


@app.get("/admin/logs")
def admin_logs(limit: int = 500) -> list[dict]:
    return database.get_logs(limit=limit)


@app.get("/admin/logs/{session_id}")
def admin_logs_for_session(session_id: str) -> list[dict]:
    return database.get_logs(session_id=session_id)


@app.post("/seed")
def seed() -> dict:
    database.reset_db()
    return {
        "status": "reseeded",
        "customers": len(database.get_customers()),
        "orders": len(database.get_orders()),
    }
