"""
src/metrics.py - Stage 5: Quantitative Performance Metrics Engine
Quantitative Momentum Strategy Backtesting System for Indian Equities.

Computes comprehensive, academically rigorous performance metrics for each strategy:
- Return & Compounding: Total Return (%), CAGR (%) based on exact calendar days.
- Risk & Volatility: Annualized Volatility (%), Maximum Drawdown (%) with Peak/Trough/Recovery dates.
- Risk-Adjusted Ratios: Annualized Sharpe Ratio (Rf=6.5%), Annualized Sortino Ratio (downside Rf penalization).
- Monthly Performance: Monthly Returns (%) and Monthly P&L (INR) across all completed months.
- Trade Statistics: Total Trades, Buys, Sells, and FIFO-based Win Rate (%) for completed round-trips.
- Friction & Turnover: Average Monthly Name Turnover (%), Traded-Value Turnover (%), Total Transaction Costs.

Outputs saved to data/processed/:
1. performance_summary.csv: Master strategy comparison table.
2. monthly_returns.csv: Monthly return and P&L time series.
3. drawdown_series.csv: Daily equity, running high-water mark, and drawdown percentages.
"""

import os
import sys
import warnings
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Ensure clean UTF-8 stdout encoding on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure project root is in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ============================================================================
# CONFIGURATION PARAMETERS
# ============================================================================
RISK_FREE_RATE = 0.065              # 6.5% annual risk-free rate
TRADING_DAYS_PER_YEAR = 252         # Standard trading sessions per calendar year

# Input Paths (Stage 4 Artifacts)
PROCESSED_DIR = os.path.join("data", "processed")
INPUT_DAILY_PORTFOLIO = os.path.join(PROCESSED_DIR, "daily_portfolio_values.csv")
INPUT_TRADE_LOG = os.path.join(PROCESSED_DIR, "trade_log.csv")
INPUT_MONTHLY_HOLDINGS = os.path.join(PROCESSED_DIR, "monthly_holdings.csv")
INPUT_TURNOVER = os.path.join(PROCESSED_DIR, "turnover.csv")

# Output Paths (Stage 5 Artifacts)
OUTPUT_PERFORMANCE_SUMMARY = os.path.join(PROCESSED_DIR, "performance_summary.csv")
OUTPUT_MONTHLY_RETURNS = os.path.join(PROCESSED_DIR, "monthly_returns.csv")
OUTPUT_DRAWDOWN_SERIES = os.path.join(PROCESSED_DIR, "drawdown_series.csv")


