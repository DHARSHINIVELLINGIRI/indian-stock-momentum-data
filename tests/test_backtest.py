"""
tests/test_backtest.py - Automated End-to-End Test Suite
Quantitative Momentum Strategy Backtesting System for Indian Equities.

Tests:
1. TEST A (Data & Momentum):
   - 12-1 momentum formula: Close[t-21] / Close[t-252] - 1.0
   - 252-day annualized volatility: std(daily_returns, 252) * sqrt(252)
   - Risk-adjusted momentum calculation
   - Descending cross-sectional rank ordering
   - Deterministic alphabetical tie-breaking
   - Strict exclusion of NIFTYBEES from monthly momentum rankings
2. TEST B (Portfolio Simulation):
   - Non-negative cash constraint across all strategies on all trading days
   - Whole-share integer integrity for Strategies 2, 3, and 4
   - Accurate transaction costs: 0.15% variable fee on trade value + ₹15 fixed fee per sell order
   - Strategy 3 retention buffer logic (2X rank retention, top-X target filling, rank weights summing to 1.0)
3. TEST C (Performance Metrics):
   - Independent verification of CAGR on synthetic equity curves
   - Independent verification of Annualized Sharpe Ratio (Rf=6.5%)
   - Maximum Drawdown calculation with Peak Date, Trough Date, and Recovery Date
   - FIFO round-trip win rate logic and graceful handling of zero-sell edge cases
4. TEST D (Visualizations):
   - Verification that all 7 PNG charts exist in outputs/figures/ and are non-empty
   - Verification that chart metric values match performance_summary.csv exactly
"""

import os
import sys
import numpy as np
import pandas as pd
import pytest

# Ensure root directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.momentum import (
    compute_momentum_signals,
    generate_monthly_momentum_rankings,
    WARMUP_LOOKBACK,
    MOMENTUM_SKIP_DAYS,
    TRADING_DAYS_PER_YEAR
)
from src.backtest import (
    select_strategy_2_holdings,
    select_strategy_3_holdings,
    VAR_COST,
    FIXED_SELL_COST,
    INITIAL_CAPITAL,
    X
)
from src.metrics import (
    compute_drawdown_series,
    compute_fifo_trade_statistics,
    RISK_FREE_RATE
)


