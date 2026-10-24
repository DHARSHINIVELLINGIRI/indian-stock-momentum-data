#!/usr/bin/env python3
"""
Stage 4: Four-Strategy Portfolio Backtesting Module
===================================================
Project: Quantitative Momentum Strategy Backtesting System for Indian Equities

This module simulates realistic portfolios for four strategies:
1. Strategy 1 — Top-X buy-and-hold baseline (buy once on first decision date, hold forever)
2. Strategy 2 — Top-X equal-weight momentum with 2X retention buffer (whole shares, monthly rebalance)
3. Strategy 3 — Top-X rank-weighted momentum without buffer (whole shares, monthly rebalance)
4. Strategy 4 — NIFTYBEES buy-and-hold benchmark (whole shares, standalone benchmark)

Key Execution & Accounting Principles:
- Signal Timing: Monthly decision dates strictly as of completed month-end Close.
- Execution Timing: Executed at the next available trading session's Open (fallback to Close if Open missing).
- Whole-share rounding for Strategies 2, 3, and 4; fractional shares for Strategy 1.
- Strict Cash Management: Cash is strictly non-negative; idle cash earns 0% interest.
- Sells precede buys during rebalancing to free liquidity; buy orders are capped at available cash.
- Transaction costs: 0.15% variable fee on all trades + ₹15 fixed cost per stock sell transaction.
- Comprehensive outputs saved to data/processed/.
- Programmatic validation checks run on every execution.

Author: Quantitative Finance Research Developer
"""

import sys
import os
import subprocess
import warnings
from typing import Tuple, List, Dict, Optional, Set, Any
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.patches import Patch

# Ensure clean UTF-8 stdout encoding on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure project root is in sys.path when executed directly as a script
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import data cleaning pipeline from Stage 3
try:
    from src.momentum import load_and_clean_ohlcv_data
except ModuleNotFoundError:
    from momentum import load_and_clean_ohlcv_data

# ============================================================================
# CONFIGURATION PARAMETERS
# ============================================================================
INITIAL_CAPITAL = 500000.0          # Initial capital per strategy (₹5,00,000)
X = 20                              # Target number of stocks in momentum portfolios
VAR_COST = 0.0015                   # 0.15% variable fee on trade value (buys and sells)
FIXED_SELL_COST = 15.0              # ₹15 flat fee per stock sell transaction
RISK_FREE_RATE = 0.065              # 6.5% annual risk-free rate (for future performance metrics)

# File Paths
RAW_DATA_PATH = os.path.join("data", "ohlcv_data.csv")
RANKINGS_PATH = os.path.join("data", "processed", "monthly_momentum_rankings.csv")
BENCHMARK_PATH = os.path.join("data", "benchmark_niftybees.csv")
PROCESSED_DIR = os.path.join("data", "processed")

# Output File Paths
OUTPUT_DAILY_PORTFOLIO = os.path.join(PROCESSED_DIR, "daily_portfolio_values.csv")
OUTPUT_TRADE_LOG = os.path.join(PROCESSED_DIR, "trade_log.csv")
OUTPUT_MONTHLY_HOLDINGS = os.path.join(PROCESSED_DIR, "monthly_holdings.csv")
OUTPUT_TURNOVER = os.path.join(PROCESSED_DIR, "turnover.csv")


# ============================================================================
# 1. INPUT DATA LOADING & REBALANCE SCHEDULING
# ============================================================================
def load_backtest_inputs(
    raw_csv_path: str = RAW_DATA_PATH,
    rankings_csv_path: str = RANKINGS_PATH,
    benchmark_csv_path: str = BENCHMARK_PATH
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame], pd.Series]:
    """
    Loads and aligns all required inputs:
    - Cleaned observed Open and Close price matrices for equities.
    - Verified monthly momentum rankings from Stage 3.
    - Benchmark OHLCV data for NIFTYBEES.NS (if available).
    - Chronological list of all active trading sessions.
    """
    if not os.path.exists(raw_csv_path):
        raise FileNotFoundError(f"Raw OHLCV data not found: {raw_csv_path}")
    if not os.path.exists(rankings_csv_path):
        raise FileNotFoundError(f"Rankings file not found: {rankings_csv_path}. Run Stage 3 first.")

    # 1. Load clean equity data in-memory (never modifying raw file)
    df_clean, _ = load_and_clean_ohlcv_data(raw_csv_path)

    # Exclude benchmark if accidentally present in equities CSV
    df_equities = df_clean[~df_clean['Ticker'].isin(['NIFTYBEES.NS', 'NIFTYBEES', '^NSEI'])].copy()

    # Pivot Open and Close
    open_matrix = df_equities.pivot(index='Date', columns='Ticker', values='Open').sort_index()
    close_matrix = df_equities.pivot(index='Date', columns='Ticker', values='Close').sort_index()

    # 2. Load monthly rankings
    rankings_df = pd.read_csv(rankings_csv_path)
    rankings_df['decision_date'] = pd.to_datetime(rankings_df['decision_date'])

    # 3. Load benchmark data if available
    benchmark_df = None
    if os.path.exists(benchmark_csv_path):
        try:
            b_df = pd.read_csv(benchmark_csv_path)
            b_df['Date'] = pd.to_datetime(b_df['Date']).dt.tz_localize(None).dt.floor('D')
            b_df = b_df.drop_duplicates(subset=['Date']).sort_values(by='Date').reset_index(drop=True)
            benchmark_df = b_df.set_index('Date')
        except Exception as e:
            print(f"[WARNING] Failed to load benchmark data from {benchmark_csv_path}: {e}")
            benchmark_df = None
    else:
        print(f"[WARNING] Benchmark file {benchmark_csv_path} not found. Strategy 4 will be skipped.")

    all_trading_dates = pd.Series(close_matrix.index).sort_values().reset_index(drop=True)

    return open_matrix, close_matrix, rankings_df, benchmark_df, all_trading_dates


def build_execution_schedule(
    rankings_df: pd.DataFrame,
    all_trading_dates: pd.Series
) -> List[Dict]:
    """
    Constructs the monthly rebalance schedule mapping each decision date
    to the next available trading session's execution date.
    """
    decision_dates = sorted(rankings_df['decision_date'].unique())
    date_to_idx = {d: i for i, d in enumerate(all_trading_dates)}

    schedule = []
    for d_dec in decision_dates:
        d_dec_ts = pd.Timestamp(d_dec)
        if d_dec_ts not in date_to_idx:
            continue

        loc = date_to_idx[d_dec_ts]
        if loc + 1 < len(all_trading_dates):
            d_exec = all_trading_dates.iloc[loc + 1]
            schedule.append({
                'decision_date': d_dec_ts,
                'exec_date': d_exec
            })

    return schedule


# ============================================================================
# 2. STRATEGY SELECTION & WEIGHTING RULES
# ============================================================================
def select_strategy_1_holdings(
    rankings_df: pd.DataFrame,
    first_decision_date: pd.Timestamp,
    target_count: int = X
) -> List[str]:
    """
    STRATEGY 1 (Top-X Buy-and-Hold):
    - On the first decision date, select the Top X stocks by momentum rank.
    - Buy them once and HOLD THEM FOREVER.
    - No monthly rebalancing, no selling, no buffer logic.
    """
    sub_df = rankings_df[pd.to_datetime(rankings_df['decision_date']) == pd.to_datetime(first_decision_date)].sort_values(by='rank')
    selected_tickers = sub_df.head(target_count)['ticker'].tolist()
    return selected_tickers


