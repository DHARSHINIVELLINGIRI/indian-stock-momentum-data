"""
src/service.py - Service Layer for Quantitative Momentum Strategy Backtesting Engine
===================================================================================
Provides a clean, headless API-ready service layer for FastAPI backend and CLI orchestration.

Features:
- load_engine_inputs(): Module-level cached data ingestion for sub-second backtests.
- run_backtest_service(): Headless execution returning a comprehensive JSON-serializable dictionary.
- Seamless output isolation: Zero file overwrites unless explicitly requested via save_outputs=True.
"""

import inspect
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

# Ensure project root is in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.backtest import (
    INITIAL_CAPITAL,
    X,
    build_execution_schedule,
    load_backtest_inputs,
    run_four_strategy_backtest,
    run_validation_checks,
    select_strategy_1_holdings,
    select_strategy_2_holdings,
    select_strategy_3_holdings,
)
from src.metrics import (
    RISK_FREE_RATE,
    TRADING_DAYS_PER_YEAR,
    build_performance_summary,
    compute_drawdown_series,
    compute_monthly_returns,
)

# Module-level cache for point-in-time datasets
_CACHED_INPUTS: Optional[Tuple] = None
_LAST_RUN_DFS: Optional[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]] = None


def load_engine_inputs() -> Tuple:
    """
    Loads and caches (module-level) the cleaned price matrices, rankings,
    benchmark dataset, trading calendar, and rebalancing schedule exactly
    once per process.
    """
    global _CACHED_INPUTS
    if _CACHED_INPUTS is None:
        open_matrix, close_matrix, rankings_df, benchmark_df, all_trading_dates = load_backtest_inputs()
        schedule = build_execution_schedule(rankings_df, all_trading_dates)
        _CACHED_INPUTS = (
            open_matrix,
            close_matrix,
            rankings_df,
            benchmark_df,
            all_trading_dates,
            schedule,
        )
    return _CACHED_INPUTS