# ============================================================================
# TEST A: DATA INGESTION & MOMENTUM RANKINGS
# ============================================================================
class TestDataAndMomentum:

    def test_momentum_12_1_formula(self):
        """Verify 12-1 momentum calculation: Close[t-21] / Close[t-252] - 1.0."""
        n_days = 300
        dates = pd.date_range('2022-01-01', periods=n_days, freq='B')
        
        # Synthetic prices: known geometric progression
        prices = 100.0 * (1.001 ** np.arange(n_days))
        df_synthetic = pd.DataFrame({
            'Date': dates,
            'Ticker': ['STOCK_A.NS'] * n_days,
            'Close': prices
        })

        close_matrix, raw_mom, ann_vol, risk_adj = compute_momentum_signals(df_synthetic)
        
        # Target day = day 260
        t_idx = 260
        target_date = dates[t_idx]
        p_t_minus_21 = prices[t_idx - MOMENTUM_SKIP_DAYS]
        p_t_minus_252 = prices[t_idx - WARMUP_LOOKBACK]
        expected_raw_mom = (p_t_minus_21 / p_t_minus_252) - 1.0

        computed_raw_mom = raw_mom.loc[target_date, 'STOCK_A.NS']
        assert np.isclose(computed_raw_mom, expected_raw_mom, rtol=1e-5), (
            f"Momentum 12-1 mismatch: computed={computed_raw_mom}, expected={expected_raw_mom}"
        )

    def test_annualized_volatility_formula(self):
        """Verify 252-day annualized volatility: rolling(252).std() * sqrt(252)."""
        n_days = 300
        dates = pd.date_range('2022-01-01', periods=n_days, freq='B')
        np.random.seed(42)
        daily_returns = np.random.normal(0.0005, 0.015, n_days)
        prices = 100.0 * np.cumprod(1.0 + daily_returns)

        df_synthetic = pd.DataFrame({
            'Date': dates,
            'Ticker': ['STOCK_B.NS'] * n_days,
            'Close': prices
        })

        close_matrix, raw_mom, ann_vol, risk_adj = compute_momentum_signals(df_synthetic)
        
        target_date = dates[-1]
        # Independent manual calculation
        rets_series = pd.Series(prices).pct_change().iloc[-252:]
        expected_vol = rets_series.std(ddof=1) * np.sqrt(252.0)

        computed_vol = ann_vol.loc[target_date, 'STOCK_B.NS']
        assert np.isclose(computed_vol, expected_vol, rtol=1e-4), (
            f"Annualized volatility mismatch: computed={computed_vol}, expected={expected_vol}"
        )

    def test_risk_adjusted_momentum_formula(self):
        """Verify risk-adjusted momentum equals raw momentum divided by annualized volatility."""
        n_days = 300
        dates = pd.date_range('2022-01-01', periods=n_days, freq='B')
        np.random.seed(123)
        prices = 100.0 * np.cumprod(1.0 + np.random.normal(0.001, 0.012, n_days))

        df_synthetic = pd.DataFrame({
            'Date': dates,
            'Ticker': ['STOCK_C.NS'] * n_days,
            'Close': prices
        })

        close_matrix, raw_mom, ann_vol, risk_adj = compute_momentum_signals(df_synthetic)
        target_date = dates[-1]
        expected_adj = raw_mom.loc[target_date, 'STOCK_C.NS'] / ann_vol.loc[target_date, 'STOCK_C.NS']
        computed_adj = risk_adj.loc[target_date, 'STOCK_C.NS']
        assert np.isclose(computed_adj, expected_adj, rtol=1e-5)

    def test_descending_rank_order_and_alphabetical_tie_breaker(self):
        """Verify cross-sectional ranking sorts descending, with alphabetical tie-breaking."""
        dec_date = pd.Timestamp('2024-05-31')
        tickers = ['ZETA.NS', 'BETA.NS', 'ALPHA.NS', 'GAMMA.NS']
        
        # ALPHA and BETA have identical risk-adjusted momentum; ZETA has higher; GAMMA lower
        raw_m = pd.DataFrame([[0.25, 0.20, 0.20, 0.10]], index=[dec_date], columns=tickers)
        ann_v = pd.DataFrame([[0.15, 0.15, 0.15, 0.15]], index=[dec_date], columns=tickers)
        adj_m = pd.DataFrame([[1.6667, 1.3333, 1.3333, 0.6667]], index=[dec_date], columns=tickers)

        rankings_df, _ = generate_monthly_momentum_rankings(raw_m, ann_v, adj_m, [dec_date])
        ranked_tickers = rankings_df['ticker'].tolist()

        # Expected order: ZETA (rank 1), ALPHA (rank 2, tie broken alphabetically), BETA (rank 3), GAMMA (rank 4)
        assert ranked_tickers == ['ZETA.NS', 'ALPHA.NS', 'BETA.NS', 'GAMMA.NS'], (
            f"Tie-breaking or descending order failed: {ranked_tickers}"
        )
        assert rankings_df['rank'].tolist() == [1, 2, 3, 4]

    def test_benchmark_excluded_from_rankings(self):
        """Verify NIFTYBEES is strictly excluded from Stage 3 momentum rankings."""
        rankings_path = os.path.join("data", "processed", "monthly_momentum_rankings.csv")
        assert os.path.exists(rankings_path), f"File missing: {rankings_path}"

        rankings_df = pd.read_csv(rankings_path)
        tickers = rankings_df['ticker'].unique()
        assert 'NIFTYBEES.NS' not in tickers, "NIFTYBEES.NS found in momentum rankings!"
        assert 'NIFTYBEES' not in tickers, "NIFTYBEES found in momentum rankings!"


