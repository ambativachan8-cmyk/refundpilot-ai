"""Pytest setup: use a throwaway SQLite DB and never call a real LLM."""
import os
import tempfile

# Point the app at a temp DB BEFORE importing app modules (config reads env at import).
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["REFUNDPILOT_DB"] = _tmp.name
os.environ.pop("OPENAI_API_KEY", None)  # force deterministic mode in tests
