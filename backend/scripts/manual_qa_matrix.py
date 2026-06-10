"""Manual QA matrix — runnable scenario sweep with a readable pass/fail table.

Run from the backend/ directory:
    .venv\\Scripts\\python.exe scripts\\manual_qa_matrix.py

Uses the in-process agent (no server needed) against a throwaway SQLite DB so it
never touches your dev data.
"""
from __future__ import annotations

import os
import sys
import tempfile

# Make `app` importable and point at a throwaway DB before importing app modules.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["REFUNDPILOT_DB"] = _tmp.name
# Deterministic by default so the matrix is a reliable gate. Override by exporting
# LLM_PROVIDER before running if you want to exercise OpenAI/Ollama live.
os.environ.setdefault("LLM_PROVIDER", "none")

from app import database, qa  # noqa: E402

GREEN, RED, DIM, RESET = "\033[92m", "\033[91m", "\033[2m", "\033[0m"


def main() -> int:
    database.reset_db()
    print(f"\nRefundPilot AI — scenario QA matrix ({len(qa.FLOWS)} flows)\n" + "=" * 78)
    total = passed = 0
    for flow in qa.FLOWS:
        for r in qa.run_flow(flow):
            total += 1
            ok = r["error"] is None
            passed += ok
            tag = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
            label = f"{r['flow']}" + (f" · turn {r['turn']}" if len(flow["turns"]) > 1 else "")
            print(f"[{tag}] {label}")
            print(f"       {DIM}{r['customer']} · \"{r['message'][:70]}\"{RESET}")
            print(f"       -> decision={r['decision']} | stage={r['stage']}")
            if not ok:
                print(f"       {RED}{r['error']}{RESET}")
            print(f"       {DIM}reply: {r['response'][:90]}{RESET}")
    print("=" * 78)
    status = f"{GREEN}ALL PASS{RESET}" if passed == total else f"{RED}{total - passed} FAILED{RESET}"
    print(f"{passed}/{total} checks passed — {status}\n")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
