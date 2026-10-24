"""
tests/test_api.py - Integration Tests for FastAPI Backend
=========================================================
Tests:
1. GET /api/health returns status 200 and {"status": "ok"}.
2. GET /api/strategies returns status 200 with 4 dynamic strategy definitions.
3. POST /api/run with valid parameters (500000, 20) succeeds, returns 200, low_capital_warning=False.
4. POST /api/run with invalid parameters returns 422 Unprocessable Entity.
5. POST /api/run with low capital per stock triggers low_capital_warning=True.
6. Caching behavior: Repeated calls with identical parameters return instantaneous cached responses.
"""

import os
import sys
import time
import pytest
from fastapi.testclient import TestClient

# Ensure root directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from api.main import app, CACHE


@pytest.fixture(scope="module")
def client():
    """
    Module-scoped TestClient fixture triggering the FastAPI lifespan manager
    (preloading point-in-time matrices and rankings once for all tests).
    """
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    """Verify service liveness endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_strategies(client):
    """Verify that strategies endpoint returns dynamic metadata for all 4 strategies."""
    response = client.get("/api/strategies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 4

    for strat in data:
        assert "id" in strat
        assert "name" in strat
        assert "description" in strat
        assert len(strat["description"]) > 10

    strategy_names = [s["name"] for s in data]
    assert any("Strategy 1" in name for name in strategy_names)
    assert any("Strategy 2" in name for name in strategy_names)
    assert any("Strategy 3" in name for name in strategy_names)
    assert any("Strategy 4" in name for name in strategy_names)


def test_post_run_valid(client):
    """Verify that POST /api/run executes with valid inputs and returns full simulation schema."""
    payload = {"capital": 500000.0, "x": 20}
    response = client.post("/api/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify low_capital_warning appended at root
    assert "low_capital_warning" in data
    assert data["low_capital_warning"] is False

    # Verify all service layer keys are present
    expected_keys = [
        "meta",
        "strategies",
        "validation",
        "performance",
        "monthly",
        "daily_equity",
        "s3_holdings",
        "warnings",
        "low_capital_warning",
    ]
    for key in expected_keys:
        assert key in data, f"Missing key in response: {key}"

    # Verify meta parameters
    assert data["meta"]["capital"] == 500000.0
    assert data["meta"]["x"] == 20

    # Verify all validation checks passed
    assert len(data["validation"]) == 7
    for check in data["validation"]:
        assert check["status"] == "PASS"


def test_post_run_invalid_inputs(client):
    """Verify that invalid parameters fail Pydantic validation with 422 Unprocessable Entity."""
    # Capital below 10,000 and X below 5
    res1 = client.post("/api/run", json={"capital": 5000.0, "x": 2})
    assert res1.status_code == 422

    # Capital above 100,000,000
    res2 = client.post("/api/run", json={"capital": 200000000.0, "x": 20})
    assert res2.status_code == 422

    # X above 50
    res3 = client.post("/api/run", json={"capital": 500000.0, "x": 100})
    assert res3.status_code == 422

    # Missing parameters
    res4 = client.post("/api/run", json={})
    assert res4.status_code == 422


def test_post_run_low_capital_warning(client):
    """Verify that capital per stock < 2,000 sets low_capital_warning to True."""
    # 15,000 / 10 = 1,500 < 2,000
    payload = {"capital": 15000.0, "x": 10}
    response = client.post("/api/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["low_capital_warning"] is True


def test_caching_and_performance(client):
    """
    Verify in-memory caching:
    - First call computes simulation.
    - Second call hits cache instantaneously.
    """
    param_capital = 450000.0
    param_x = 15
    cache_key = (param_capital, param_x)
    CACHE.pop(cache_key, None)

    # First call: cache miss
    t0 = time.time()
    res1 = client.post("/api/run", json={"capital": param_capital, "x": param_x})
    miss_duration = time.time() - t0
    assert res1.status_code == 200
    assert cache_key in CACHE

    # Second call: cache hit
    t1 = time.time()
    res2 = client.post("/api/run", json={"capital": param_capital, "x": param_x})
    hit_duration = time.time() - t1
    assert res2.status_code == 200

    # Cache hit should be near-instantaneous (< 50ms)
    assert hit_duration < 0.1, f"Cache hit took too long: {hit_duration:.4f}s"
    assert hit_duration < miss_duration
    assert res1.json() == res2.json()