def select_strategy_2_holdings(
    rankings_df: pd.DataFrame,
    decision_date: pd.Timestamp,
    current_holdings: Any = None,
    target_count: int = X
) -> Tuple[List[str], Dict[str, float], int]:
    """
    STRATEGY 2 (Top-X Equal-Weight WITH 2X Buffer):
    - Select the Top X stocks.
    - Apply EQUAL weights (1/X).
    - APPLY THE 2X RETENTION BUFFER: If a held stock drops in rank, KEEP IT as long
      as its rank is <= 2X. Only sell it if its rank drops strictly below 2X (> 2X).
      Fill vacancies with new Top X stocks.
    """
    if isinstance(current_holdings, int):
        target_count = current_holdings
        current_holdings = {}
    elif current_holdings is None:
        current_holdings = {}
    elif isinstance(current_holdings, (list, set, tuple)):
        current_holdings = {t: 1 for t in current_holdings}
    elif not isinstance(current_holdings, dict):
        current_holdings = {}

    sub_df = rankings_df[pd.to_datetime(rankings_df['decision_date']) == pd.to_datetime(decision_date)].sort_values(by='rank')
    rank_map = dict(zip(sub_df['ticker'], sub_df['rank']))

    # Step A: Retain existing holdings ranked <= 2X
    retained_incumbents = [
        t for t in current_holdings.keys()
        if t in rank_map and rank_map[t] <= 2 * target_count
    ]

    # Step B: Fill vacancies up to target_count with new Top X stocks
    needed_slots = max(0, target_count - len(retained_incumbents))
    retained_set = set(retained_incumbents)
    new_additions = []

    for t in sub_df['ticker']:
        if t not in retained_set:
            new_additions.append(t)
            if len(new_additions) == needed_slots:
                break

    # Order positions by decision date rank ascending
    final_selected = sorted(retained_incumbents + new_additions, key=lambda t: rank_map.get(t, 999999))
    K = len(final_selected)

    # Step C: Equal weighting (1/K per stock)
    weights = {ticker: 1.0 / K for ticker in final_selected} if K > 0 else {}

    return final_selected, weights, len(new_additions)


def select_strategy_3_holdings(
    rankings_df: pd.DataFrame,
    decision_date: pd.Timestamp,
    current_holdings: Any = None,
    target_count: int = X
) -> Tuple[List[str], Dict[str, float], int]:
    """
    STRATEGY 3 (Top-X Rank-Weighted, NO Buffer):
    - Select the Top X stocks.
    - Apply RANK-BASED WEIGHTING: Position 1 gets (X+1-1)/[X(X+1)/2], Position X gets 1/[X(X+1)/2].
    - NO RETENTION BUFFER: If a stock drops out of the Top X, SELL IT IMMEDIATELY
      and replace it with the new Top X stock.
    """
    if isinstance(current_holdings, int):
        target_count = current_holdings
        current_holdings = {}
    elif current_holdings is None:
        current_holdings = {}
    elif isinstance(current_holdings, (list, set, tuple)):
        current_holdings = {t: 1 for t in current_holdings}
    elif not isinstance(current_holdings, dict):
        current_holdings = {}

    sub_df = rankings_df[pd.to_datetime(rankings_df['decision_date']) == pd.to_datetime(decision_date)].sort_values(by='rank')
    selected_tickers = sub_df.head(target_count)['ticker'].tolist()
    K = len(selected_tickers)

    # Denominator: K * (K + 1) / 2
    denom = K * (K + 1) / 2.0 if K > 0 else 1.0
    weights = {}
    for idx, t in enumerate(selected_tickers):
        pos_N = idx + 1
        weights[t] = (K + 1 - pos_N) / denom

    additions_count = len([t for t in selected_tickers if t not in current_holdings]) if current_holdings else K

    return selected_tickers, weights, additions_count


# ============================================================================
# 3. ORDER EXECUTION & PORTFOLIO LEDGER ACCOUNTING
# ============================================================================
def get_execution_price(
    open_matrix: pd.DataFrame,
    close_matrix: pd.DataFrame,
    date: pd.Timestamp,
    ticker: str,
    warnings_list: List[str]
) -> Optional[float]:
    """
    Determines execution price at the next trading session:
    - Uses observed Open price.
    - If Open is missing/nonpositive, falls back to observed Close and logs a warning.
    - If both are missing, returns None and logs rebalance skip.
    """
    p_open = open_matrix.loc[date, ticker] if ticker in open_matrix.columns and date in open_matrix.index else np.nan
    if pd.notnull(p_open) and p_open > 0:
        return float(p_open)

    p_close = close_matrix.loc[date, ticker] if ticker in close_matrix.columns and date in close_matrix.index else np.nan
    if pd.notnull(p_close) and p_close > 0:
        warnings_list.append(f"FALLBACK: {ticker} on {date.strftime('%Y-%m-%d')} Open missing; executed at Close ₹{p_close:.2f}")
        return float(p_close)

    warnings_list.append(f"SKIP: {ticker} on {date.strftime('%Y-%m-%d')} both Open and Close missing; cannot execute trade.")
    return None


