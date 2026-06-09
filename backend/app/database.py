"""SQLite persistence for RefundPilot AI.

Uses the stdlib `sqlite3` (no ORM) for speed and zero friction. Holds three
tables: customers, orders, and logs. Customers/orders are seeded from seed.py;
logs are written by the agent as it reasons.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from . import config
from .seed import CUSTOMERS, ORDERS


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(reset: bool = False) -> None:
    """Create tables and seed customer/order data. Idempotent."""
    conn = _connect()
    try:
        cur = conn.cursor()
        if reset:
            cur.executescript(
                "DROP TABLE IF EXISTS customers;"
                "DROP TABLE IF EXISTS orders;"
                "DROP TABLE IF EXISTS logs;"
                "DROP TABLE IF EXISTS support_sessions;"
            )
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id TEXT PRIMARY KEY,
                name TEXT, email TEXT, tier TEXT,
                refund_count_90d INTEGER, risk_flag INTEGER, notes TEXT
            );
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT, product_name TEXT, category TEXT,
                price REAL, delivered_days_ago INTEGER, status TEXT,
                condition_claimed TEXT, final_sale INTEGER, damaged_claim INTEGER,
                photo_proof_available INTEGER, payment_method TEXT, country TEXT
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, session_id TEXT, step TEXT, tool_name TEXT,
                input_summary TEXT, output_summary TEXT, status TEXT,
                decision_snapshot TEXT
            );
            CREATE TABLE IF NOT EXISTS support_sessions (
                session_id TEXT PRIMARY KEY,
                customer_id TEXT,
                selected_order_id TEXT,
                stage TEXT,
                last_decision TEXT,
                last_reason TEXT,
                pending_requirement TEXT,
                defect_claim_active INTEGER DEFAULT 0,
                proof_required INTEGER DEFAULT 0,
                proof_received INTEGER DEFAULT 0,
                clarification_question TEXT,
                turn_count INTEGER DEFAULT 0,
                updated_at TEXT
            );
            """
        )
        # Seed only if empty.
        if cur.execute("SELECT COUNT(*) AS n FROM customers").fetchone()["n"] == 0:
            cur.executemany(
                "INSERT INTO customers VALUES (:customer_id,:name,:email,:tier,"
                ":refund_count_90d,:risk_flag,:notes)",
                [{**c, "risk_flag": int(c["risk_flag"])} for c in CUSTOMERS],
            )
        if cur.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"] == 0:
            cur.executemany(
                "INSERT INTO orders VALUES (:order_id,:customer_id,:product_name,:category,"
                ":price,:delivered_days_ago,:status,:condition_claimed,:final_sale,"
                ":damaged_claim,:photo_proof_available,:payment_method,:country)",
                [
                    {
                        **o,
                        "final_sale": int(o["final_sale"]),
                        "damaged_claim": int(o["damaged_claim"]),
                        "photo_proof_available": int(o["photo_proof_available"]),
                    }
                    for o in ORDERS
                ],
            )
        conn.commit()
    finally:
        conn.close()


def reset_db() -> None:
    init_db(reset=True)


# --- Read helpers ----------------------------------------------------------
def _order_from_row(row: sqlite3.Row) -> dict[str, Any]:
    o = dict(row)
    o["final_sale"] = bool(o["final_sale"])
    o["damaged_claim"] = bool(o["damaged_claim"])
    o["photo_proof_available"] = bool(o["photo_proof_available"])
    return o


def _customer_from_row(row: sqlite3.Row) -> dict[str, Any]:
    c = dict(row)
    c["risk_flag"] = bool(c["risk_flag"])
    return c


def get_customers() -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM customers ORDER BY customer_id").fetchall()
        return [_customer_from_row(r) for r in rows]
    finally:
        conn.close()


def get_customer(customer_id: str) -> Optional[dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
        ).fetchone()
        return _customer_from_row(row) if row else None
    finally:
        conn.close()