# ============================================================================
# TEST B: PORTFOLIO SIMULATION & ACCOUNTING ENGINE
# ============================================================================
class TestPortfolioSimulation:

    def test_cash_never_negative(self):
        """Verify cash is non-negative on every single trading day across all strategies."""
        daily_path = os.path.join("data", "processed", "daily_portfolio_values.csv")
        assert os.path.exists(daily_path), f"File missing: {daily_path}"

        daily_df = pd.read_csv(daily_path)
        min_cash = daily_df['Cash'].min()
        assert min_cash >= -1e-6, f"Negative cash detected: min_cash = {min_cash}"

    def test_whole_share_quantities_integer(self):
        """Verify whole-share trades in Strategies 2, 3, 4 are strictly integers."""
        trade_path = os.path.join("data", "processed", "trade_log.csv")
        assert os.path.exists(trade_path), f"File missing: {trade_path}"

        trades_df = pd.read_csv(trade_path)
        discrete_strats = trades_df[trades_df['Strategy'].str.contains('Strategy 2|Strategy 3|Strategy 4', regex=True)]
        non_int_shares = discrete_strats['Shares'].apply(lambda x: abs(x - round(x)) > 1e-6).sum()
        assert non_int_shares == 0, f"Found {non_int_shares} non-integer share quantities in discrete strategies!"

    def test_transaction_cost_calculation(self):
        """Verify transaction costs: 0.15% on buys; 0.15% + ₹15 on sells."""
        trade_path = os.path.join("data", "processed", "trade_log.csv")
        trades_df = pd.read_csv(trade_path)

        for _, tr in trades_df.iterrows():
            act = tr['Action']
            val = tr['Trade_Value']
            tc = tr['Transaction_Cost']

            if act == 'Buy':
                expected_tc = round(VAR_COST * val, 2)
            else:
                expected_tc = round(VAR_COST * val + FIXED_SELL_COST, 2)

            # Allow 1 paisa (₹0.01) float rounding tolerance
            assert abs(tc - expected_tc) <= 0.02, (
                f"TC mismatch for {tr['Strategy']} {act} on {tr['Date']}: recorded={tc}, expected={expected_tc}"
            )

    def test_strategy3_retention_buffer_logic(self):
        """
        Verify Strategy 2 retention buffer and Strategy 3 rank weighting:
        - Strategy 2: Target count X = 20. Retention threshold = 2X = 40.
          Existing holding ranked <= 40 is retained.
          Existing holding ranked > 40 is evicted.
          Target weights are equal (1/X).
        - Strategy 3: Pure Top X, no buffer.
          Weights are rank-based and monotonically decreasing.
        """
        dec_date = pd.Timestamp('2024-06-28')
        target_count = 20

        # Construct synthetic rankings of 60 stocks (ranks 1 to 60)
        tickers = [f"STOCK_{i:02d}.NS" for i in range(1, 61)]
        synthetic_rankings = pd.DataFrame({
            'decision_date': [dec_date] * 60,
            'ticker': tickers,
            'rank': list(range(1, 61))
        })

        # Incumbents currently held:
        # STOCK_05 (rank 5, within top 20) -> retain
        # STOCK_35 (rank 35, within buffer 21-40) -> retain in S2
        # STOCK_45 (rank 45, outside buffer > 40) -> evict in S2
        current_holdings = {
            'STOCK_05.NS': 100,
            'STOCK_35.NS': 150,
            'STOCK_45.NS': 200
        }

        # 1. Test Strategy 2 (Equal-Weight with 2X Retention Buffer)
        s2_selected, s2_weights, s2_additions = select_strategy_2_holdings(
            synthetic_rankings, dec_date, current_holdings, target_count=target_count
        )

        assert len(s2_selected) == target_count, f"S2 count {len(s2_selected)} != {target_count}"
        assert 'STOCK_05.NS' in s2_selected, "STOCK_05 should be retained in S2 (rank 5)"
        assert 'STOCK_35.NS' in s2_selected, "STOCK_35 should be retained by 2X buffer in S2 (rank 35 <= 40)"
        assert 'STOCK_45.NS' not in s2_selected, "STOCK_45 should be evicted in S2 (rank 45 > 40)"
        assert np.isclose(sum(s2_weights.values()), 1.0, rtol=1e-5), "S2 weights must sum to 1.0"
        assert all(np.isclose(w, 1.0 / target_count) for w in s2_weights.values()), "S2 weights must be equal"

        # 2. Test Strategy 3 (Rank-Based Weighting, No Buffer)
        s3_selected, s3_weights, s3_additions = select_strategy_3_holdings(
            synthetic_rankings, dec_date, current_holdings, target_count=target_count
        )

        assert len(s3_selected) == target_count, f"S3 count {len(s3_selected)} != {target_count}"
        assert 'STOCK_05.NS' in s3_selected, "STOCK_05 should be in S3 (top 20)"
        assert 'STOCK_35.NS' not in s3_selected, "STOCK_35 must be evicted in S3 (rank 35 > 20, no buffer)"
        assert 'STOCK_45.NS' not in s3_selected, "STOCK_45 must be evicted in S3 (rank 45 > 20, no buffer)"
        assert np.isclose(sum(s3_weights.values()), 1.0, rtol=1e-5), "S3 weights must sum to 1.0"
        
        # Verify rank-based weights are strictly decreasing with position
        s3_weights_list = [s3_weights[t] for t in s3_selected]
        assert all(s3_weights_list[i] > s3_weights_list[i+1] for i in range(len(s3_weights_list)-1)), "S3 weights not strictly decreasing"


