"""
api/main.py - FastAPI Backend for Quantitative Momentum Backtesting System
==========================================================================
Provides REST API endpoints to interface with the quantitative backtesting engine:
- GET /api/health: Service liveness healthcheck.
- GET /api/strategies: Dynamic metadata for all 4 backtested strategies.
- POST /api/run: Dynamic portfolio simulation with caching, concurrency lock, and validation.
"""

import asyncio
from contextlib import asynccontextmanager
import logging
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root is available in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.service import (
    get_strategy_metadata,
    load_engine_inputs,
    run_backtest_service,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("api.main")

# In-memory result cache: (capital, x) -> result dict
CACHE: Dict[Tuple[float, int], Dict[str, Any]] = {}

# Simulation lock: serializes backtest executions to prevent concurrent memory spikes
SIMULATION_LOCK = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Server lifespan manager:
    Preloads and caches all cleaned price matrices, momentum rankings, calendar,
    and benchmark data exactly once at startup.
    """
    logger.info("Initializing quantitative momentum backtest engine...")
    t_start = time.time()
    try:
        load_engine_inputs()
        load_duration = time.time() - t_start
        logger.info(f"Engine inputs preloaded and cached successfully in {load_duration:.3f}s.")
    except Exception as exc:
        logger.error(f"Failed to preload engine inputs at startup: {exc}\n{traceback.format_exc()}")
        raise exc
    yield
    logger.info("Shutting down API server...")


app = FastAPI(
    title="Quantitative Momentum Backtesting API",
    description="High-performance backend API serving quantitative momentum strategy backtests.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for React frontend (Vite dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunBacktestRequest(BaseModel):
    capital: float = Field(
        ...,
        ge=10000.0,
        le=100000000.0,
        description="Total initial investment capital in INR (min 10,000, max 100,000,000)",
    )
    x: int = Field(
        ...,
        ge=5,
        le=50,
        description="Number of top momentum stocks to hold (min 5, max 50)",
    )


@app.get("/api/health")
def health_check() -> Dict[str, str]:
    """
    Service health check endpoint.
    """
    return {"status": "ok"}


@app.get("/api/strategies")
def get_strategies() -> List[Dict[str, Any]]:
    """
    Returns metadata and descriptions for all 4 strategies extracted dynamically
    from the service layer docstrings.
    """
    try:
        return get_strategy_metadata()
    except Exception as exc:
        logger.error(f"Error retrieving strategy metadata: {exc}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve strategy metadata from engine.",
        )


@app.post("/api/run")
async def run_backtest(
    request: RunBacktestRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Executes the quantitative backtest simulation with dynamic parameters:
    - Validates capital in [10,000, 100,000,000] and X in [5, 50].
    - Evaluates low-capital safety warning ((capital / X) < 2000).
    - Checks in-memory cache keyed by (capital, X).
    - Serializes concurrent simulations using asyncio.Lock.
    - Offloads CPU execution to thread to avoid blocking event loop.
    - Guarantees save_outputs=False to isolate processed directory.
    """
    cache_key = (float(request.capital), int(request.x))

    # Fast path: check cache before acquiring simulation lock
    if cache_key in CACHE:
        logger.info(f"Cache hit for capital={request.capital}, x={request.x}")
        return CACHE[cache_key]

    async with SIMULATION_LOCK:
        # Double-check cache in case another request computed it while waiting for lock
        if cache_key in CACHE:
            logger.info(f"Cache hit for capital={request.capital}, x={request.x}")
            return CACHE[cache_key]

        logger.info(f"Cache miss for capital={request.capital}, x={request.x}. Executing backtest...")
        try:
            # Run CPU-bound simulation in worker thread
            result = await asyncio.to_thread(
                run_backtest_service,
                capital=request.capital,
                x=request.x,
                save_outputs=False,
            )

            # Append low-capital safety warning at the root level
            low_capital_warning = bool((request.capital / request.x) < 2000.0)
            result["low_capital_warning"] = low_capital_warning

            # Store in cache
            CACHE[cache_key] = result
            return result
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Backtest simulation failed: {exc}\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An internal error occurred while executing the backtest simulation.",
            )