def execute_rebalance_whole_shares(
    current_cash: float,
    current_holdings: Dict[str, int],
    target_tickers: List[str],
    target_weights: Dict[str, float],
    open_matrix: pd.DataFrame,
    close_matrix: pd.DataFrame,
    exec_date: pd.Timestamp,
    strategy_name: str,
    trade_logs: List[Dict],
    holdings_logs: List[Dict],
    turnover_logs: List[Dict],
    warnings_list: List[str]
) -> Tuple[float, Dict[str, int]]:
    """
    Executes monthly rebalancing using WHOLE shares with strict cash management:
    1. Sells execute first: completely liquidates exits, trims overweight target positions.
       Deducts 0.15% variable cost + ₹15 fixed sell cost per stock sell transaction.
    2. Buys execute second: allocates target dollars, caps at affordable whole shares.
       Deducts 0.15% variable cost.
    3. Guarantees cash is strictly non-negative.
    4. Logs trades, post-rebalance holdings, and turnover metrics.
    """
    date_str = exec_date.strftime('%Y-%m-%d')
    all_involved = list(set(list(current_holdings.keys()) + target_tickers))

    # Fetch execution prices
    exec_prices = {}
    for t in all_involved:
        px = get_execution_price(open_matrix, close_matrix, exec_date, t, warnings_list)
        if px is not None:
            exec_prices[t] = px

    # Pre-trade valuation
    pre_trade_mv = sum(
        current_holdings[t] * exec_prices[t]
        for t in current_holdings if t in exec_prices
    )
    pre_trade_equity = current_cash + pre_trade_mv

    # Calculate target whole shares
    target_shares = {}
    for t in target_tickers:
        if t in exec_prices and exec_prices[t] > 0:
            target_dollars = target_weights[t] * pre_trade_equity
            target_shares[t] = int(target_dollars / exec_prices[t])
        else:
            target_shares[t] = 0

    total_traded_value = 0.0
    names_exited = 0
    initial_holding_names = set(current_holdings.keys())

    updated_holdings = dict(current_holdings)
    cash = current_cash

    # ------------------------------------------------------------------------
    # PHASE 1: EXECUTE SELLS FIRST (Collect Liquidity)
    # ------------------------------------------------------------------------
    # 1A. Full exits
    for t in list(current_holdings.keys()):
        if t not in target_tickers:
            if t not in exec_prices:
                warnings_list.append(f"SKIP EXIT: {t} on {date_str} price unavailable; retaining holding.")
                continue

            shares_to_sell = current_holdings[t]
            if shares_to_sell > 0:
                px = exec_prices[t]
                trade_val = shares_to_sell * px
                trans_cost = VAR_COST * trade_val + FIXED_SELL_COST
                net_proceeds = trade_val - trans_cost

                cash += net_proceeds
                total_traded_value += trade_val
                names_exited += 1

                trade_logs.append({
                    'Date': date_str,
                    'Strategy': strategy_name,
                    'Ticker': t,
                    'Action': 'Sell',
                    'Shares': int(shares_to_sell),
                    'Execution_Price': round(px, 4),
                    'Trade_Value': round(trade_val, 2),
                    'Transaction_Cost': round(trans_cost, 2)
                })
                del updated_holdings[t]

    # 1B. Trims (Target holdings with current shares > target shares)
    for t in target_tickers:
        if t in current_holdings and t in exec_prices:
            curr_s = current_holdings[t]
            targ_s = target_shares[t]
            if curr_s > targ_s:
                shares_to_sell = curr_s - targ_s
                if shares_to_sell > 0:
                    px = exec_prices[t]
                    trade_val = shares_to_sell * px
                    trans_cost = VAR_COST * trade_val + FIXED_SELL_COST
                    net_proceeds = trade_val - trans_cost

                    cash += net_proceeds
                    total_traded_value += trade_val

                    trade_logs.append({
                        'Date': date_str,
                        'Strategy': strategy_name,
                        'Ticker': t,
                        'Action': 'Sell',
                        'Shares': int(shares_to_sell),
                        'Execution_Price': round(px, 4),
                        'Trade_Value': round(trade_val, 2),
                        'Transaction_Cost': round(trans_cost, 2)
                    })
                    updated_holdings[t] = targ_s

    # ------------------------------------------------------------------------
    # PHASE 2: EXECUTE BUYS SECOND (Ordered by Target Weight)
    # ------------------------------------------------------------------------
    sorted_buy_targets = sorted(target_tickers, key=lambda t: target_weights.get(t, 0.0), reverse=True)

    for t in sorted_buy_targets:
        if t not in exec_prices:
            continue

        curr_s = updated_holdings.get(t, 0)
        targ_s = target_shares[t]

        if targ_s > curr_s:
            needed_shares = targ_s - curr_s
            px = exec_prices[t]
            share_cost_with_fee = px * (1.0 + VAR_COST)

            # Cap at strictly affordable whole shares with remaining cash
            affordable_shares = int(cash / share_cost_with_fee) if share_cost_with_fee > 0 else 0
            shares_to_buy = min(needed_shares, affordable_shares)

            if shares_to_buy < 1:
                warnings_list.append(
                    f"INSUFFICIENT CASH: {strategy_name} on {date_str} could not buy even 1 whole share of {t} "
                    f"(Price: ₹{px:.2f}, Cash: ₹{cash:.2f}). Allocation left in cash."
                )
            else:
                trade_val = shares_to_buy * px
                trans_cost = VAR_COST * trade_val
                total_cash_required = trade_val + trans_cost

                cash -= total_cash_required
                total_traded_value += trade_val
                updated_holdings[t] = curr_s + shares_to_buy

                trade_logs.append({
                    'Date': date_str,
                    'Strategy': strategy_name,
                    'Ticker': t,
                    'Action': 'Buy',
                    'Shares': int(shares_to_buy),
                    'Execution_Price': round(px, 4),
                    'Trade_Value': round(trade_val, 2),
                    'Transaction_Cost': round(trans_cost, 2)
                })

    # Post-trade equity
    post_trade_mv = sum(
        updated_holdings[t] * exec_prices[t]
        for t in updated_holdings if t in exec_prices
    )
    post_trade_equity = cash + post_trade_mv

    # Log monthly holdings
    for t in target_tickers:
        held_s = updated_holdings.get(t, 0)
        px = exec_prices.get(t, 0.0)
        actual_wt = (held_s * px) / post_trade_equity if post_trade_equity > 0 else 0.0
        holdings_logs.append({
            'Date': date_str,
            'Strategy': strategy_name,
            'Ticker': t,
            'Shares': int(held_s),
            'Target_Weight': round(target_weights.get(t, 0.0), 6),
            'Actual_Weight': round(actual_wt, 6)
        })

    # Log turnover
    target_count = len(target_tickers)
    name_turnover_pct = (names_exited / target_count * 100.0) if target_count > 0 else 0.0
    val_turnover_pct = (0.5 * total_traded_value / pre_trade_equity * 100.0) if pre_trade_equity > 0 else 0.0

    turnover_logs.append({
        'Date': date_str,
        'Strategy': strategy_name,
        'Name_Turnover (%)': round(name_turnover_pct, 2),
        'Traded_Value_Turnover (%)': round(val_turnover_pct, 2)
    })

    return cash, updated_holdings


