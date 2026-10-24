# Quantitative Momentum Strategy Backtesting System for Indian Equities

An academically rigorous, point-in-time quantitative research and portfolio backtesting system designed to evaluate risk-adjusted cross-sectional momentum strategies on National Stock Exchange (NSE) equities, benchmarked against `NIFTYBEES.NS`.

---

## 1. Project Objective and Scope

This project implements an end-to-end quantitative backtesting pipeline:
1. **Factor Computation**: Computes risk-adjusted 12-1 month cross-sectional momentum rankings across 400 NSE equities, strictly excluding the benchmark from the stock selection universe and penalizing idiosyncratic volatility.
2. **Realistic Execution Engine**: Simulates four discrete investment strategies using realistic execution rules:
   - Month-end signal generation paired with next-session Market Open execution (strictly preventing look-ahead bias).
   - Strict whole-share rounding with two-phase liquidation-then-purchase rebalancing.
   - Non-negative cash constraints (0% idle interest).
   - Real-world institutional friction: 0.15% variable transaction fees plus a flat ₹15 sell fee per liquidated position.
3. **Academic Evaluation**: Generates comprehensive risk-adjusted performance metrics, drawdown analytics, FIFO-based round-trip trade statistics, and seven publication-quality visualizations.

---

## 2. Repository Structure

```text
stock_momentum_strategy/
├── data/
│   ├── ohlcv_data.csv                       # Historical daily OHLCV dataset (400 NSE equities)
│   ├── benchmark_niftybees.csv              # Standalone NIFTYBEES.NS benchmark data
│   └── processed/
│       ├── data_quality_report.csv          # Audit trail of data deduplication & clean metrics
│       ├── monthly_momentum_rankings.csv    # Cross-sectional momentum rankings (48 cycles)
│       ├── daily_portfolio_values.csv       # Daily cash, market value, equity, & holdings
│       ├── trade_log.csv                    # Complete chronological order execution ledger
│       ├── monthly_holdings.csv             # Portfolio composition at each rebalance
│       ├── turnover.csv                     # Name and traded-value turnover percentages
│       ├── performance_summary.csv          # Master strategy comparison metrics table
│       ├── monthly_returns.csv              # Month-end returns (%) and rupee P&L time series
│       └── drawdown_series.csv              # Daily equity, running high-water mark, & drawdown %
├── outputs/
│   └── figures/
│       ├── 01_equity_curves.png             # Total equity growth curves across all strategies
│       ├── 02_drawdown_curves.png           # Underwater percentage drawdown profiles
│       ├── 03_monthly_pnl_strategy3.png     # Monthly rupee profit/loss for Strategy 3
│       ├── 04_turnover_comparison.png       # Grouped bar chart of name and value turnover
│       ├── 05_replacement_heatmap.png       # Churn and retention heatmap (Top 15 stocks)
│       ├── 06_sharpe_comparison.png         # Annualized Sharpe Ratio comparison (Rf=6.5%)
│       └── 07_max_drawdown_comparison.png   # Maximum peak-to-trough decline comparison
├── src/
│   ├── __init__.py                          # Package initialization
│   ├── momentum.py                          # Stage 3: Momentum factor & ranking engine
│   ├── backtest.py                          # Stage 4: Four-strategy portfolio simulation engine
│   ├── metrics.py                           # Stage 5: Quantitative performance & risk metrics
│   └── visualize.py                         # Stage 6: Publication-quality charting pipeline
├── tests/
│   └── test_backtest.py                     # Stage 7: Automated pytest test suite (15 tests)
├── README.md                                # Project overview, setup, and pipeline commands
└── PROJECT_REPORT.md                        # Formal academic research report & methodology
```

---

## 3. Installation & Dependencies

The project requires Python 3.10+ (tested on Python 3.12 64-bit). Install required dependencies via `pip`:

```bash
pip install pandas numpy matplotlib seaborn scipy pytest
```

---

## 4. Pipeline Execution Commands

The complete system is modularized and can be executed sequentially from the repository root:

### Step 1: Calculate Momentum Factors & Rankings (Stage 3)
```bash
python src/momentum.py
```
*Generates `data/processed/monthly_momentum_rankings.csv` across 48 monthly decision dates (`2022-10-31` to `2026-09-30`) and `data/processed/data_quality_report.csv`.*

### Step 2: Run Four-Strategy Portfolio Backtest (Stage 4)
```bash
python src/backtest.py
```
*Simulates daily ledger accounting across 983 trading sessions for all four strategies. Generates `daily_portfolio_values.csv`, `trade_log.csv`, `monthly_holdings.csv`, and `turnover.csv`, then runs 7 programmatic validation checks.*

### Step 3: Compute Comprehensive Performance Metrics (Stage 5)
```bash
python src/metrics.py
```
*Calculates CAGR, Annualized Volatility, Sharpe Ratio ($R_f=6.5\%$), Sortino Ratio, Maximum Drawdown (Peak/Trough/Recovery dates), and FIFO round-trip win rates. Generates `performance_summary.csv`, `monthly_returns.csv`, and `drawdown_series.csv`.*