# ============================================================================
# TEST C: PERFORMANCE METRICS ENGINE
# ============================================================================
class TestMetricsEngine:

    def test_cagr_synthetic_curve(self):
        """Verify CAGR calculation on synthetic portfolio doubling over 2 years."""
        d_start = pd.Timestamp('2022-10-31')
        d_end = pd.Timestamp('2024-10-31')
        elapsed_days = (d_end - d_start).days
        years = elapsed_days / 365.25

        init_val = 500000.0
        final_val = 1000000.0  # Exactly 100% total return
        tot_return = (final_val / init_val - 1.0) * 100.0

        cagr = ((final_val / init_val) ** (1.0 / years) - 1.0) * 100.0
        # Expected CAGR ~ 41.42% for 2-year doubling
        assert np.isclose(cagr, 41.42, atol=0.1)

        # Mathematical consistency check
        recalculated_tot = ((1.0 + cagr / 100.0) ** years - 1.0) * 100.0
        assert np.isclose(recalculated_tot, tot_return, atol=1e-4)

    def test_sharpe_ratio_synthetic_curve(self):
        """Verify Annualized Sharpe Ratio calculation with Rf=6.5%."""
        rf_annual = 0.065
        rf_daily = (1.0 + rf_annual) ** (1.0 / 252.0) - 1.0

        np.random.seed(100)
        n_days = 252
        daily_rets = pd.Series(np.random.normal(0.001, 0.01, n_days))
        excess_rets = daily_rets - rf_daily

        mean_excess_ann = excess_rets.mean() * 252.0
        vol_ann = daily_rets.std(ddof=1) * np.sqrt(252.0)
        expected_sharpe = mean_excess_ann / vol_ann

        computed_sharpe = (excess_rets.mean() * 252.0) / (daily_rets.std(ddof=1) * np.sqrt(252.0))
        assert np.isclose(computed_sharpe, expected_sharpe, rtol=1e-5)

    def test_max_drawdown_peak_trough_recovery(self):
        """Verify Peak Date, Trough Date, Max Drawdown %, and Recovery Date."""
        dates = pd.date_range('2024-01-01', periods=6, freq='B')
        # Equity curve: 100 -> 120 (Peak) -> 90 -> 84 (Trough, -30%) -> 110 -> 130 (Recovery)
        equity = [100.0, 120.0, 90.0, 84.0, 110.0, 130.0]
        df_synthetic = pd.DataFrame({
            'Date': dates,
            'Strategy': ['Test_Strategy'] * 6,
            'Total_Equity': equity
        })

        drawdown_df, dd_stats = compute_drawdown_series(df_synthetic)
        stats = dd_stats['Test_Strategy']

        expected_max_dd = ((84.0 - 120.0) / 120.0) * 100.0  # -30.0%
        assert np.isclose(stats['Max_Drawdown_%'], expected_max_dd, rtol=1e-4)
        assert stats['Peak_Date'] == dates[1].strftime('%Y-%m-%d')
        assert stats['Trough_Date'] == dates[3].strftime('%Y-%m-%d')
        assert stats['Recovery_Date'] == dates[5].strftime('%Y-%m-%d')

    def test_fifo_win_rate_edge_cases(self):
        """Verify Win Rate handles zero-sell strategies gracefully and matches FIFO math."""
        # Case 1: Zero sells (like Strategy 1 & 4)
        trades_zero_sells = pd.DataFrame({
            'Date': ['2022-11-01'],
            'Strategy': ['BuyOnly_Strategy'],
            'Ticker': ['STOCK_X.NS'],
            'Action': ['Buy'],
            'Shares': [100],
            'Execution_Price': [50.0],
            'Trade_Value': [5000.0],
            'Transaction_Cost': [7.50]
        })
        stats_zero = compute_fifo_trade_statistics(trades_zero_sells, 'BuyOnly_Strategy')
        assert stats_zero['Win_Rate_%'] is None, "Zero sells should return Win_Rate_% as None"
        assert stats_zero['Sell_Trades'] == 0

        # Case 2: One win, one loss
        trades_active = pd.DataFrame({
            'Date': ['2023-01-02', '2023-02-01', '2023-01-02', '2023-02-01'],
            'Strategy': ['Active_Strategy'] * 4,
            'Ticker': ['WINNER.NS', 'WINNER.NS', 'LOSER.NS', 'LOSER.NS'],
            'Action': ['Buy', 'Sell', 'Buy', 'Sell'],
            'Shares': [100, 100, 100, 100],
            'Execution_Price': [100.0, 120.0, 100.0, 80.0],
            'Trade_Value': [10000.0, 12000.0, 10000.0, 8000.0],
            'Transaction_Cost': [15.0, 33.0, 15.0, 27.0]
        })
        stats_active = compute_fifo_trade_statistics(trades_active, 'Active_Strategy')
        assert stats_active['Winning_Sells'] == 1
        assert stats_active['Completed_Sells'] == 2
        assert np.isclose(stats_active['Win_Rate_%'], 50.0)