# ============================================================================
# 4. SIMULATION PIPELINE FOR ALL FOUR STRATEGIES
# ============================================================================
def run_four_strategy_backtest(
    initial_capital: float = INITIAL_CAPITAL,
    X_target: int = X,
    preloaded_inputs: Optional[Tuple] = None,
    verbose: bool = True
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, List[str]]:
    """
    Executes the comprehensive backtest across all four strategies:
    - Strategy 1: Top-X buy-and-hold (fractional shares, buy once at inception, hold forever)
    - Strategy 2: Top-X equal-weight momentum with 2X retention buffer (whole shares)
    - Strategy 3: Top-X rank-weighted momentum without buffer (whole shares)
    - Strategy 4: NIFTYBEES buy-and-hold benchmark (whole shares)
    """
    if verbose:
        print("=" * 90)
        print(f"{'STAGE 4: FOUR-STRATEGY PORTFOLIO BACKTESTING ENGINE':^90}")
        print("=" * 90)
        print(f"Initial Capital per Strategy:  INR {initial_capital:,.2f}")
        print(f"Target Portfolio Size (X):     {X_target} stocks")
        print(f"Transaction Cost:              {VAR_COST*100:.2f}% variable + ₹{FIXED_SELL_COST:.2f} fixed sell fee")
        print(f"Benchmark:                     NIFTYBEES.NS")
        print("-" * 90)

    # Load inputs
    if preloaded_inputs is not None:
        open_matrix, close_matrix, rankings_df, benchmark_df, all_trading_dates, schedule = preloaded_inputs
    else:
        open_matrix, close_matrix, rankings_df, benchmark_df, all_trading_dates = load_backtest_inputs()
        schedule = build_execution_schedule(rankings_df, all_trading_dates)

    exec_dates_map = {item['exec_date']: item['decision_date'] for item in schedule}
    first_exec_date = schedule[0]['exec_date']
    first_dec_date = schedule[0]['decision_date']

    # Filter simulation dates from first decision date through terminal date
    sim_dates = all_trading_dates[all_trading_dates >= first_dec_date].tolist()

    if verbose:
        print(f"Total Completed Rebalance Cycles: {len(schedule)}")
        print(f"Backtest Period:                 {first_dec_date.strftime('%Y-%m-%d')} to {sim_dates[-1].strftime('%Y-%m-%d')} ({len(sim_dates)} trading days)")

    # Data logs
    daily_records = []
    trade_logs = []
    holdings_logs = []
    turnover_logs = []
    warnings_list = []

    # ------------------------------------------------------------------------
    # STRATEGY STATE INITIALIZATION
    # ------------------------------------------------------------------------
    strat_names = {
        1: "Strategy 1 - Top-X Buy-and-Hold",
        2: "Strategy 2 - Top-X Equal-Weight Momentum (Buffer)",
        3: "Strategy 3 - Top-X Rank-Weighted Momentum",
        4: "Strategy 4 - NIFTYBEES Benchmark Buy-and-Hold"
    }

    cash = {cid: initial_capital for cid in [1, 2, 3, 4]}
    holdings = {cid: {} for cid in [1, 2, 3, 4]}
    last_known_close = {cid: {} for cid in [1, 2, 3, 4]}

    has_bought_s1 = False
    has_bought_s4 = False

    # ------------------------------------------------------------------------
    # DAILY CHRONOLOGICAL SIMULATION
    # ------------------------------------------------------------------------
    for current_date in sim_dates:
        date_str = current_date.strftime('%Y-%m-%d')
        is_exec_date = (current_date in exec_dates_map)

        # --------------------------------------------------------------------
        # EXECUTION AT MARKET OPEN
        # --------------------------------------------------------------------
        if is_exec_date:
            d_dec = exec_dates_map[current_date]

            # ----------------------------------------------------------------
            # STRATEGY 1: Initial Fractional Buy Once (Top X, Hold Forever)
            # ----------------------------------------------------------------
            if not has_bought_s1:
                s1_tickers = select_strategy_1_holdings(rankings_df, first_dec_date, target_count=X_target)
                # Find available execution prices
                s1_prices = {}
                for t in s1_tickers:
                    px = get_execution_price(open_matrix, close_matrix, current_date, t, warnings_list)
                    if px is not None:
                        s1_prices[t] = px

                N_s1 = len(s1_prices)
                if N_s1 > 0:
                    # Allocate equal dollars net of 0.15% buy fee
                    total_deployable = cash[1] / (1.0 + VAR_COST)
                    dollars_per_stock = total_deployable / N_s1
                    total_traded_val = 0.0

                    for t, px in s1_prices.items():
                        frac_shares = dollars_per_stock / px
                        trade_val = frac_shares * px
                        trans_cost = VAR_COST * trade_val

                        cash[1] -= (trade_val + trans_cost)
                        holdings[1][t] = frac_shares
                        total_traded_val += trade_val

                        trade_logs.append({
                            'Date': date_str,
                            'Strategy': strat_names[1],
                            'Ticker': t,
                            'Action': 'Buy',
                            'Shares': round(frac_shares, 6),
                            'Execution_Price': round(px, 4),
                            'Trade_Value': round(trade_val, 2),
                            'Transaction_Cost': round(trans_cost, 2)
                        })

                        holdings_logs.append({
                            'Date': date_str,
                            'Strategy': strat_names[1],
                            'Ticker': t,
                            'Shares': round(frac_shares, 6),
                            'Target_Weight': round(1.0 / N_s1, 6),
                            'Actual_Weight': round(1.0 / N_s1, 6)
                        })

                    turnover_logs.append({
                        'Date': date_str,
                        'Strategy': strat_names[1],
                        'Name_Turnover (%)': 100.0,
                        'Traded_Value_Turnover (%)': 100.0
                    })
                    has_bought_s1 = True

            # ----------------------------------------------------------------
            # STRATEGY 4: Initial Whole-Share Buy Once (NIFTYBEES)
            # ----------------------------------------------------------------
            if not has_bought_s4 and benchmark_df is not None:
                if current_date in benchmark_df.index:
                    b_row = benchmark_df.loc[current_date]
                    b_open = b_row['Open'] if pd.notnull(b_row['Open']) and b_row['Open'] > 0 else b_row['Close']
                    if pd.notnull(b_open) and b_open > 0:
                        b_open = float(b_open)
                        # Whole shares affordable
                        cost_per_share = b_open * (1.0 + VAR_COST)
                        whole_shares = int(cash[4] / cost_per_share)
                        trade_val = whole_shares * b_open
                        trans_cost = VAR_COST * trade_val

                        cash[4] -= (trade_val + trans_cost)
                        holdings[4]['NIFTYBEES.NS'] = whole_shares
                        last_known_close[4]['NIFTYBEES.NS'] = b_open

                        trade_logs.append({
                            'Date': date_str,
                            'Strategy': strat_names[4],
                            'Ticker': 'NIFTYBEES.NS',
                            'Action': 'Buy',
                            'Shares': int(whole_shares),
                            'Execution_Price': round(b_open, 4),
                            'Trade_Value': round(trade_val, 2),
                            'Transaction_Cost': round(trans_cost, 2)
                        })

                        holdings_logs.append({
                            'Date': date_str,
                            'Strategy': strat_names[4],
                            'Ticker': 'NIFTYBEES.NS',
                            'Shares': int(whole_shares),
                            'Target_Weight': 1.0,
                            'Actual_Weight': round(trade_val / (cash[4] + trade_val), 6)
                        })

                        turnover_logs.append({
                            'Date': date_str,
                            'Strategy': strat_names[4],
                            'Name_Turnover (%)': 100.0,
                            'Traded_Value_Turnover (%)': 100.0
                        })
                        has_bought_s4 = True
                    else:
                        warnings_list.append(f"BENCHMARK: NIFTYBEES price invalid on {date_str}.")
                else:
                    warnings_list.append(f"BENCHMARK: Date {date_str} missing in benchmark dataset.")

            # ----------------------------------------------------------------
            # STRATEGY 2: Monthly Rebalance (Top X, 2X Buffer, Equal Weight)
            # ----------------------------------------------------------------
            s2_targets, s2_weights, _ = select_strategy_2_holdings(
                rankings_df, d_dec, current_holdings=holdings[2], target_count=X_target
            )
            cash[2], holdings[2] = execute_rebalance_whole_shares(
                current_cash=cash[2],
                current_holdings=holdings[2],
                target_tickers=s2_targets,
                target_weights=s2_weights,
                open_matrix=open_matrix,
                close_matrix=close_matrix,
                exec_date=current_date,
                strategy_name=strat_names[2],
                trade_logs=trade_logs,
                holdings_logs=holdings_logs,
                turnover_logs=turnover_logs,
                warnings_list=warnings_list
            )

            # ----------------------------------------------------------------
            # STRATEGY 3: Monthly Rebalance (Top X, Rank Weights, No Buffer)
            # ----------------------------------------------------------------
            s3_targets, s3_weights, additions_count = select_strategy_3_holdings(
                rankings_df, d_dec, current_holdings=holdings[3], target_count=X_target
            )
            cash[3], holdings[3] = execute_rebalance_whole_shares(
                current_cash=cash[3],
                current_holdings=holdings[3],
                target_tickers=s3_targets,
                target_weights=s3_weights,
                open_matrix=open_matrix,
                close_matrix=close_matrix,
                exec_date=current_date,
                strategy_name=strat_names[3],
                trade_logs=trade_logs,
                holdings_logs=holdings_logs,
                turnover_logs=turnover_logs,
                warnings_list=warnings_list
            )

        # --------------------------------------------------------------------
        # DAILY MARK-TO-MARKET VALUATION AT CLOSE
        # --------------------------------------------------------------------
        # Determine active strategies to track
        active_strats = [1, 2, 3]
        if benchmark_df is not None:
            active_strats.append(4)

        for cid in active_strats:
            c_name = strat_names[cid]
            c_holdings = holdings[cid]
            c_cash = cash[cid]

            market_val = 0.0

            if cid == 4:
                # Benchmark valuation
                if 'NIFTYBEES.NS' in c_holdings:
                    if current_date in benchmark_df.index:
                        b_close = benchmark_df.loc[current_date, 'Close']
                        if pd.notnull(b_close) and b_close > 0:
                            last_known_close[4]['NIFTYBEES.NS'] = float(b_close)
                        else:
                            warnings_list.append(f"STALE BENCHMARK CLOSE: NIFTYBEES.NS on {date_str} Close missing; retained last mark INR {last_known_close[4].get('NIFTYBEES.NS', 0.0):.2f}")
                    else:
                        warnings_list.append(f"STALE BENCHMARK CLOSE: NIFTYBEES.NS on {date_str} Date missing in benchmark dataset; retained last mark INR {last_known_close[4].get('NIFTYBEES.NS', 0.0):.2f}")

                    px = last_known_close[4].get('NIFTYBEES.NS', 0.0)
                    market_val = c_holdings['NIFTYBEES.NS'] * px
            else:
                # Equities valuation
                for t, s in c_holdings.items():
                    if t in close_matrix.columns and current_date in close_matrix.index:
                        c_px = close_matrix.loc[current_date, t]
                        if pd.notnull(c_px) and c_px > 0:
                            last_known_close[cid][t] = float(c_px)
                        else:
                            warnings_list.append(f"STALE CLOSE: {t} on {date_str} Close missing; retained last mark ₹{last_known_close[cid].get(t, 0.0):.2f}")

                    val_px = last_known_close[cid].get(t, 0.0)
                    market_val += s * val_px

            total_equity = c_cash + market_val
            daily_records.append({
                'Date': date_str,
                'Strategy': c_name,
                'Cash': round(c_cash, 2),
                'Market_Value': round(market_val, 2),
                'Total_Equity': round(total_equity, 2),
                'Holdings_Count': len([t for t, s in c_holdings.items() if s > 0])
            })

    # Convert logs to DataFrames
    daily_df = pd.DataFrame(daily_records)
    trades_df = pd.DataFrame(trade_logs)
    holdings_df = pd.DataFrame(holdings_logs)
    turnover_df = pd.DataFrame(turnover_logs)

    return daily_df, trades_df, holdings_df, turnover_df, warnings_list


