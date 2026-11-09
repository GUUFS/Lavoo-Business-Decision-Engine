"""
Runs the end-to-end payment simulation (tests/simulation/payment_simulation.py)
as part of the test suite: a smaller population than the default command-line
run, in its own process and its own throwaway database (lavoo_sim), so it
can't affect the other tests' database.

Fails if the simulation finds any violation; the full report (every event and
check) is written to a temporary folder and its path printed on failure.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def test_payment_and_payout_simulation_has_no_violations(tmp_path):
    base = os.getenv("TEST_DATABASE_URL")
    if not base:
        pytest.skip("TEST_DATABASE_URL not set (needs a local Postgres with pgvector)")
    env = {**os.environ, "SIM_BASE_DATABASE_URL": base}
    env.pop("DATABASE_URL", None)
    proc = subprocess.run(
        [sys.executable, "-W", "ignore", "-m", "tests.simulation.payment_simulation",
         "--seed", "5", "--referrers", "8", "--referrals-each", "3", "--out", str(tmp_path)],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=900,
    )
    report = json.loads((tmp_path / "report.json").read_text())
    summary, violations = report["summary"], report["violations"]
    assert not violations, f"{len(violations)} violation(s), see {tmp_path / 'report.md'}: {violations[:5]}"
    assert proc.returncode == 0, proc.stderr[-2000:]
    # The run must actually have exercised the system, not passed vacuously.
    assert summary["payments"] >= 50 and summary["checks"] >= 500
    coverage = summary["coverage"]
    for scenario in ("stripe_first", "stripe_renewal", "flutterwave_first", "flutterwave_renewal",
                     "duplicate_webhook_ignored", "underpayment_refused"):
        assert coverage.get(scenario, 0) > 0, f"scenario not exercised: {scenario}"