def get_orders(customer_id: Optional[str] = None) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        if customer_id:
            rows = conn.execute(
                "SELECT * FROM orders WHERE customer_id = ? ORDER BY delivered_days_ago",
                (customer_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM orders ORDER BY order_id").fetchall()
        return [_order_from_row(r) for r in rows]
    finally:
        conn.close()


def get_order(order_id: str) -> Optional[dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM orders WHERE order_id = ?", (order_id,)
        ).fetchone()
        return _order_from_row(row) if row else None
    finally:
        conn.close()


# --- Logs ------------------------------------------------------------------
def add_log(
    session_id: str,
    step: str,
    tool_name: str,
    input_summary: str,
    output_summary: str,
    status: str,
    decision_snapshot: Optional[str] = None,
) -> dict[str, Any]:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_id": session_id,
        "step": step,
        "tool_name": tool_name,
        "input_summary": input_summary,
        "output_summary": output_summary,
        "status": status,
        "decision_snapshot": decision_snapshot,
    }
    conn = _connect()
    try:
        cur = conn.execute(
            "INSERT INTO logs (timestamp,session_id,step,tool_name,input_summary,"
            "output_summary,status,decision_snapshot) VALUES "
            "(:timestamp,:session_id,:step,:tool_name,:input_summary,:output_summary,"
            ":status,:decision_snapshot)",
            entry,
        )
        conn.commit()
        entry["id"] = cur.lastrowid
        return entry
    finally:
        conn.close()


def get_logs(session_id: Optional[str] = None, limit: int = 500) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        if session_id:
            rows = conn.execute(
                "SELECT * FROM logs WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# --- Support sessions (multi-turn conversation state) ----------------------
_BOOL_FIELDS = ("defect_claim_active", "proof_required", "proof_received")


def get_session(session_id: str) -> Optional[dict[str, Any]]:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM support_sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            return None
        s = dict(row)
        for f in _BOOL_FIELDS:
            s[f] = bool(s.get(f))
        return s
    finally:
        conn.close()


def save_session(state: dict[str, Any]) -> None:
    """Upsert a support session. Unknown keys are ignored."""
    record = {
        "session_id": state["session_id"],
        "customer_id": state.get("customer_id"),
        "selected_order_id": state.get("selected_order_id"),
        "stage": state.get("stage", "new_request"),
        "last_decision": state.get("last_decision"),
        "last_reason": state.get("last_reason"),
        "pending_requirement": state.get("pending_requirement", "none"),
        "defect_claim_active": int(bool(state.get("defect_claim_active"))),
        "proof_required": int(bool(state.get("proof_required"))),
        "proof_received": int(bool(state.get("proof_received"))),
        "clarification_question": state.get("clarification_question"),
        "turn_count": int(state.get("turn_count", 1)),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO support_sessions (session_id,customer_id,selected_order_id,"
            "stage,last_decision,last_reason,pending_requirement,defect_claim_active,"
            "proof_required,proof_received,clarification_question,turn_count,updated_at) "
            "VALUES (:session_id,:customer_id,:selected_order_id,:stage,:last_decision,"
            ":last_reason,:pending_requirement,:defect_claim_active,:proof_required,"
            ":proof_received,:clarification_question,:turn_count,:updated_at) "
            "ON CONFLICT(session_id) DO UPDATE SET "
            "customer_id=excluded.customer_id, selected_order_id=excluded.selected_order_id, "
            "stage=excluded.stage, last_decision=excluded.last_decision, "
            "last_reason=excluded.last_reason, pending_requirement=excluded.pending_requirement, "
            "defect_claim_active=excluded.defect_claim_active, proof_required=excluded.proof_required, "
            "proof_received=excluded.proof_received, clarification_question=excluded.clarification_question, "
            "turn_count=excluded.turn_count, updated_at=excluded.updated_at",
            record,
        )
        conn.commit()
    finally:
        conn.close()