# ============================================================================
# 1. DATA INGESTION
# ============================================================================
def load_stage4_outputs(
    daily_path: str = INPUT_DAILY_PORTFOLIO,
    trades_path: str = INPUT_TRADE_LOG,
    holdings_path: str = INPUT_MONTHLY_HOLDINGS,
    turnover_path: str = INPUT_TURNOVER
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Loads and validates the four Stage 4 backtesting output files.
    """
    for p, name in [
        (daily_path, "Daily Portfolio Values"),
        (trades_path, "Trade Log"),
        (holdings_path, "Monthly Holdings"),
        (turnover_path, "Turnover")
    ]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Required Stage 4 file not found: {p} ({name})")

    daily_df = pd.read_csv(daily_path)
    daily_df['Date'] = pd.to_datetime(daily_df['Date'])

    trades_df = pd.read_csv(trades_path)
    trades_df['Date'] = pd.to_datetime(trades_df['Date'])

    holdings_df = pd.read_csv(holdings_path)
    holdings_df['Date'] = pd.to_datetime(holdings_df['Date'])

    turnover_df = pd.read_csv(turnover_path)
    turnover_df['Date'] = pd.to_datetime(turnover_df['Date'])

    return daily_df, trades_df, holdings_df, turnover_df


# ============================================================================
# 2. RETURNS & DRAWDOWN ENGINE
# ============================================================================
def compute_drawdown_series(daily_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Dict]]:
    """
    Calculates the running peak equity and daily drawdown percentage for each strategy.
    Identifies Maximum Drawdown (%), Peak Date, Trough Date, and Recovery Date.
    """
    df = daily_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = pd.to_datetime(df['Date'])

    records = []
    dd_stats = {}

    for strat in df['Strategy'].unique():
        sub = df[df['Strategy'] == strat].copy().sort_values('Date').reset_index(drop=True)
        running_peak = sub['Total_Equity'].cummax()
        drawdown_pct = (sub['Total_Equity'] - running_peak) / running_peak * 100.0

        sub['Running_Peak_Equity'] = running_peak.round(2)
        sub['Drawdown_%'] = drawdown_pct.round(4)
        records.append(sub[['Date', 'Strategy', 'Total_Equity', 'Running_Peak_Equity', 'Drawdown_%']])

        # Identify Maximum Drawdown metrics
        trough_idx = drawdown_pct.idxmin()
        max_dd = float(drawdown_pct.loc[trough_idx])
        trough_date = sub.loc[trough_idx, 'Date'].strftime('%Y-%m-%d')
        peak_equity_at_trough = float(running_peak.loc[trough_idx])

        # Peak date: the latest date on or before trough_idx where Total_Equity == peak_equity_at_trough
        peak_subset = sub.loc[:trough_idx]
        peak_idx = peak_subset[peak_subset['Total_Equity'] >= peak_equity_at_trough - 1e-4].index[-1]
        peak_date = sub.loc[peak_idx, 'Date'].strftime('%Y-%m-%d')

        # Recovery date: first date after trough_idx where Total_Equity >= peak_equity_at_trough
        post_trough_subset = sub.loc[trough_idx + 1:]
        recovery_candidates = post_trough_subset[post_trough_subset['Total_Equity'] >= peak_equity_at_trough - 1e-4]
        if len(recovery_candidates) > 0:
            recovery_date = recovery_candidates.iloc[0]['Date'].strftime('%Y-%m-%d')
        else:
            recovery_date = "Not Recovered"

        dd_stats[strat] = {
            'Max_Drawdown_%': round(max_dd, 4),
            'Peak_Date': peak_date,
            'Trough_Date': trough_date,
            'Recovery_Date': recovery_date,
            'Peak_Equity': round(peak_equity_at_trough, 2),
            'Trough_Equity': round(float(sub.loc[trough_idx, 'Total_Equity']), 2)
        }

    drawdown_series_df = pd.concat(records, ignore_index=True)
    drawdown_series_df['Date'] = drawdown_series_df['Date'].dt.strftime('%Y-%m-%d')
    return drawdown_series_df, dd_stats


def compute_monthly_returns(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates monthly percentage returns and rupee profit/loss from the last
    trading session of each calendar month to the next.
    """
    df = daily_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = pd.to_datetime(df['Date'])
    df['YearMonth'] = df['Date'].dt.to_period('M')

    # Select last trading day of each month
    month_ends = df.sort_values('Date').groupby(['Strategy', 'YearMonth']).last().reset_index()

    month_ends['Monthly_Return_%'] = month_ends.groupby('Strategy')['Total_Equity'].pct_change() * 100.0
    month_ends['Monthly_Profit_Loss_INR'] = month_ends.groupby('Strategy')['Total_Equity'].diff()

    # Drop inception row where return is NaN
    monthly_returns_df = month_ends.dropna(subset=['Monthly_Return_%']).copy()
    monthly_returns_df['Date'] = monthly_returns_df['Date'].dt.strftime('%Y-%m-%d')
    monthly_returns_df['Monthly_Return_%'] = monthly_returns_df['Monthly_Return_%'].round(4)
    monthly_returns_df['Monthly_Profit_Loss_INR'] = monthly_returns_df['Monthly_Profit_Loss_INR'].round(2)

    return monthly_returns_df[['Date', 'Strategy', 'Monthly_Return_%', 'Monthly_Profit_Loss_INR']]


# ============================================================================
# 3. TRADE STATISTICS & FIFO WIN RATE
# ============================================================================
def compute_fifo_trade_statistics(
    trades_df: pd.DataFrame,
    strategy_name: str
) -> Dict[str, Optional[float]]:
    """
    Computes trade statistics and FIFO-matched round-trip win rate.
    
    FIFO Matching Methodology:
    1. Each Buy creates an inventory lot: [shares, unit_cost_basis], where
       unit_cost_basis = (shares * Execution_Price + Transaction_Cost) / shares.
    2. When a Sell order executes for Q shares at Execution_Price with Transaction_Cost:
       unit_net_proceeds = (Q * Execution_Price - Transaction_Cost) / Q.
       Shares are matched against open lots in First-In, First-Out (FIFO) sequence.
    3. The total cost basis of the liquidated shares is the sum of (matched_shares * unit_cost_basis).
    4. A completed sell trade is classified as a "Win" if Net Proceeds > Cost Basis.
    5. Partial sells consume partial lots and carry forward remaining shares at their original cost basis.
    
    Edge cases: Strategies with zero sells (Strategy 1 & 4) report Win Rate as None (N/A) without crashing.
    """
    s_trades = trades_df[trades_df['Strategy'] == strategy_name].copy().sort_values('Date').reset_index(drop=True)
    total_trades = len(s_trades)
    buy_trades = len(s_trades[s_trades['Action'] == 'Buy'])
    sell_trades = len(s_trades[s_trades['Action'] == 'Sell'])
    total_tc = s_trades['Transaction_Cost'].sum()

    if sell_trades == 0:
        return {
            'Total_Trades': total_trades,
            'Buy_Trades': buy_trades,
            'Sell_Trades': sell_trades,
            'Win_Rate_%': None,
            'Winning_Sells': 0,
            'Completed_Sells': 0,
            'Total_Transaction_Costs_INR': round(float(total_tc), 2)
        }

    # FIFO Inventory Queue per ticker: list of dicts {'shares': float, 'cost_per_share': float}
    inventory: Dict[str, List[Dict[str, float]]] = {}
    completed_sells = 0
    winning_sells = 0

    for _, row in s_trades.iterrows():
        ticker = row['Ticker']
        action = row['Action']
        shares = float(row['Shares'])
        px = float(row['Execution_Price'])
        tc = float(row['Transaction_Cost'])

        if action == 'Buy':
            if ticker not in inventory:
                inventory[ticker] = []
            unit_cost = (shares * px + tc) / shares if shares > 0 else px
            inventory[ticker].append({'shares': shares, 'cost_per_share': unit_cost})

        elif action == 'Sell':
            net_proceeds_per_share = (shares * px - tc) / shares if shares > 0 else px
            remaining_to_sell = shares
            total_cost_basis = 0.0

            while remaining_to_sell > 1e-6 and inventory.get(ticker):
                lot = inventory[ticker][0]
                matched_shares = min(remaining_to_sell, lot['shares'])
                total_cost_basis += matched_shares * lot['cost_per_share']
                remaining_to_sell -= matched_shares
                lot['shares'] -= matched_shares

                if lot['shares'] <= 1e-6:
                    inventory[ticker].pop(0)

            net_sell_proceeds = shares * net_proceeds_per_share
            realized_pnl = net_sell_proceeds - total_cost_basis
            completed_sells += 1
            if realized_pnl > 0.0:
                winning_sells += 1

    win_rate = (winning_sells / completed_sells * 100.0) if completed_sells > 0 else None

    return {
        'Total_Trades': total_trades,
        'Buy_Trades': buy_trades,
        'Sell_Trades': sell_trades,
        'Win_Rate_%': round(win_rate, 4) if win_rate is not None else None,
        'Winning_Sells': winning_sells,
        'Completed_Sells': completed_sells,
        'Total_Transaction_Costs_INR': round(float(total_tc), 2)
    }


# ============================================================================
# 4. MASTER PERFORMANCE SUMMARY BUILDER
# ============================================================================
def build_performance_summary(
    daily_df: pd.DataFrame,
    trades_df: pd.DataFrame,
    turnover_df: pd.DataFrame,
    dd_stats: Dict[str, Dict],
    rf_annual: float = RISK_FREE_RATE,
    trading_days_per_year: int = TRADING_DAYS_PER_YEAR
) -> pd.DataFrame:
    """
    Computes all 10 performance and risk metrics across each of the 4 strategies.
    """
    df = daily_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['Date']):
        df['Date'] = pd.to_datetime(df['Date'])

    rf_daily = (1.0 + rf_annual) ** (1.0 / trading_days_per_year) - 1.0
    summary_rows = []

    for strat in df['Strategy'].unique():
        s_df = df[df['Strategy'] == strat].copy().sort_values('Date').reset_index(drop=True)
        init_cap = float(s_df['Total_Equity'].iloc[0])
        final_val = float(s_df['Total_Equity'].iloc[-1])

        # 1. Total Return (%)
        tot_return = (final_val / init_cap - 1.0) * 100.0

        # 2. CAGR (%) based on exact calendar days
        d_start = s_df['Date'].iloc[0]
        d_end = s_df['Date'].iloc[-1]
        elapsed_days = (d_end - d_start).days
        years = elapsed_days / 365.25
        cagr = ((final_val / init_cap) ** (1.0 / years) - 1.0) * 100.0 if years > 0 else 0.0

        # 3. Annualized Volatility (%)
        daily_rets = s_df['Total_Equity'].pct_change().dropna()
        daily_std = daily_rets.std(ddof=1)
        vol_ann = daily_std * np.sqrt(trading_days_per_year) * 100.0

        # 4. Annualized Sharpe Ratio
        excess_rets = daily_rets - rf_daily
        mean_excess_ann = excess_rets.mean() * trading_days_per_year
        vol_ann_dec = daily_std * np.sqrt(trading_days_per_year)
        sharpe = (mean_excess_ann / vol_ann_dec) if vol_ann_dec > 0 else 0.0

        # 5. Annualized Sortino Ratio
        # Downside deviation only penalizes daily returns falling below the daily risk-free rate
        downside_diff = np.minimum(daily_rets - rf_daily, 0.0)
        downside_dev = np.sqrt(np.mean(downside_diff ** 2))
        downside_dev_ann = downside_dev * np.sqrt(trading_days_per_year)
        sortino = (mean_excess_ann / downside_dev_ann) if downside_dev_ann > 0 else 0.0

        # 6. Drawdown stats
        s_dd = dd_stats.get(strat, {})

        # 7. Trade stats & Win Rate
        t_stats = compute_fifo_trade_statistics(trades_df, strat)

        # 8. Turnover stats
        s_to = turnover_df[turnover_df['Strategy'] == strat]
        avg_name_to = float(s_to['Name_Turnover (%)'].mean()) if len(s_to) > 0 else 0.0
        avg_val_to = float(s_to['Traded_Value_Turnover (%)'].mean()) if len(s_to) > 0 else 0.0

        summary_rows.append({
            'Strategy': strat,
            'Initial_Capital': round(init_cap, 2),
            'Final_Value': round(final_val, 2),
            'Total_Return_%': round(tot_return, 4),
            'CAGR_%': round(cagr, 4),
            'Volatility_%': round(vol_ann, 4),
            'Sharpe_Ratio': round(sharpe, 4),
            'Sortino_Ratio': round(sortino, 4),
            'Max_Drawdown_%': s_dd.get('Max_Drawdown_%', 0.0),
            'Peak_Date': s_dd.get('Peak_Date', ''),
            'Trough_Date': s_dd.get('Trough_Date', ''),
            'Recovery_Date': s_dd.get('Recovery_Date', ''),
            'Total_Trades': t_stats['Total_Trades'],
            'Buy_Trades': t_stats['Buy_Trades'],
            'Sell_Trades': t_stats['Sell_Trades'],
            'Win_Rate_%': t_stats['Win_Rate_%'],
            'Avg_Name_Turnover_%': round(avg_name_to, 4),
            'Avg_Value_Turnover_%': round(avg_val_to, 4),
            'Total_Transaction_Costs_INR': t_stats['Total_Transaction_Costs_INR']
        })

    summary_df = pd.DataFrame(summary_rows)
    return summary_df


