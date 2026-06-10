"""Customer-conversation simulator — acts like a QA customer across all profiles.

Replays every multi-turn flow in app/qa.py (clean returns, defects, proof
attach/unavailable, policy-window/eligibility/email questions, pressure, typos,
safety hazards, warranty, high-value, cancelled, gift, international...) against
the in-process agent, and prints per-turn: message intent, decision, stage,
latency, and pass/fail against the expected behaviour.

Run from the backend/ directory:
    .venv\\Scripts\\python.exe scripts\\simulate_customer_conversations.py

Deterministic by default (LLM_PROVIDER=none) so it is a reliable gate; export
LLM_PROVIDER before running to exercise OpenAI/Ollama live instead.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["REFUNDPILOT_DB"] = _tmp.name
os.environ.setdefault("LLM_PROVIDER", "none")

from app import database, qa  # noqa: E402

GREEN, RED, YELLOW, DIM, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"
SLOW_MS = 3000  # deterministic turns over this are flagged (not failed)


def main() -> int:
    database.reset_db()
    print(f"\nRefundPilot AI — customer-conversation simulator ({len(qa.FLOWS)} conversations)")
    print("=" * 84)
    total = passed = slow = 0
    worst_ms = 0
    for flow in qa.FLOWS:
        sid = f"sim-{uuid.uuid4().hex[:8]}"
        print(f"\n{flow['name']}  {DIM}({flow['customer']} · {sid}){RESET}")
        for i, turn in enumerate(flow["turns"], 1):
            t0 = time.perf_counter()
            result = qa.run_turn(sid, flow["customer"], turn)
            ms = int((time.perf_counter() - t0) * 1000)
            worst_ms = max(worst_ms, ms)
            err = qa.check_turn(turn, result)
            total += 1
            passed += err is None
            slow += ms > SLOW_MS
            tag = f"{GREEN}PASS{RESET}" if err is None else f"{RED}FAIL{RESET}"
            lat = f"{YELLOW}{ms}ms{RESET}" if ms > SLOW_MS else f"{ms}ms"
            print(f"  [{tag}] turn {i} [{lat}] \"{turn['msg'][:58]}\"")
            print(f"         intent={result.get('message_intent')} | decision={result['decision']} "
                  f"| stage={result['stage']}")
            if err:
                print(f"         {RED}{err}{RESET}")
            print(f"         {DIM}reply: {result['response'][:88]}{RESET}")
    print("\n" + "=" * 84)
    verdict = f"{GREEN}ALL PASS{RESET}" if passed == total else f"{RED}{total - passed} FAILED{RESET}"
    print(f"{passed}/{total} turns passed — {verdict} · worst latency {worst_ms}ms · "
          f"{slow} turn(s) over {SLOW_MS}ms")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
