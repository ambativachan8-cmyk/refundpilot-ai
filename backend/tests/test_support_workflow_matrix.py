"""Scenario matrix as assertions. Runs every QA flow and checks expectations.

The critical safety property: no defect / no-proof / internal-issue flow may ever
become `approved`, while clean approvals and policy violations still behave.
"""
import pytest

from app import database, qa


@pytest.fixture(autouse=True, scope="module")
def _db():
    database.reset_db()
    yield


@pytest.mark.parametrize("flow", qa.FLOWS, ids=[f["name"] for f in qa.FLOWS])
def test_flow(flow):
    rows = qa.run_flow(flow)
    failures = [f"  turn {r['turn']}: {r['error']} (msg: {r['message']!r})"
                for r in rows if r["error"]]
    assert not failures, f"\n{flow['name']} failed:\n" + "\n".join(failures)


def test_no_flow_wrongly_approves_a_defect():
    """Hard safety sweep: any turn flagged not_approved must not be approved."""
    for flow in qa.FLOWS:
        for row, turn in zip(qa.run_flow(flow), flow["turns"]):
            if turn.get("not_approved"):
                assert row["decision"] != "approved", (
                    f"{flow['name']} turn {row['turn']} wrongly approved")