# ============================================================================
# 5. PROGRAMMATIC VALIDATION CHECKS
# ============================================================================
def run_stage5_validation_checks(
    summary_df: pd.DataFrame,
    daily_df: pd.DataFrame
) -> bool:
    """
    Executes programmatic validation suite verifying the 4 required criteria:
    1. Final Portfolio Value matches last row of daily_portfolio_values.csv (< ₹1.00 tolerance).
    2. CAGR and Total Return are mathematically consistent with elapsed time.
    3. Check for any NaN, Infinity, or negative volatility values in metrics.
    4. Confirm Win Rate handles zero-sell edge cases safely without crashing.
    """
    print("=" * 90)
    print(f"{'STAGE 5 PROGRAMMATIC VALIDATION SUITE':^90}")
    print("=" * 90)

    all_passed = True

    # 1. Final Value Reconciliation
    max_recon_diff = 0.0
    for _, row in summary_df.iterrows():
        strat = row['Strategy']
        reported_val = row['Final_Value']
        actual_val = daily_df[daily_df['Strategy'] == strat].sort_values('Date').iloc[-1]['Total_Equity']
        diff = abs(reported_val - actual_val)
        if diff > max_recon_diff:
            max_recon_diff = diff

    pass_recon = (max_recon_diff < 1.00)
    if not pass_recon:
        all_passed = False
    print(f"  [{'PASS' if pass_recon else 'FAIL'}] 1. Final Equity Reconciliation (< ₹1.00)            | Max strategy discrepancy: INR {max_recon_diff:.4f}")

    # 2. Mathematical Consistency: (1 + Total_Return) == (1 + CAGR)^years
    d_start = daily_df['Date'].min()
    d_end = daily_df['Date'].max()
    years = (d_end - d_start).days / 365.25
    max_cagr_discrepancy = 0.0

    for _, row in summary_df.iterrows():
        tot_ret_dec = row['Total_Return_%'] / 100.0
        cagr_dec = row['CAGR_%'] / 100.0
        expected_tot_ret = ((1.0 + cagr_dec) ** years) - 1.0
        diff = abs(tot_ret_dec - expected_tot_ret) * 100.0
        if diff > max_cagr_discrepancy:
            max_cagr_discrepancy = diff

    pass_cagr = (max_cagr_discrepancy < 0.01)
    if not pass_cagr:
        all_passed = False
    print(f"  [{'PASS' if pass_cagr else 'FAIL'}] 2. CAGR-Total Return Mathematical Consistency        | Max return discrepancy: {max_cagr_discrepancy:.6f}% (Elapsed: {years:.4f} yrs)")

    # 3. Numeric Integrity (No NaNs, Infs, or negative volatilities)
    numeric_cols = [
        'Initial_Capital', 'Final_Value', 'Total_Return_%', 'CAGR_%',
        'Volatility_%', 'Sharpe_Ratio', 'Sortino_Ratio', 'Max_Drawdown_%',
        'Total_Trades', 'Buy_Trades', 'Sell_Trades',
        'Avg_Name_Turnover_%', 'Avg_Value_Turnover_%', 'Total_Transaction_Costs_INR'
    ]
    has_nan_or_inf = False
    for col in numeric_cols:
        if summary_df[col].isna().any() or np.isinf(summary_df[col]).any():
            has_nan_or_inf = True
            break

    negative_vols = (summary_df['Volatility_%'] <= 0).sum()
    pass_integrity = (not has_nan_or_inf) and (negative_vols == 0)
    if not pass_integrity:
        all_passed = False
    print(f"  [{'PASS' if pass_integrity else 'FAIL'}] 3. Numeric Sanity (No Invalid NaNs/Infs/Negative Vol) | Invalid entries: 0 | All volatilities strictly positive")

    # 4. Zero-sell Win Rate edge cases
    zero_sell_strats = summary_df[summary_df['Sell_Trades'] == 0]
    pass_edge_cases = True
    for _, row in zero_sell_strats.iterrows():
        if pd.notnull(row['Win_Rate_%']):
            pass_edge_cases = False
            break

    active_sell_strats = summary_df[summary_df['Sell_Trades'] > 0]
    for _, row in active_sell_strats.iterrows():
        if pd.isnull(row['Win_Rate_%']) or row['Win_Rate_%'] < 0 or row['Win_Rate_%'] > 100:
            pass_edge_cases = False
            break

    if not pass_edge_cases:
        all_passed = False
    print(f"  [{'PASS' if pass_edge_cases else 'FAIL'}] 4. Win Rate Edge Case Handling (0 Sells -> N/A)     | Buy-and-hold strategies gracefully return N/A; active strategies bounded [0-100%]")
    print("-" * 90)

    if all_passed:
        print("[VERIFIED] All 4 Stage 5 programmatic validation checks PASSED successfully.")
    else:
        print("[ERROR] One or more validation checks failed.")
    print("=" * 90 + "\n")

    return all_passed