### Step 4: Generate Publication Figures (Stage 6)
```bash
python src/visualize.py
```
*Renders all 7 high-resolution publication charts in `outputs/figures/`.*

### Step 5: Execute Automated Test Suite (Stage 7)
```bash
python -m pytest tests/test_backtest.py -v
```
*Runs all 15 automated validation unit tests verifying momentum factor math, accounting constraints, metric calculations, and chart fidelity.*

---

## 5. Description of Generated Artifacts

### Processed Datasets (`data/processed/`)
| File | Records | Key Columns & Description |
| :--- | :---: | :--- |
| `monthly_momentum_rankings.csv` | 18,732 | `decision_date`, `ticker`, `raw_momentum`, `annualized_volatility`, `risk_adjusted_momentum`, `rank`. Point-in-time cross-sectional rankings. |
| `daily_portfolio_values.csv` | 3,932 | `Date`, `Strategy`, `Cash`, `Market_Value`, `Total_Equity`, `Holdings_Count`. Daily mark-to-market valuations. |
| `trade_log.csv` | 2,667 | `Date`, `Strategy`, `Ticker`, `Action`, `Shares`, `Execution_Price`, `Trade_Value`, `Transaction_Cost`. Complete audit trail of executed orders. |
| `monthly_holdings.csv` | 2,310 | `Date`, `Strategy`, `Ticker`, `Shares`, `Target_Weight`, `Actual_Weight`. Post-rebalance portfolio composition. |
| `turnover.csv` | 98 | `Date`, `Strategy`, `Name_Turnover (%)`, `Traded_Value_Turnover (%)`. Portfolio churn per rebalance event. |
| `performance_summary.csv` | 4 | Master 19-column summary table containing all return, risk, trade, and cost metrics for each strategy. |
| `monthly_returns.csv` | 192 | `Date`, `Strategy`, `Monthly_Return_%`, `Monthly_Profit_Loss_INR`. 48 completed monthly return records per strategy. |
| `drawdown_series.csv` | 3,932 | `Date`, `Strategy`, `Total_Equity`, `Running_Peak_Equity`, `Drawdown_%`. Daily underwater series. |

### Publication Charts (`outputs/figures/`)
| Figure | Name | Description |
| :--- | :--- | :--- |
| `01_equity_curves.png` | Portfolio Equity Growth | Net asset value growth curves for all four strategies initialized at ₹5,00,000. |
| `02_drawdown_curves.png` | Underwater Drawdown Curves | Percentage drawdown from high-water mark with light red underwater shading. |
| `03_monthly_pnl_strategy3.png` | Strategy 3 Monthly P&L | Bar chart of monthly rupee gains and losses for the core strategy. |
| `04_turnover_comparison.png` | Turnover Comparison | Grouped bar chart comparing Name Turnover vs Traded-Value Turnover across all strategies. |
| `05_replacement_heatmap.png` | Churn & Retention Heatmap | Visualizes New Entries, Held positions, and Exits for the Top 15 holdings in Strategy 3. |
| `06_sharpe_comparison.png` | Annualized Sharpe Ratio | Horizontal bar chart comparing Sharpe ratios ($R_f=6.5\%$). |
| `07_max_drawdown_comparison.png` | Maximum Drawdown | Horizontal bar chart comparing peak-to-trough historical drawdowns. |

---

## 6. Summary Performance Comparison

| Metric | S1: Equal-Weight B&H | S2: Top-20 EW Momentum | S3: Top-20 Buffer (Core) | S4: NIFTYBEES Benchmark |
| :--- | :---: | :---: | :---: | :---: |
| **Initial Capital** | ₹5,00,000.00 | ₹5,00,000.00 | ₹5,00,000.00 | ₹5,00,000.00 |
| **Final Value** | ₹10,19,050.30 | ₹11,44,602.22 | ₹11,06,154.84 | ₹6,53,568.49 |
| **Total Net Return (%)** | +103.81% | +128.92% | +121.23% | +30.71% |
| **CAGR (Annualized)** | 19.61% | 23.16% | 22.11% | 6.97% |
| **Annualized Volatility** | 18.28% | 21.64% | 22.55% | 11.45% |
| **Sharpe Ratio ($R_f=6.5\%$)** | 0.75 | 0.80 | 0.74 | 0.11 |
| **Sortino Ratio ($R_f=6.5\%$)** | 0.99 | 1.07 | 0.99 | 0.15 |
| **Maximum Drawdown (%)** | -25.50% | -29.51% | -32.07% | -15.23% |
| **Total Transaction Costs** | ₹750.77 | ₹59,181.21 | ₹57,848.88 | ₹748.87 |
| **Avg Monthly Name Turnover** | 0.00% *(after buy)* | 32.81% | 17.60% | 0.00% *(after buy)* |
| **Completed Trades (Buys/Sells)** | 389 (389 / 0) | 1,175 (603 / 572) | 1,102 (501 / 601) | 1 (1 / 0) |
| **FIFO Round-Trip Win Rate** | N/A | 66.96% | 57.40% | N/A |

*For complete academic methodology, mathematical proofs, factor literature citations, and research limitations, refer to [PROJECT_REPORT.md](PROJECT_REPORT.md).*