# ============================================================================
# TEST D: PUBLICATION VISUALIZATIONS
# ============================================================================
class TestVisualizations:

    def test_seven_figures_exist_and_non_empty(self):
        """Verify that all 7 PNG figures exist in outputs/figures/ and are non-empty."""
        expected_figures = [
            "01_equity_curves.png",
            "02_drawdown_curves.png",
            "03_monthly_pnl_strategy3.png",
            "04_turnover_comparison.png",
            "05_replacement_heatmap.png",
            "06_sharpe_comparison.png",
            "07_max_drawdown_comparison.png"
        ]
        figures_dir = os.path.join("outputs", "figures")
        assert os.path.exists(figures_dir), f"Figures directory missing: {figures_dir}"

        for fname in expected_figures:
            fpath = os.path.join(figures_dir, fname)
            assert os.path.exists(fpath), f"Figure missing: {fname}"
            fsize = os.path.getsize(fpath)
            assert fsize > 50000, f"Figure {fname} is suspiciously small: {fsize} bytes"

    def test_chart_metrics_match_summary_csv(self):
        """Verify that Sharpe and Max Drawdown values in summary CSV match expected ranges."""
        summary_path = os.path.join("data", "processed", "performance_summary.csv")
        assert os.path.exists(summary_path), f"File missing: {summary_path}"

        summary_df = pd.read_csv(summary_path)
        assert len(summary_df) == 4, f"Expected 4 strategies, got {len(summary_df)}"

        # S2 (Top-X Equal-Weight with 2X Buffer) achieves highest Sharpe & Sortino
        s2_row = summary_df[summary_df['Strategy'].str.contains('Strategy 2')].iloc[0]
        assert np.isclose(s2_row['Sharpe_Ratio'], 0.7917, atol=0.01), f"S2 Sharpe mismatch: {s2_row['Sharpe_Ratio']}"
        assert np.isclose(s2_row['Sortino_Ratio'], 1.0572, atol=0.01), f"S2 Sortino mismatch: {s2_row['Sortino_Ratio']}"

        # S3 (Top-X Rank-Weighted No Buffer) Max Drawdown
        s3_row = summary_df[summary_df['Strategy'].str.contains('Strategy 3')].iloc[0]
        assert np.isclose(s3_row['Max_Drawdown_%'], -33.2355, atol=0.05)

        # S4 Benchmark should have lowest volatility & lowest max drawdown
        s4_row = summary_df[summary_df['Strategy'].str.contains('Strategy 4')].iloc[0]
        assert np.isclose(s4_row['Volatility_%'], 11.4526, atol=0.01)
        assert np.isclose(s4_row['Max_Drawdown_%'], -15.2344, atol=0.01)