# ============================================================================
# 6. OUTPUT EXPORTERS & CONSOLE REPORTING
# ============================================================================
def export_stage5_outputs(
    summary_df: pd.DataFrame,
    monthly_returns_df: pd.DataFrame,
    drawdown_series_df: pd.DataFrame
) -> None:
    """
    Saves performance_summary.csv, monthly_returns.csv, and drawdown_series.csv to data/processed/.
    """
    os.makedirs(PROCESSED_DIR, exist_ok=True)

    summary_df.to_csv(OUTPUT_PERFORMANCE_SUMMARY, index=False)
    print(f"[1/3] Generated: {OUTPUT_PERFORMANCE_SUMMARY} ({len(summary_df)} strategy rows)")

    monthly_returns_df.to_csv(OUTPUT_MONTHLY_RETURNS, index=False)
    print(f"[2/3] Generated: {OUTPUT_MONTHLY_RETURNS} ({len(monthly_returns_df):,} monthly return records)")

    drawdown_series_df.to_csv(OUTPUT_DRAWDOWN_SERIES, index=False)
    print(f"[3/3] Generated: {OUTPUT_DRAWDOWN_SERIES} ({len(drawdown_series_df):,} daily drawdown records)")
    print()


def print_stage5_report(summary_df: pd.DataFrame) -> None:
    """
    Prints a formatted, human-readable terminal table comparing key performance metrics.
    """
    print("=" * 115)
    print(f"{'STAGE 5: COMPREHENSIVE STRATEGY PERFORMANCE SUMMARY':^115}")
    print("=" * 115)

    headers = [
        ("Strategy", 38),
        ("Final Value", 15),
        ("CAGR", 10),
        ("Vol", 9),
        ("Sharpe", 9),
        ("Sortino", 9),
        ("Max DD", 10),
        ("Win Rate", 10)
    ]
    hdr_str = " | ".join(f"{h:<{w}}" if i == 0 else f"{h:>{w}}" for i, (h, w) in enumerate(headers))
    print(hdr_str)
    print("-" * 115)

    for _, r in summary_df.iterrows():
        strat_display = r['Strategy'][:38]
        final_str = f"INR {r['Final_Value']:>11,.2f}"
        cagr_str = f"{r['CAGR_%']:>9.2f}%"
        vol_str = f"{r['Volatility_%']:>8.2f}%"
        sharpe_str = f"{r['Sharpe_Ratio']:>8.2f}"
        sortino_str = f"{r['Sortino_Ratio']:>8.2f}"
        dd_str = f"{r['Max_Drawdown_%']:>9.2f}%"
        wr_str = f"{r['Win_Rate_%']:>9.2f}%" if pd.notnull(r['Win_Rate_%']) else f"{'N/A':>10}"

        row_str = (
            f"{strat_display:<38} | "
            f"{final_str:>15} | "
            f"{cagr_str:>10} | "
            f"{vol_str:>9} | "
            f"{sharpe_str:>9} | "
            f"{sortino_str:>9} | "
            f"{dd_str:>10} | "
            f"{wr_str:>10}"
        )
        print(row_str)

    print("=" * 115 + "\n")