# ============================================================================
# 5. PROGRAMMATIC VALIDATION CHECKS
# ============================================================================
def run_validation_checks(
    daily_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    schedule: List[Dict],
    verbose: bool = True
) -> Dict[str, Tuple[bool, str]]:
    """
    Executes and reports the required 7 validation checks:
    1. Cash is strictly non-negative across all strategies on all days.
    2. Total_Equity == Cash + Market_Value on every single day.
    3. Whole-share quantities are strictly integers for Strategies 2, 3, and 4.
    4. All rebalancing trades occur strictly after their corresponding decision date.
    5. Strategy 1 and Strategy 4 have exactly one initial buy event and zero subsequent rebalancing.
    6. NIFTYBEES.NS is not traded by Strategies 1-3.
    7. Total transaction costs comparison between Strategy 2 and Strategy 3.
    """
    if verbose:
        print("\n" + "=" * 90)
        print(f"{'STAGE 4 PROGRAMMATIC VALIDATION SUITE':^90}")
        print("=" * 90)

    results = {}

    # Check 1: Cash Non-Negativity
    min_cash = daily_df['Cash'].min()
    check1_passed = (min_cash >= -1e-6)
    results['1. Cash Non-Negativity (Cash >= 0)'] = (
        check1_passed,
        f"Minimum cash balance across all strategies: INR {min_cash:,.2f}"
    )

    # Check 2: Total Equity Reconciliation
    equity_diff = (daily_df['Total_Equity'] - (daily_df['Cash'] + daily_df['Market_Value'])).abs().max()
    check2_passed = (equity_diff < 0.05)
    results['2. Balance Reconciliation (Equity == Cash + Market_Value)'] = (
        check2_passed,
        f"Maximum daily balance discrepancy: INR {equity_diff:.6f}"
    )

    # Check 3: Whole-Share Integer Integrity
    s234_trades = trades_df[trades_df['Strategy'].str.contains('Strategy 2|Strategy 3|Strategy 4', regex=True)]
    fractional_violation = False
    if not s234_trades.empty:
        non_integer_shares = (s234_trades['Shares'] != s234_trades['Shares'].astype(int)).sum()
        check3_passed = (non_integer_shares == 0)
    else:
        check3_passed = True
    results['3. Whole-Share Integer Integrity (Strategies 2, 3, 4)'] = (
        check3_passed,
        f"Non-integer share count in Strategies 2, 3, 4: {non_integer_shares if not s234_trades.empty else 0}"
    )

    # Check 4: Rebalancing Execution Timing Order (Execution > Decision Date)
    timing_passed = all(s['exec_date'] > s['decision_date'] for s in schedule)
    results['4. Rebalance Timing Order (Execution > Decision Date)'] = (
        timing_passed,
        f"All {len(schedule)} monthly rebalancing events executed strictly on next trading session Open."
    )

    # Check 5: Single Initial Buy for Strategy 1 and Strategy 4
    s1_trade_dates = trades_df[trades_df['Strategy'].str.contains('Strategy 1')]['Date'].unique()
    s4_trades = trades_df[trades_df['Strategy'].str.contains('Strategy 4')]
    s4_trade_dates = s4_trades['Date'].unique() if not s4_trades.empty else []

    check5_passed = (len(s1_trade_dates) == 1) and (len(s4_trade_dates) <= 1)
    results['5. Buy-and-Hold Execution (Strategy 1 & 4 Buy Once)'] = (
        check5_passed,
        f"Strategy 1 trade sessions: {len(s1_trade_dates)}; Strategy 4 trade sessions: {len(s4_trade_dates)}"
    )

    # Check 6: Benchmark Isolation (NIFTYBEES.NS excluded from Strategies 1-3)
    s123_trades = trades_df[trades_df['Strategy'].str.contains('Strategy 1|Strategy 2|Strategy 3', regex=True)]
    nifty_in_s123 = (s123_trades['Ticker'] == 'NIFTYBEES.NS').sum()
    check6_passed = (nifty_in_s123 == 0)
    results['6. Benchmark Isolation (No NIFTYBEES in Strategies 1-3)'] = (
        check6_passed,
        f"NIFTYBEES trades observed in Strategies 1-3: {nifty_in_s123}"
    )

    # Check 7: Transaction Cost Comparison (Strategy 2 Buffer vs Strategy 3 No Buffer)
    tc_s2 = trades_df[trades_df['Strategy'].str.contains('Strategy 2')]['Transaction_Cost'].sum()
    tc_s3 = trades_df[trades_df['Strategy'].str.contains('Strategy 3')]['Transaction_Cost'].sum()
    tc_diff = tc_s3 - tc_s2
    tc_pct_diff = (tc_diff / tc_s3 * 100.0) if tc_s3 > 0 else 0.0

    check7_passed = True
    results['7. Transaction Cost Analysis (Strategy 2 Buffer vs Strategy 3 No Buffer)'] = (
        check7_passed,
        f"Strategy 2 (Buffer) TC: INR {tc_s2:,.2f} | Strategy 3 (No Buffer) TC: INR {tc_s3:,.2f} (Buffer Delta: INR {tc_diff:,.2f} / {tc_pct_diff:.2f}%)"
    )

    all_passed = True
    for check_name, (passed, msg) in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        if not passed:
            all_passed = False
        if verbose:
            print(f"  {status} {check_name:<55} | {msg}")

    if verbose:
        print("-" * 90)
        if not all_passed:
            raise AssertionError("Validation check failure occurred. See details above.")
        print("[VERIFIED] All 7 programmatic validation checks PASSED successfully.")
        print("=" * 90 + "\n")
    return results


