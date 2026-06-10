"""Central configuration for RefundPilot AI.

All knobs live here. Nothing secret is hardcoded — the OpenAI key is read from
the environment only, and the app runs in deterministic mode when it is absent.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env if present (no-op if the file does not exist).
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

# --- Paths -----------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
POLICY_PATH = DATA_DIR / "refund_policy.md"
DB_PATH = Path(os.getenv("REFUNDPILOT_DB", str(BACKEND_DIR / "refundpilot.db")))

# --- LLM -------------------------------------------------------------------
# Provider selection: "auto" (prefer OpenAI key, else local Ollama if reachable,
# else deterministic), "openai", "ollama", or "none".
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").strip().lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip() or None

# Local Ollama (no internet, no key required).
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip().rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip()

# Kept low for demo responsiveness — any slower call falls back to deterministic.
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "8"))

# Whether to let the LLM rephrase the (already natural) reply templates. Off by
# default: templates are fast, precise, and natural enough, which keeps demo
# latency low. The LLM is still used for language UNDERSTANDING regardless.
LLM_REPHRASE = os.getenv("LLM_REPHRASE", "false").strip().lower() in ("1", "true", "yes", "on")

# Coarse hint only — the real, fail-safe resolution lives in app/llm.py
# (get_llm_status / resolve_provider). The agent runs fully without any LLM.
LLM_ENABLED = LLM_PROVIDER != "none" and (bool(OPENAI_API_KEY) or LLM_PROVIDER in ("ollama", "auto"))

# --- Business rules (single source of truth for thresholds) ----------------
STANDARD_WINDOW_DAYS = 30
ELECTRONICS_WINDOW_DAYS = 15
HIGH_VALUE_THRESHOLD = 25_000  # INR; orders above this need manual approval
REFUND_ABUSE_THRESHOLD = 3  # more than this many refunds in 90d -> escalate

# --- App -------------------------------------------------------------------
APP_NAME = "RefundPilot AI"
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
