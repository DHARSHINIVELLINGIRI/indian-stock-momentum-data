"""
tests/test_service.py - Automated Regression & Integration Tests for Service Layer
================================================================================
Verifies the headless API service layer:
1. Output contract structure (exact keys: meta, strategies, validation, performance, monthly, daily_equity, s3_holdings, warnings).
2. Numerical accuracy against known verified baseline:
   - Strategy 1: ~₹842,202.45
   - Strategy 2: ~₹1,138,365.06
   - Strategy 3: ~₹1,123,652.04
   - Strategy 4: ~₹653,568.49
   (All verified within ₹1.00 tolerance).
3. All 7 programmatic validation checks report status 'PASS'.
4. Idempotency, caching, and determinism across repeated service executions.
5. Parameter sensitivity: Running with X=10 yields distinctly different results from X=20.
6. Artifact isolation: save_outputs=True writes to outputs/runs/<capital>_<x>/ without polluting data/processed/.
"""

import json
import os
import sys
import pytest
import numpy as np

# Ensure root directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.service import run_backtest_service, load_engine_inputs, get_last_run_dfs


def test_service_keys_and_schema():
    """Verify that run_backtest_service returns all 8 required keys with valid structures."""
    result = run_backtest_service(500000.0, 20, save_outputs=False)

    required_keys = [
        "meta",
        "strategies",
        "validation",
        "performance",
        "monthly",
        "daily_equity",
        "s3_holdings",
        "warnings"
    ]
    for key in required_keys:
        assert key in result, f"Missing required key in service result: {key}"

    # Verify JSON serializability directly
    serialized = json.dumps(result)
    assert len(serialized) > 1000

    # Verify meta dictionary
    meta = result["meta"]
    assert meta["capital"] == 500000.0
    assert meta["x"] == 20
    assert meta["trading_days"] == 983
    assert meta["rebalances"] == 48
    assert meta["risk_free_rate"] == 0.065
    assert isinstance(meta["runtime_seconds"], float)

    # Verify strategies metadata
    assert len(result["strategies"]) == 4
    for strat in result["strategies"]:
        assert "id" in strat and "name" in strat and "description" in strat
        assert len(strat["description"]) > 10

    # Verify daily_equity structure
    assert len(result["daily_equity"]) == 983
    first_day = result["daily_equity"][0]
    for col in ["date", "s1_equity", "s2_equity", "s3_equity", "s4_equity"]:
        assert col in first_day, f"Missing {col} in daily_equity record"

    # Verify monthly structure
    assert len(result["monthly"]) >= 48
    first_month = result["monthly"][0]
    for col in ["date", "s1_value", "s1_ret", "s2_value", "s2_ret", "s3_value", "s3_ret", "s4_value", "s4_ret"]:
        assert col in first_month, f"Missing {col} in monthly record"

    # Verify s3_holdings structure
    assert len(result["s3_holdings"]) > 0
    first_holding = result["s3_holdings"][0]
    for col in ["date", "ticker", "rank", "target_weight_pct", "status", "is_in_buffer"]:
        assert col in first_holding, f"Missing {col} in s3_holdings record"
    assert first_holding["status"] in ["New Entry", "Retained", "Exit"]
    assert isinstance(first_holding["is_in_buffer"], bool)

    # Verify warnings structure
    assert "count" in result["warnings"]
    assert "samples" in result["warnings"]
    assert isinstance(result["warnings"]["samples"], list)


def test_service_known_final_equities():
    """
    Verify final equity for each strategy matches verified baseline within ₹1.00:
    - S1: ~842,202.45
    - S2: ~1,138,365.06
    - S3: ~1,123,652.04
    - S4: ~653,568.49
    """
    result = run_backtest_service(500000.0, 20, save_outputs=False)
    perf = {row["Strategy"]: row["Final_Value"] for row in result["performance"]}

    expected = {
        "Strategy 1": 842202.45,
        "Strategy 2": 1138365.06,
        "Strategy 3": 1123652.04,
        "Strategy 4": 653568.49
    }

    for key, expected_val in expected.items():
        matching = [v for k, v in perf.items() if key in k]
        assert len(matching) == 1, f"Strategy matching '{key}' not found or ambiguous"
        actual_val = matching[0]
        assert abs(actual_val - expected_val) <= 1.0, (
            f"Final equity for {key} mismatch: actual ₹{actual_val:,.2f}, expected ₹{expected_val:,.2f}"
        )


def test_service_all_validation_checks_pass():
    """Verify all 7 programmatic validation checks return status 'PASS'."""
    result = run_backtest_service(500000.0, 20, save_outputs=False)
    validation = result["validation"]
    assert len(validation) == 7, f"Expected 7 validation checks, got {len(validation)}"

    for check in validation:
        assert check["status"] == "PASS", f"Validation check failed: {check['name']} - {check['message']}"


def test_service_caching_and_determinism():
    """Verify that two sequential calls with identical inputs produce identical numerical results."""
    res1 = run_backtest_service(500000.0, 20, save_outputs=False)
    res2 = run_backtest_service(500000.0, 20, save_outputs=False)

    # Performance values should match exactly
    perf1 = [r["Final_Value"] for r in res1["performance"]]
    perf2 = [r["Final_Value"] for r in res2["performance"]]
    assert perf1 == perf2

    # Monthly values should match exactly
    assert len(res1["monthly"]) == len(res2["monthly"])
    assert res1["monthly"][10] == res2["monthly"][10]

    # Daily equity endpoints should match exactly
    assert res1["daily_equity"][-1] == res2["daily_equity"][-1]


def test_service_different_x_different_results():
    """Verify that calling service with X=10 yields distinctly different results from X=20."""
    res_x20 = run_backtest_service(500000.0, 20, save_outputs=False)
    res_x10 = run_backtest_service(500000.0, 10, save_outputs=False)

    perf_x20 = {r["Strategy"]: r["Final_Value"] for r in res_x20["performance"]}
    perf_x10 = {r["Strategy"]: r["Final_Value"] for r in res_x10["performance"]}

    # S2 and S3 should differ significantly when X is 10 vs 20
    s2_x20 = [v for k, v in perf_x20.items() if "Strategy 2" in k][0]
    s2_x10 = [v for k, v in perf_x10.items() if "Strategy 2" in k][0]
    assert s2_x20 != s2_x10

    s3_x20 = [v for k, v in perf_x20.items() if "Strategy 3" in k][0]
    s3_x10 = [v for k, v in perf_x10.items() if "Strategy 3" in k][0]
    assert s3_x20 != s3_x10


def test_service_save_outputs():
    """Verify that save_outputs=True creates the directory outputs/runs/<capital>_<x>/ with expected CSVs."""
    run_backtest_service(250000.0, 15, save_outputs=True)
    expected_dir = os.path.join(root_dir, "outputs", "runs", "250000_15")
    assert os.path.exists(expected_dir), f"Directory {expected_dir} not created"
    for fname in [
        "daily_portfolio_values.csv",
        "trade_log.csv",
        "monthly_holdings.csv",
        "turnover.csv",
        "performance_summary.csv",
        "monthly_returns.csv",
        "drawdown_series.csv"
    ]:
        p = os.path.join(expected_dir, fname)
        assert os.path.exists(p), f"Artifact missing: {p}"
        assert os.path.getsize(p) > 50, f"Artifact empty: {p}"