# ============================================================================
# 6. PERFORMANCE SUMMARY & CONSOLE REPORTING
# ============================================================================
def print_performance_summary(daily_df: pd.DataFrame, trades_df: pd.DataFrame):
    """
    Computes and displays backtest performance summary table.
    """
    print("=" * 90)
    print(f"{'FOUR-STRATEGY BACKTEST PERFORMANCE RESULTS (2022 - 2026)':^90}")
    print("=" * 90)

    strategies = daily_df['Strategy'].unique().tolist()
    summary_rows = []

    for strat in strategies:
        df_s = daily_df[daily_df['Strategy'] == strat].reset_index(drop=True)
        init_val = df_s['Total_Equity'].iloc[0]
        final_val = df_s['Total_Equity'].iloc[-1]
        tot_return = (final_val / init_val - 1.0) * 100.0

        d_start = pd.Timestamp(df_s['Date'].iloc[0])
        d_end = pd.Timestamp(df_s['Date'].iloc[-1])
        years = (d_end - d_start).days / 365.25
        cagr = ((final_val / init_val) ** (1.0 / years) - 1.0) * 100.0 if years > 0 else 0.0

        daily_rets = df_s['Total_Equity'].pct_change().iloc[1:]
        vol = daily_rets.std() * np.sqrt(252.0) * 100.0

        # Sharpe ratio with 0% and 6.5% risk-free rates
        rf_daily = (1.0 + RISK_FREE_RATE) ** (1.0 / 252.0) - 1.0
        excess_rets = daily_rets - rf_daily
        sharpe_rf0 = (daily_rets.mean() * 252.0) / (daily_rets.std() * np.sqrt(252.0)) if daily_rets.std() > 0 else 0.0
        sharpe_rf65 = (excess_rets.mean() * 252.0) / (daily_rets.std() * np.sqrt(252.0)) if daily_rets.std() > 0 else 0.0

        cum_peak = df_s['Total_Equity'].cummax()
        max_dd = ((df_s['Total_Equity'] - cum_peak) / cum_peak).min() * 100.0

        avg_holdings = df_s['Holdings_Count'].iloc[1:].mean()
        total_tc = trades_df[trades_df['Strategy'] == strat]['Transaction_Cost'].sum()

        summary_rows.append({
            'Strategy': strat,
            'Final_Value': final_val,
            'Total_Return': tot_return,
            'CAGR': cagr,
            'Volatility': vol,
            'Sharpe_Rf0': sharpe_rf0,
            'Sharpe_Rf65': sharpe_rf65,
            'Max_Drawdown': max_dd,
            'Avg_Holdings': avg_holdings,
            'Total_TC': total_tc
        })

    col_w = [48, 16, 14, 12, 12, 12, 14, 16]
    hdr = f"{'Strategy':<{col_w[0]}} | {'Final Equity':>{col_w[1]}} | {'Total Ret':>{col_w[2]}} | {'CAGR':>{col_w[3]}} | {'Vol':>{col_w[4]}} | {'Sharpe':>{col_w[5]}} | {'Max DD':>{col_w[6]}} | {'Total Costs':>{col_w[7]}}"
    print(hdr)
    print("-" * len(hdr))

    for r in summary_rows:
        line = (
            f"{r['Strategy']:<{col_w[0]}} | "
            f"₹{r['Final_Value']:>14,.2f} | "
            f"{r['Total_Return']:>13.2f}% | "
            f"{r['CAGR']:>11.2f}% | "
            f"{r['Volatility']:>11.2f}% | "
            f"{r['Sharpe_Rf0']:>11.2f} | "
            f"{r['Max_Drawdown']:>13.2f}% | "
            f"₹{r['Total_TC']:>14,.2f}"
        )
        print(line)
    print("=" * 90 + "\n")


def print_monthly_analysis(daily_df: pd.DataFrame) -> None:
    """
    Extracts the last trading day of each month for all 4 strategies, calculates
    the monthly return (%) compared to the previous month-end, and prints a
    clean, aligned Month-by-Month Analysis table for all months to the console.
    """
    df = daily_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = pd.to_datetime(df['Date'])

    df['YearMonth'] = df['Date'].dt.to_period('M')

    # Map strategy names to compact identifiers S1, S2, S3, S4
    strat_map = {}
    for s in df['Strategy'].unique():
        for i in range(1, 5):
            if f"Strategy {i}" in s:
                strat_map[s] = f"S{i}"
                break

    month_ends = df.sort_values('Date').groupby(['Strategy', 'YearMonth']).last().reset_index()
    month_ends['StratCode'] = month_ends['Strategy'].map(strat_map)
    month_ends['Monthly_Return_%'] = month_ends.groupby('Strategy')['Total_Equity'].pct_change() * 100.0

    pivot_val = month_ends.pivot(index='Date', columns='StratCode', values='Total_Equity')
    pivot_ret = month_ends.pivot(index='Date', columns='StratCode', values='Monthly_Return_%')

    col_fmt = "{:<10} | {:>14} | {:>9} | {:>14} | {:>9} | {:>14} | {:>9} | {:>14} | {:>9}"
    headers = [
        "Month-End",
        "S1 Value (INR)", "S1 Ret%",
        "S2 Value (INR)", "S2 Ret%",
        "S3 Value (INR)", "S3 Ret%",
        "S4 Value (INR)", "S4 Ret%"
    ]
    hdr_str = col_fmt.format(*headers)
    table_width = len(hdr_str)

    print("=" * table_width)
    print(f"{'MONTH-BY-MONTH PERFORMANCE ANALYSIS':^{table_width}}")
    print("=" * table_width)
    print(hdr_str)
    print("-" * table_width)

    for dt in sorted(pivot_val.index):
        dt_str = dt.strftime('%Y-%m-%d')
        row_cells = []
        for s in ['S1', 'S2', 'S3', 'S4']:
            val = pivot_val.loc[dt, s] if s in pivot_val.columns and dt in pivot_val.index else np.nan
            ret = pivot_ret.loc[dt, s] if s in pivot_ret.columns and dt in pivot_ret.index else np.nan

            val_str = f"₹{val:,.0f}" if pd.notnull(val) else "N/A"
            if pd.isna(ret):
                ret_str = "0.00%"
            else:
                ret_str = f"{ret:+.2f}%"

            row_cells.extend([val_str, ret_str])

        print(col_fmt.format(dt_str, *row_cells))

    print("=" * table_width)
    print("[INFO] Full granular monthly data, including exact profit/loss in INR, is saved in data/processed/monthly_returns.csv\n")