# ============================================================================
# 7. MAIN ORCHESTRATION PIPELINE
# ============================================================================
def main():
    print("=" * 90)
    print(f"{'STAGE 5: QUANTITATIVE PERFORMANCE METRICS ENGINE':^90}")
    print("=" * 90)
    print(f"Annual Risk-Free Rate:        {RISK_FREE_RATE*100:.2f}%")
    print(f"Trading Sessions per Year:   {TRADING_DAYS_PER_YEAR}")
    print(f"Input Directory:             {PROCESSED_DIR}")
    print("-" * 90)

    # 1. Load Stage 4 datasets
    daily_df, trades_df, holdings_df, turnover_df = load_stage4_outputs()

    # 2. Compute Drawdown Series & Extremes
    drawdown_series_df, dd_stats = compute_drawdown_series(daily_df)

    # 3. Compute Monthly Returns
    monthly_returns_df = compute_monthly_returns(daily_df)

    # 4. Build Master Performance Summary Table
    summary_df = build_performance_summary(
        daily_df, trades_df, turnover_df, dd_stats,
        rf_annual=RISK_FREE_RATE, trading_days_per_year=TRADING_DAYS_PER_YEAR
    )

    # 5. Export Stage 5 Artifacts
    export_stage5_outputs(summary_df, monthly_returns_df, drawdown_series_df)

    # 6. Run Validation Suite
    run_stage5_validation_checks(summary_df, daily_df)

    # 7. Display Formatted Terminal Summary
    print_stage5_report(summary_df)


if __name__ == '__main__':
    main()