def get_last_run_dfs() -> Optional[Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    """
    Returns the raw pandas DataFrames (daily_df, trades_df, holdings_df, turnover_df)
    generated during the most recent service execution.
    """
    global _LAST_RUN_DFS
    return _LAST_RUN_DFS


def _clean_json_val(val: Any) -> Any:
    """
    Recursively normalizes Python/numpy/pandas values to strictly JSON-compliant types.
    """
    if val is None:
        return None
    if isinstance(val, (bool, np.bool_)):
        return bool(val)
    if isinstance(val, dict):
        return {str(k): _clean_json_val(v) for k, v in val.items()}
    if isinstance(val, (list, tuple, set)):
        return [_clean_json_val(x) for x in val]
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        if np.isnan(val) or np.isinf(val):
            return None
        return float(val)
    if isinstance(val, (pd.Timestamp, pd.Period)):
        return str(val)
    if isinstance(val, str):
        return val
    try:
        if pd.isna(val):
            return None
    except Exception:
        pass
    return val


def get_strategy_metadata() -> List[Dict[str, Any]]:
    """
    Dynamically generates strategy metadata and descriptions from code docstrings.
    """
    def clean_doc(doc: Optional[str], fallback: str) -> str:
        if not doc:
            return fallback
        return inspect.cleandoc(doc).strip()

    return [
        {
            "id": 1,
            "name": "Strategy 1 - Top-X Buy-and-Hold",
            "description": clean_doc(
                select_strategy_1_holdings.__doc__,
                "Top-X Buy-and-Hold: Select Top X stocks on first decision date and hold forever."
            ),
        },
        {
            "id": 2,
            "name": "Strategy 2 - Top-X Equal-Weight Momentum (2X Buffer)",
            "description": clean_doc(
                select_strategy_2_holdings.__doc__,
                "Top-X Equal-Weight with 2X Retention Buffer: Retain held stocks ranked <= 2X; 1/X equal weights."
            ),
        },
        {
            "id": 3,
            "name": "Strategy 3 - Top-X Rank-Weighted Momentum (No Buffer)",
            "description": clean_doc(
                select_strategy_3_holdings.__doc__,
                "Top-X Rank-Weighted Momentum (No Buffer): Pure Top X with linear rank-based weights."
            ),
        },
        {
            "id": 4,
            "name": "Strategy 4 - NIFTYBEES Benchmark Buy-and-Hold",
            "description": (
                "STRATEGY 4 (NIFTYBEES Benchmark Buy-and-Hold):\n"
                "- Buy and hold NIFTYBEES.NS standalone index benchmark ETF.\n"
                "- 100% allocation at inception with zero rebalancing."
            ),
        },
    ]


_get_strategy_metadata = get_strategy_metadata



def run_backtest_service(
    capital: float = INITIAL_CAPITAL,
    x: int = X,
    save_outputs: bool = False
) -> Dict[str, Any]:
    """
    Runs the 4-strategy quantitative momentum simulation headlessly and returns
    a fully JSON-serializable dictionary.

    Parameters:
    - capital: Initial investment amount in INR.
    - x: Number of top stocks to hold.
    - save_outputs: When True, writes CSV artifacts to outputs/runs/<capital>_<x>/

    Returns:
    Dictionary containing:
    - meta
    - strategies
    - validation
    - performance
    - monthly
    - daily_equity
    - s3_holdings
    - warnings
    """
    global _LAST_RUN_DFS
    start_time = time.time()

    # 1. Fetch preloaded & cached datasets
    cached_inputs = load_engine_inputs()
    open_matrix, close_matrix, rankings_df, benchmark_df, all_trading_dates, schedule = cached_inputs

    # 2. Execute discrete portfolio simulation headlessly
    daily_df, trades_df, holdings_df, turnover_df, warnings_list = run_four_strategy_backtest(
        initial_capital=float(capital),
        X_target=int(x),
        preloaded_inputs=cached_inputs,
        verbose=False,
    )
    _LAST_RUN_DFS = (daily_df, trades_df, holdings_df, turnover_df)

    # 3. Validation Suite Checks (Silent)
    val_dict = run_validation_checks(daily_df, trades_df, schedule, verbose=False)
    validation_records = [
        {
            "id": idx,
            "name": check_name,
            "status": "PASS" if passed else "FAIL",
            "message": msg,
        }
        for idx, (check_name, (passed, msg)) in enumerate(val_dict.items(), 1)
    ]

    # 4. Performance Metrics & Master Summary Table
    drawdown_series_df, dd_stats = compute_drawdown_series(daily_df)
    summary_df = build_performance_summary(
        daily_df=daily_df,
        trades_df=trades_df,
        turnover_df=turnover_df,
        dd_stats=dd_stats,
        rf_annual=RISK_FREE_RATE,
        trading_days_per_year=TRADING_DAYS_PER_YEAR,
    )

    performance_records = summary_df.replace({np.nan: None}).to_dict(orient="records")
    performance_records = _clean_json_val(performance_records)

    # 5. Month-by-Month Performance Series
    df_m = daily_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_m["Date"]):
        df_m["Date"] = pd.to_datetime(df_m["Date"])
    df_m["YearMonth"] = df_m["Date"].dt.to_period("M")

    strat_code_map = {}
    for s in df_m["Strategy"].unique():
        for code in ["1", "2", "3", "4"]:
            if f"Strategy {code}" in s:
                strat_code_map[s] = f"s{code}"
                break

    month_ends = df_m.sort_values("Date").groupby(["Strategy", "YearMonth"]).last().reset_index()
    month_ends["StratCode"] = month_ends["Strategy"].map(strat_code_map)
    month_ends["Monthly_Return_%"] = month_ends.groupby("Strategy")["Total_Equity"].pct_change() * 100.0

    pivot_val = month_ends.pivot(index="Date", columns="StratCode", values="Total_Equity")
    pivot_ret = month_ends.pivot(index="Date", columns="StratCode", values="Monthly_Return_%")

    monthly_records = []
    for dt in sorted(pivot_val.index):
        dt_str = dt.strftime("%Y-%m-%d")
        row_dict = {"date": dt_str}
        for s_id in ["s1", "s2", "s3", "s4"]:
            v = pivot_val.loc[dt, s_id] if s_id in pivot_val.columns and dt in pivot_val.index else None
            r = pivot_ret.loc[dt, s_id] if s_id in pivot_ret.columns and dt in pivot_ret.index else None
            row_dict[f"{s_id}_value"] = round(float(v), 2) if v is not None and pd.notnull(v) else None
            row_dict[f"{s_id}_ret"] = round(float(r), 4) if r is not None and pd.notnull(r) else 0.0
        monthly_records.append(row_dict)

    # 6. Daily Equity Series (All 4 Strategies)
    pivot_daily = df_m.pivot(index="Date", columns="Strategy", values="Total_Equity")
    col_remap = {}
    for c in pivot_daily.columns:
        for code in ["1", "2", "3", "4"]:
            if f"Strategy {code}" in c:
                col_remap[c] = f"s{code}_equity"
                break
    pivot_daily = pivot_daily.rename(columns=col_remap)

    daily_equity_records = []
    for dt in sorted(pivot_daily.index):
        dt_str = dt.strftime("%Y-%m-%d")
        row_dict = {"date": dt_str}
        for col in ["s1_equity", "s2_equity", "s3_equity", "s4_equity"]:
            val = pivot_daily.loc[dt, col] if col in pivot_daily.columns else None
            row_dict[col] = round(float(val), 2) if val is not None and pd.notnull(val) else None
        daily_equity_records.append(row_dict)

    # 7. Monthly Holdings Breakdown for Strategy 3
    s3_h = holdings_df[holdings_df["Strategy"].str.contains("Strategy 3")].copy()
    s3_h["date_str"] = pd.to_datetime(s3_h["Date"]).dt.strftime("%Y-%m-%d")
    exec_dates = sorted(s3_h["date_str"].unique())

    rankings_copy = rankings_df.copy()
    rankings_copy["dec_str"] = pd.to_datetime(rankings_copy["decision_date"]).dt.strftime("%Y-%m-%d")
    dec_dates = sorted(rankings_copy["dec_str"].unique())

    exec_to_dec = {}
    for ed in exec_dates:
        priors = [dd for dd in dec_dates if dd < ed]
        exec_to_dec[ed] = priors[-1] if priors else ed

    s3_holdings_records = []
    prev_held: Set[str] = set()

    for ed in exec_dates:
        m_end = exec_to_dec.get(ed, ed)
        sub_ranks = rankings_copy[rankings_copy["dec_str"] == m_end]
        curr_ranks = sub_ranks.set_index("ticker")["rank"].to_dict()

        month_sub = s3_h[s3_h["date_str"] == ed]
        held_tickers = set(month_sub["Ticker"].tolist())

        active_rows = []
        for _, row in month_sub.iterrows():
            t = str(row["Ticker"])
            rk = curr_ranks.get(t, None)
            wt = round(float(row["Target_Weight"]) * 100.0, 4)
            status = "Retained" if t in prev_held else "New Entry"
            is_in_buf = bool(rk is not None and rk <= 2 * x)
            active_rows.append({
                "date": m_end,
                "ticker": t,
                "rank": int(rk) if rk is not None else None,
                "target_weight_pct": wt,
                "status": status,
                "is_in_buffer": is_in_buf,
            })
        active_rows.sort(key=lambda r: (r["rank"] if r["rank"] is not None else 9999, r["ticker"]))

        exited_tickers = sorted(prev_held - held_tickers)
        exit_rows = []
        for t in exited_tickers:
            rk = curr_ranks.get(t, None)
            is_in_buf = bool(rk is not None and rk <= 2 * x)
            exit_rows.append({
                "date": m_end,
                "ticker": t,
                "rank": int(rk) if rk is not None else None,
                "target_weight_pct": 0.0,
                "status": "Exit",
                "is_in_buffer": is_in_buf,
            })
        exit_rows.sort(key=lambda r: (r["rank"] if r["rank"] is not None else 9999, r["ticker"]))

        s3_holdings_records.extend(active_rows + exit_rows)
        prev_held = held_tickers

    runtime_sec = time.time() - start_time

    # 8. Metadata
    first_dec_date_ts = schedule[0]["decision_date"]
    sim_trading_days = len(all_trading_dates[all_trading_dates >= first_dec_date_ts])

    meta_dict = {
        "capital": float(capital),
        "x": int(x),
        "first_date": schedule[0]["decision_date"].strftime("%Y-%m-%d"),
        "last_date": all_trading_dates.iloc[-1].strftime("%Y-%m-%d"),
        "trading_days": int(sim_trading_days),
        "rebalances": int(len(schedule)),
        "runtime_seconds": round(float(runtime_sec), 3),
        "risk_free_rate": float(RISK_FREE_RATE),
    }

    warnings_dict = {
        "count": len(warnings_list),
        "samples": warnings_list[:20],
    }

    # 9. Artifact Export (Only if save_outputs=True)
    if save_outputs:
        cap_tag = f"{int(capital)}" if float(capital).is_integer() else f"{capital}"
        run_dir = os.path.join(project_root, "outputs", "runs", f"{cap_tag}_{x}")
        os.makedirs(run_dir, exist_ok=True)

        daily_df.to_csv(os.path.join(run_dir, "daily_portfolio_values.csv"), index=False)
        trades_df.to_csv(os.path.join(run_dir, "trade_log.csv"), index=False)
        holdings_df.to_csv(os.path.join(run_dir, "monthly_holdings.csv"), index=False)
        turnover_df.to_csv(os.path.join(run_dir, "turnover.csv"), index=False)
        summary_df.to_csv(os.path.join(run_dir, "performance_summary.csv"), index=False)
        compute_monthly_returns(daily_df).to_csv(os.path.join(run_dir, "monthly_returns.csv"), index=False)
        drawdown_series_df.to_csv(os.path.join(run_dir, "drawdown_series.csv"), index=False)

    # 10. Assemble complete JSON-compliant dictionary
    result = {
        "meta": meta_dict,
        "strategies": _get_strategy_metadata(),
        "validation": validation_records,
        "performance": performance_records,
        "monthly": monthly_records,
        "daily_equity": daily_equity_records,
        "s3_holdings": s3_holdings_records,
        "warnings": warnings_dict,
    }

    # Clean to ensure 100% JSON-serializability
    clean_result = _clean_json_val(result)
    # Sanity check serialization
    json.dumps(clean_result)

    return clean_result