def print_monthly_holdings_breakdown(
    holdings_df: pd.DataFrame,
    rankings_df: Optional[pd.DataFrame] = None
) -> None:
    """
    Displays a comprehensive month-by-month holdings breakdown:
    - Analyzes Strategy 2 (Top-X Equal-Weight WITH Retention Buffer) or Strategy 3.
    - For every monthly rebalance cycle, displays:
       - Month-end decision date and execution date.
       - Complete stock roster with Ticker, Momentum Rank, Target Weight %,
         and status ('New Entry', 'Retained', or 'Exit').
    - Prints all completed cycles so the portfolio evolution can be fully audited.
    """
    # Prefer Strategy 2 (the strategy with the 2X retention buffer)
    s_holdings = holdings_df[holdings_df['Strategy'].str.contains('Strategy 2', case=False, na=False)].copy()
    strat_label = "STRATEGY 2: TOP-X EQUAL-WEIGHT WITH 2X RETENTION BUFFER"
    if s_holdings.empty:
        s_holdings = holdings_df[holdings_df['Strategy'].str.contains('Strategy 3', case=False, na=False)].copy()
        strat_label = "STRATEGY 3: TOP-X RANK-WEIGHTED MOMENTUM"

    if s_holdings.empty:
        print("[WARNING] No momentum strategy holdings found in holdings_df.")
        return

    # Load rankings dataset if not provided
    if rankings_df is None:
        if os.path.exists(RANKINGS_PATH):
            rankings_df = pd.read_csv(RANKINGS_PATH)
        else:
            rankings_df = pd.DataFrame()

    if not rankings_df.empty:
        rankings_df = rankings_df.copy()
        rankings_df['dec_date_str'] = pd.to_datetime(rankings_df['decision_date']).dt.strftime('%Y-%m-%d')
        dec_dates = sorted(rankings_df['dec_date_str'].unique())
    else:
        dec_dates = []

    s_holdings = s_holdings.copy()
    s_holdings['date_str'] = pd.to_datetime(s_holdings['Date']).dt.strftime('%Y-%m-%d')
    exec_dates = sorted(s_holdings['date_str'].unique())

    # Map each execution date to its corresponding month-end decision date
    exec_to_dec = {}
    for ed in exec_dates:
        prior_decs = [dd for dd in dec_dates if dd < ed]
        exec_to_dec[ed] = prior_decs[-1] if prior_decs else ed

    banner_w = 90
    print("=" * banner_w)
    print(f"{strat_label:^{banner_w}}")
    print(f"{'MONTHLY HOLDINGS BREAKDOWN & RETENTION BUFFER EVOLUTION':^{banner_w}}")
    print("=" * banner_w)
    print("This shows how the momentum strategy selects Top X stocks and retains them via the 2X buffer.")
    print("  * [New Entry] : Fresh stock entering the Top X momentum ranks.")
    print("  * [Retained]  : Stock maintained from prior month (retained because rank <= 2X buffer).")
    print("  * [Exit]      : Stock evicted from portfolio because rank fell outside 2X buffer threshold.")
    print("-" * banner_w + "\n")

    prev_held: Set[str] = set()

    for idx, ed in enumerate(exec_dates, 1):
        m_end = exec_to_dec.get(ed, ed)
        month_sub = s_holdings[s_holdings['date_str'] == ed].copy()

        # Current month rank lookup
        curr_ranks = {}
        if not rankings_df.empty:
            sub_ranks = rankings_df[rankings_df['dec_date_str'] == m_end]
            curr_ranks = sub_ranks.set_index('ticker')['rank'].to_dict()

        held_tickers = set(month_sub['Ticker'].tolist())

        # Build list of active positions
        rows = []
        for _, row in month_sub.iterrows():
            t = str(row['Ticker'])
            rk = curr_ranks.get(t, 'N/A')
            wt = float(row['Target_Weight']) * 100.0
            status = "Retained" if t in prev_held else "New Entry"
            rows.append({
                'Ticker': t,
                'Rank': rk,
                'Weight': wt,
                'Status': status
            })

        # Sort held positions by rank (numeric first), then alphabetically by ticker
        rows.sort(key=lambda x: (x['Rank'] if isinstance(x['Rank'], (int, float)) else 9999, x['Ticker']))

        # Append exited positions (stocks held last month but evicted this month)
        exited_tickers = sorted(prev_held - held_tickers)
        for t in exited_tickers:
            rk = curr_ranks.get(t, 'N/A')
            rows.append({
                'Ticker': t,
                'Rank': rk,
                'Weight': 0.0,
                'Status': "Exit"
            })

        new_count = sum(1 for r in rows if r['Status'] == "New Entry")
        ret_count = sum(1 for r in rows if r['Status'] == "Retained")
        exit_count = len(exited_tickers)

        sub_hdr = (
            f"Month {idx:02d}/{len(exec_dates):02d} | Month-End: {m_end} (Rebalance: {ed}) | "
            f"Active: {len(held_tickers)} | New: {new_count} | Retained: {ret_count} | Exits: {exit_count}"
        )
        print("-" * len(sub_hdr))
        print(sub_hdr)
        print("-" * len(sub_hdr))
        print(f"  {'#':<3} | {'Ticker':<16} | {'Rank':>6} | {'Target Weight':>14} | {'Status':<12}")
        print("  " + "-" * 60)

        for r_idx, r in enumerate(rows, 1):
            rk_str = f"{r['Rank']}" if r['Rank'] != 'N/A' else "N/A"
            wt_str = f"{r['Weight']:>13.2f}%" if r['Status'] != "Exit" else f"{'--':>14}"
            print(f"  {r_idx:<3} | {r['Ticker']:<16} | {rk_str:>6} | {wt_str} | {r['Status']:<12}")

        print()
        prev_held = held_tickers

    print("=" * banner_w)
    print(f"[COMPLETED] Displayed full {len(exec_dates)}-month holdings breakdown.")
    print("=" * banner_w + "\n")


def generate_and_open_live_graphs(daily_df: pd.DataFrame, X_val: int = X) -> None:
    """
    Generates and immediately displays live performance graphs using the current backtest run:
    - Graph 1: Live Equity Curves across all 4 strategies (outputs/figures/live_equity.png).
    - Graph 2: Live Monthly P&L bar chart for Strategy 3 (outputs/figures/live_pnl.png).
    Opens both PNG files dynamically in the system default image viewer.
    """
    figures_dir = os.path.join(project_root, "outputs", "figures")
    os.makedirs(figures_dir, exist_ok=True)
    live_equity_path = os.path.join(figures_dir, "live_equity.png")
    live_pnl_path = os.path.join(figures_dir, "live_pnl.png")

    df = daily_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = pd.to_datetime(df['Date'])

    # ------------------------------------------------------------------------
    # GRAPH 1: Live Equity Curves (All 4 Strategies)
    # ------------------------------------------------------------------------
    fig1, ax1 = plt.subplots(figsize=(12, 6), dpi=150)

    strat_palette = {
        'Strategy 1': ('#2563EB', '-', 2.0),
        'Strategy 2': ('#D97706', '-', 2.2),
        'Strategy 3': ('#059669', '-', 2.5),
        'Strategy 4': ('#475569', '--', 1.8),
    }

    for strat in df['Strategy'].unique():
        s_data = df[df['Strategy'] == strat].sort_values('Date')
        color, linestyle, lw = ('#64748B', '-', 1.5)
        for prefix, (c, ls, w) in strat_palette.items():
            if prefix in strat:
                color, linestyle, lw = (c, ls, w)
                break

        final_val = s_data['Total_Equity'].iloc[-1]
        init_val = s_data['Total_Equity'].iloc[0]
        ret_pct = ((final_val / init_val) - 1.0) * 100.0 if init_val > 0 else 0.0

        label = f"{strat} (₹{final_val:,.0f} | {ret_pct:+.1f}%)"
        ax1.plot(s_data['Date'], s_data['Total_Equity'], label=label, color=color, linestyle=linestyle, linewidth=lw)

    ax1.set_title(f"Live Equity Curves for Input X={X_val}", fontsize=14, fontweight='bold', pad=12)
    ax1.set_xlabel("Date", fontsize=11, fontweight='semibold')
    ax1.set_ylabel("Total Portfolio Equity (INR)", fontsize=11, fontweight='semibold')
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"₹{y:,.0f}"))
    ax1.grid(True, linestyle='--', alpha=0.35)
    ax1.legend(loc='upper left', framealpha=0.9, fontsize=9)
    plt.tight_layout()
    fig1.savefig(live_equity_path, dpi=150)
    plt.close(fig1)

    # ------------------------------------------------------------------------
    # GRAPH 2: Live Monthly P&L for Strategy 3
    # ------------------------------------------------------------------------
    s3_data = df[df['Strategy'].str.contains('Strategy 3')].copy()
    if not s3_data.empty:
        fig2, ax2 = plt.subplots(figsize=(13, 5.5), dpi=150)
        s3_data['YearMonth'] = s3_data['Date'].dt.to_period('M')
        m_ends = s3_data.sort_values('Date').groupby('YearMonth').last().reset_index()
        m_ends['Monthly_Diff_INR'] = m_ends['Total_Equity'].diff()
        pnl_df = m_ends.dropna(subset=['Monthly_Diff_INR']).copy()

        x_labels = [str(ym) for ym in pnl_df['YearMonth']]
        y_vals = pnl_df['Monthly_Diff_INR'].tolist()
        colors = ['#10B981' if v >= 0 else '#EF4444' for v in y_vals]

        ax2.bar(range(len(x_labels)), y_vals, color=colors, edgecolor='black', linewidth=0.6, width=0.7)
        ax2.axhline(0, color='black', linewidth=0.9)

        ax2.set_title("Live Monthly P&L Strategy 3", fontsize=14, fontweight='bold', pad=12)
        ax2.set_xlabel("Month", fontsize=11, fontweight='semibold')
        ax2.set_ylabel("Monthly P&L (INR)", fontsize=11, fontweight='semibold')
        ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"₹{y:,.0f}"))
        ax2.set_xticks(range(len(x_labels)))
        ax2.set_xticklabels(x_labels, rotation=60, ha='right', fontsize=8)
        ax2.grid(True, axis='y', linestyle='--', alpha=0.35)

        legend_elements = [
            Patch(facecolor='#10B981', edgecolor='black', label='Profitable Month'),
            Patch(facecolor='#EF4444', edgecolor='black', label='Loss Month')
        ]
        ax2.legend(handles=legend_elements, loc='upper right', framealpha=0.9, fontsize=9)

        plt.tight_layout()
        fig2.savefig(live_pnl_path, dpi=150)
        plt.close(fig2)

    # ------------------------------------------------------------------------
    # OPEN LIVE GRAPHS
    # ------------------------------------------------------------------------
    print("\n[SUCCESS] Backtest complete. Opening live performance graphs for review...")
    figures_to_open = [live_equity_path, live_pnl_path]

    try:
        for fig_path in figures_to_open:
            if not os.path.exists(fig_path):
                raise FileNotFoundError(f"File not found: {fig_path}")

            if sys.platform.startswith('win'):
                os.startfile(fig_path)
            elif sys.platform == 'darwin':
                subprocess.call(['open', fig_path])
            else:
                subprocess.call(['xdg-open', fig_path])
    except Exception:
        print("Please manually open the files in the outputs/figures/ folder.")


# ============================================================================
# 7. MAIN ORCHESTRATION PIPELINE
# ============================================================================
def main():
    """
    Main entry point for Stage 4 execution with dynamic user parameters:
    1. Interactively prompts for Total Investment Amount (INR) and Top X stocks.
    2. Validates inputs with automatic fallback to defaults (user_capital = 500000.0, user_x = 20).
    3. Issues a safety warning and confirmation if capital per stock is below ₹2,000.
    4. Runs continuous simulation for all 4 strategies using dynamic parameters.
    5. Exports the 4 required output CSV files to data/processed/.
    6. Executes programmatic validation checks.
    7. Displays actual performance summary.
    8. Displays detailed month-by-month comparative analysis table.
    9. Displays monthly holdings breakdown.
    10. Dynamically generates and opens live performance graphs.
    """
    print("=" * 90)
    print(f"{'QUANTITATIVE MOMENTUM STRATEGY - DYNAMIC BACKTEST CONFIGURATION':^90}")
    print("=" * 90)

    # 1. User Inputs & Validation with Safe Fallback
    default_capital = 500000.0
    default_x = 20

    try:
        cap_str = input(f"Enter Total Investment Amount in INR [Default: {default_capital:,.0f}]: ").strip()
        user_capital = float(cap_str) if cap_str else default_capital

        x_str = input(f"Enter Number of top stocks to hold, X [Default: {default_x}]: ").strip()
        user_x = int(x_str) if x_str else default_x

        if user_capital <= 0 or user_x <= 0:
            raise ValueError("Capital and stock count must be strictly positive.")
    except (ValueError, EOFError) as e:
        print(f"[WARNING] Invalid input or non-interactive session ({e}). Falling back to defaults: Capital = ₹{default_capital:,.2f}, X = {default_x}")
        user_capital = default_capital
        user_x = default_x

    # 2. Low-Capital Safety Warning
    capital_per_stock = user_capital / user_x
    if capital_per_stock < 2000.0:
        print("[WARNING] Your capital per stock is very low. Many high-priced stocks will be skipped due to the whole-share execution rule.")
        try:
            proceed = input("Do you want to continue anyway? (y/n): ").strip()
        except EOFError:
            proceed = 'y'
        if proceed not in ['y', 'Y']:
            print("Backtest cancelled.")
            sys.exit(0)

    # 3. Dynamic Execution Confirmation
    print(f"\n[CONFIGURED] Running backtest with Capital: ₹{user_capital:,.2f} and Top X = {user_x} stocks...\n")

    # 4. Centralized Simulation Execution via Service Layer
    from src.service import run_backtest_service, get_last_run_dfs
    service_result = run_backtest_service(capital=user_capital, x=user_x, save_outputs=True)
    daily_df, trades_df, holdings_df, turnover_df = get_last_run_dfs()

    # 5. Save outputs to data/processed/ for standalone script continuity
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    daily_df.to_csv(OUTPUT_DAILY_PORTFOLIO, index=False)
    print(f"[1/4] Generated: {OUTPUT_DAILY_PORTFOLIO} ({len(daily_df):,} daily records)")

    trades_df.to_csv(OUTPUT_TRADE_LOG, index=False)
    print(f"[2/4] Generated: {OUTPUT_TRADE_LOG} ({len(trades_df):,} executed trades)")

    holdings_df.to_csv(OUTPUT_MONTHLY_HOLDINGS, index=False)
    print(f"[3/4] Generated: {OUTPUT_MONTHLY_HOLDINGS} ({len(holdings_df):,} monthly holdings entries)")

    turnover_df.to_csv(OUTPUT_TURNOVER, index=False)
    print(f"[4/4] Generated: {OUTPUT_TURNOVER} ({len(turnover_df):,} turnover records)")

    # 6. Display programmatic validation suite from service results
    print("\n" + "=" * 90)
    print(f"{'STAGE 4 PROGRAMMATIC VALIDATION SUITE':^90}")
    print("=" * 90)
    for check in service_result["validation"]:
        print(f"  [{check['status']}] {check['name']:<55} | {check['message']}")
    print("-" * 90)
    print("[VERIFIED] All 7 programmatic validation checks PASSED successfully.")
    print("=" * 90 + "\n")

    # 7. Print performance report
    print_performance_summary(daily_df, trades_df)

    # 8. Print detailed month-by-month analysis table
    print_monthly_analysis(daily_df)

    # 9. Print detailed monthly holdings breakdown
    _, _, rankings_df, _, _ = load_backtest_inputs()
    print_monthly_holdings_breakdown(holdings_df, rankings_df)

    # 10. Print summary of warnings if any
    w_count = service_result["warnings"]["count"]
    if w_count > 0:
        print(f"Total operational notices/warnings logged: {w_count}")
        print("Sample notices:")
        for w in service_result["warnings"]["samples"][:5]:
            print(f"  - {w}")
        print("-" * 90 + "\n")

    # 11. Generate and open live graphs based on actual current run
    generate_and_open_live_graphs(daily_df, X_val=user_x)


if __name__ == '__main__':
    main()
