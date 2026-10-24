# Quantitative Momentum Strategy Backtesting System for Indian Equities
## An Empirical Investigation of Cross-Sectional Risk-Adjusted Momentum and Retention Buffering

---

### Executive Summary

This report presents the empirical methodology, portfolio simulation architecture, performance results, and risk characteristics of an academic quantitative momentum backtesting system applied to the Indian equity market (National Stock Exchange). Using approximately five years of daily price and volume data across 400 NSE equities from October 2021 through October 2026, the study investigates whether a **12-1 month risk-adjusted cross-sectional momentum factor** delivers persistent alpha relative to the broad market benchmark (**NIFTYBEES.NS**) and an equal-weight buy-and-hold baseline. Furthermore, the study evaluates the efficacy of a **2X rank retention buffer** and **linear rank-based portfolio weighting** in mitigating turnover and execution friction.

Across 48 completed monthly rebalancing cycles (November 2022 to October 2026; 983 trading sessions), both momentum strategies substantially outperformed the benchmark (+6.97% CAGR) and equal-weight baseline (+19.61% CAGR):
- **Strategy 2 (Top-20 Equal-Weight Momentum)** generated a final portfolio equity of **₹11,44,602.22** (+128.92% total return; **23.16% CAGR**), achieving an Annualized Sharpe Ratio of **0.80** and the highest Sortino Ratio of **1.07** ($R_f=6.5\%$).
- **Strategy 3 (Top-20 Rank-Weighted Momentum with 2X Buffer)** generated a final equity of **₹11,06,154.84** (+121.23% total return; **22.11% CAGR**), an Annualized Sharpe Ratio of **0.74**, and a Sortino Ratio of **0.99**.
- The **2X retention buffer** successfully reduced monthly portfolio name turnover by **46.4%** (from **32.81%** down to **17.60%** per month), reducing cumulative transaction costs from ₹59,181.21 to ₹57,848.88 while maintaining strong momentum factor exposure.

---

## 1. Introduction and Theoretical Foundations

The cross-sectional momentum anomaly, first formally documented by **Jegadeesh and Titman (1993)**, represents one of the most persistent and extensively verified empirical asset pricing phenomena across global equity markets (Fama & French, 2012; Asness, Moskowitz & Pedersen, 2013). The core premise establishes that assets demonstrating superior relative performance over an intermediate horizon (typically 3 to 12 months) continue to outperform their peers over subsequent holding periods (typically 1 to 12 months).

### 1.1 The 12-1 Month Momentum Skip Rationale
A standard naive 12-month return calculation incorporates the most recent month of trading ($t-1$ to $t$). However, empirical literature extensively identifies that the most immediate past month exhibits short-term mean reversion driven by market microstructure friction, liquidity provision imbalances, and bid-ask bounce (Jegadeesh, 1990; Lehmann, 1990). Consequently, academic best practice skips the most recent 21 trading days (~1 calendar month), measuring performance from month $t-12$ to $t-1$:
$$\text{Raw Momentum}_{i,t} = \frac{P_{i,t-21}}{P_{i,t-252}} - 1.0$$
where $P_{i,\tau}$ denotes the split- and dividend-adjusted closing price of stock $i$ on trading day $\tau$.

### 1.2 Risk-Adjusted Momentum Scaling
Unadjusted momentum portfolios frequently exhibit vulnerability to momentum crashes, particularly following market inflection points or macroeconomic regime shifts (Barroso & Santa-Clara, 2015; Daniel & Moskowitz, 2016). High-beta or highly speculative equities often exhibit volatile, short-lived price surges that distort pure return rankings. To penalize idiosyncratic risk and favor equities exhibiting consistent, low-volatility price appreciation, each asset's raw momentum is scaled by its historical annualized volatility:
$$\sigma_{i,t} = \text{std}\left(\{R_{i,\tau}\}_{\tau=t-251}^t\right) \times \sqrt{252}$$
$$\text{Risk-Adjusted Momentum}_{i,t} = \frac{\text{Raw Momentum}_{i,t}}{\sigma_{i,t}}$$
where $R_{i,\tau} = \frac{P_{i,\tau}}{P_{i,\tau-1}} - 1$ represents daily close-to-close returns.

### 1.3 Turnover Mitigation and Retention Buffering
High-turnover momentum strategies incur substantial transaction drag, bid-ask slippage, and statutory exchange charges that can erode paper profits (Novy-Marx & Velikov, 2016). In institutional asset management, a **retention buffer** is routinely implemented: existing holdings are retained in the portfolio as long as their ranking remains within a defined buffer zone (e.g., top $2X$), preventing premature liquidation of stocks undergoing temporary rank fluctuations.

---

## 2. Dataset Definition and Preprocessing

### 2.1 Universe Definition
The dataset consists of **504,997 historical daily records** across **400 National Stock Exchange (NSE) equity tickers** and the exchange-traded fund benchmark **`NIFTYBEES.NS`**, spanning October 2021 through October 2026. The equities encompass large-cap, mid-cap, and small-cap segments of the Indian market.

### 2.2 Point-in-Time Data Deduplication Rule
Inspection of the raw dataset (`data/ohlcv_data.csv`) revealed duplicate records arising from concurrent thread downloads in the initial collection stage:
1. **Exact Duplicate Rows**: 7,612 identical rows across all columns were detected and dropped.
2. **Conflicting Date-Ticker Micro-Float Discrepancies**: 3,511 Date-Ticker pairs (7,022 rows across 8 tickers) exhibited microscopic price variations ($< ₹0.0015$, well below the NSE minimum tick size of ₹0.05). Volume, Dividends, and Stock Splits were strictly identical (0.0 difference).

A documented, defensible resolution rule was implemented in `src/momentum.py`:
- Discrepancies exceeding the NSE tick tolerance ($> ₹0.05$) trigger a hard `DataIntegrityError`.
- Discrepancies within tick tolerance are reconciled by computing the exact arithmetic mean of `Open`, `High`, `Low`, and `Close`, yielding **493,874 unique, verified daily records**.

### 2.3 Benchmark Isolation
`NIFTYBEES.NS` represents the Nippon India ETF Nifty BeES, tracking the Nifty 50 Index. To prevent contamination of the stock selection universe, the backtesting system enforces complete isolation:
- `NIFTYBEES.NS` is strictly excluded from `monthly_momentum_rankings.csv` (verified by automated tests).
- Benchmark data is loaded separately from `data/benchmark_niftybees.csv` and assigned exclusively to Strategy 4.

---

## 3. Signal Generation and Rebalance Scheduling

### 3.1 Decision Timing and Look-Ahead Prevention
- **Decision Date ($T_{\text{dec}}$)**: The final available trading session of each complete calendar month.
- **Warmup Lookback**: The initial 252 trading days (October 2021 to October 2022) serve exclusively as the statistical estimation window. The first valid decision date is **October 31, 2022**.
- **Incomplete Terminal Month**: Because the dataset ends on October 22, 2026 (an incomplete calendar month), October 2026 is excluded from signal generation. The 48th and final decision date is **September 30, 2026**.
- **Deterministic Tie-Breaking**: Stocks exhibiting identical risk-adjusted momentum scores are ranked alphabetically by ticker symbol to guarantee reproducible, deterministic portfolio selection.

### 3.2 Execution Schedule
Orders are executed at the **Market Open of the immediately succeeding trading session ($T_{\text{exec}} = T_{\text{dec}} + 1$)**. Under no circumstances does execution occur at the decision date Close, eliminating look-ahead bias and simulating realistic next-day execution.

```text
Decision Date (Month-End Close) ----> Signal Computation
                                              |
                                              v
Next Trading Day (Market Open) -------> Two-Phase Order Execution
```

---

## 4. Four Investment Strategies

| Strategy | Selection Universe | Weighting Scheme | Rebalancing Frequency | Share Unit Constraints |
| :--- | :--- | :--- | :--- | :--- |
| **Strategy 1: Top-X Buy-and-Hold** | Top $X=20$ on first decision date | Equal Weight ($1/X = 5\%$) | Buy once at inception; hold forever | Fractional shares |
| **Strategy 2: Top-X Equal-Weight (2X Buffer)** | Top $X=20$ preferred; retain incumbents ranked $\le 2X=40$ | Equal Weight ($1/X = 5\%$) | Monthly rebalance; sell names ranked $> 40$ | Whole shares only |
| **Strategy 3: Top-X Rank-Weighted (No Buffer)** | Top $X=20$ strictly by momentum rank | Linear Rank Weights: $w_N = \frac{X+1-N}{X(X+1)/2}$ | Monthly rebalance; sell names falling outside Top 20 | Whole shares only |
| **Strategy 4: NIFTYBEES Benchmark Buy-and-Hold** | `NIFTYBEES.NS` standalone | 100% allocation | Buy once at inception; hold forever | Whole shares only |

### 4.1 Strategy 3 Linear Rank Weighting
For the $K$ actual holdings selected in Strategy 3 ($K=20$), holdings are ordered by cross-sectional momentum rank. Target weights are allocated linearly:
$$w_N = \frac{K + 1 - N}{\sum_{j=1}^K j} = \frac{K + 1 - N}{\frac{K(K + 1)}{2}}$$
For $K=20$, the denominator is $\frac{20 \times 21}{2} = 210$:
- Position 1 (Highest Momentum): $w_1 = \frac{20}{210} \approx 9.52\%$
- Position 2: $w_2 = \frac{19}{210} \approx 9.05\%$
- Position 20 (Lowest Momentum): $w_{20} = \frac{1}{210} \approx 0.48\%$
- $\sum_{N=1}^{20} w_N = 1.000000$ (100.0%).

### 4.2 Realistic Order Execution and Cash Accounting Engine
1. **Initial Capital**: ₹5,00,000.00 allocated separately to each strategy.
2. **Two-Phase Rebalance**:
   - **Phase 1 (Liquidations First)**: Liquidations and position trimmings execute first. Net proceeds (sale value minus transaction costs) immediately replenish available cash.
   - **Phase 2 (Purchases Next)**: New purchases and position increases are sized based on total portfolio equity.
3. **Whole-Share Affordability**: The maximum whole shares purchased is bounded by:
   $$\text{Max Shares} = \left\lfloor \frac{\text{Available Cash}}{P_{\text{open}} \times (1 + \text{Fee}_{\text{var}})} \right\rfloor$$
   If available cash cannot purchase at least 1 whole share, the order is skipped and cash remains idle.
4. **Transaction Costs**:
   - Variable Fee: **0.15%** of gross traded value applied to all buys and sells.
   - Fixed Sell Fee: Flat **₹15.00** charge applied to every sell order (reflecting DP and exchange transaction charges in the Indian equity market).
5. **Mark-to-Market Ledger**: Every portfolio is marked to market at the end of every trading session using verified closing prices. Stale pricing fallbacks preserve capital during temporary feed outages.

---

## 5. Empirical Results & Discussion

The backtest was executed across **983 trading sessions** from October 31, 2022 to October 22, 2026. The table below presents the verified results extracted directly from [`data/processed/performance_summary.csv`](file:///c:/projects/stock_momentum_strategy/data/processed/performance_summary.csv).

### 5.1 Master Performance Summary

| Performance Metric | Strategy 1: Equal-Weight B&H | Strategy 2: Top-20 EW Momentum | Strategy 3: Top-20 Buffer (Core) | Strategy 4: NIFTYBEES Benchmark |
| :--- | :---: | :---: | :---: | :---: |
| **Initial Capital (INR)** | ₹5,00,000.00 | ₹5,00,000.00 | ₹5,00,000.00 | ₹5,00,000.00 |
| **Final Portfolio Value (INR)** | **₹10,19,050.30** | **₹11,44,602.22** | **₹11,06,154.84** | **₹6,53,568.49** |
| **Total Net Return (%)** | +103.81% | +128.92% | +121.23% | +30.71% |
| **CAGR (Annualized)** | 19.61% | 23.16% | 22.11% | 6.97% |
| **Annualized Volatility (%)** | 18.28% | 21.64% | 22.55% | 11.45% |
| **Annualized Sharpe Ratio ($R_f=6.5\%$)** | 0.75 | **0.80** | 0.74 | 0.11 |
| **Annualized Sortino Ratio ($R_f=6.5\%$)** | 0.99 | **1.07** | 0.99 | 0.15 |
| **Maximum Drawdown (%)** | -25.50% | -29.51% | -32.07% | **-15.23%** |
| **Peak Equity Date** | 2024-09-24 | 2024-07-11 | 2024-07-11 | 2024-09-27 |
| **Trough Equity Date** | 2025-03-03 | 2025-02-28 | 2025-02-28 | 2025-03-04 |
| **Drawdown Recovery Date** | *Not Recovered* | *Not Recovered* | *Not Recovered* | 2025-10-23 |
| **Total Executed Trades** | 389 | 1,175 | 1,102 | 1 |
| **Buy / Sell Orders** | 389 / 0 | 603 / 572 | 501 / 601 | 1 / 0 |
| **FIFO Round-Trip Win Rate (%)** | N/A | **66.96%** (383 / 572) | 57.40% (345 / 601) | N/A |
| **Average Monthly Name Turnover (%)** | 100.0% *(inception)* | 32.81% | **17.60%** | 100.0% *(inception)* |
| **Average Traded-Value Turnover (%)** | 100.0% *(inception)* | 35.55% | **32.49%** | 100.0% *(inception)* |
| **Total Transaction Costs Incurred (INR)** | ₹750.77 | ₹59,181.21 | ₹57,848.88 | ₹748.87 |

---

### 5.2 Comparative Return Analysis
As illustrated in Figure 1 (`01_equity_curves.png`), both momentum strategies generated substantial excess returns relative to the benchmark:
- **Strategy 2 (Unbuffered Top-20 Momentum)** achieved the highest final equity of **₹11,44,602.22** (+128.92% net return; **23.16% CAGR**), outperforming the NIFTYBEES benchmark by **+16.19 percentage points annualized**.
- **Strategy 3 (Rank-Weighted Momentum with Retention Buffer)** generated **₹11,06,154.84** (+121.23% net return; **22.11% CAGR**), outpacing the benchmark by **+15.14 percentage points annualized**.
- **Strategy 1 (Equal-Weight Baseline)** delivered **₹10,19,050.30** (+103.81% net return; **19.61% CAGR**), reflecting broad mid-cap equity appreciation over the 2022-2024 Indian market expansion.
- **Strategy 4 (NIFTYBEES Benchmark)** ended at **₹6,53,568.49** (+30.71% net return; **6.97% CAGR**).

![Equity Growth Curves](outputs/figures/01_equity_curves.png)

---

### 5.3 Risk-Adjusted Return & Downside Deviation
In accordance with academic standards, downside deviation penalizes only daily returns falling below the daily compounded risk-free hurdle ($r_{f,\text{daily}} = 0.024987\%/\text{day}$, corresponding to 6.50% annualized).

- **Sharpe Ratio ($R_f=6.5\%$)**: Strategy 2 delivered the highest Sharpe Ratio of **0.80**, compared to Strategy 1 (0.75), Strategy 3 (0.74), and NIFTYBEES (0.11).
- **Sortino Ratio ($R_f=6.5\%$)**: Strategy 2 achieved the highest Sortino Ratio (**1.07**), indicating superior excess return generation per unit of downside risk. Strategy 3 achieved **0.99**, while NIFTYBEES achieved **0.15** (Figure 6, `06_sharpe_comparison.png`).

![Sharpe Comparison](outputs/figures/06_sharpe_comparison.png)

---

### 5.4 Drawdown Cycles and Recovery Characteristics
As depicted in Figure 2 (`02_drawdown_curves.png`) and Figure 7 (`07_max_drawdown_comparison.png`), the backtest captures a full market cycle:
1. **The Bull Phase (Nov 2022 – Jul 2024)**: Aggressive capital appreciation driven by capital goods, defense, railway, and manufacturing equities. Strategy 3 reached an all-time high of ₹15,17,349.62 on July 11, 2024.
2. **The Correction Phase (Jul 2024 – Feb 2025)**: Broad-based valuation compression in mid- and small-cap momentum leaders. Strategy 3 bottomed at ₹10,30,727.24 on February 28, 2025, recording a maximum drawdown of **-32.07%**. Strategy 2 bottomed at ₹9,49,715.06 on February 28, 2025 (**-29.51% Max Drawdown**).
3. **Benchmark Resilience**: NIFTYBEES suffered a shallower drawdown of **-15.23%** (bottoming March 4, 2025) and fully recovered by October 23, 2025. In contrast, the high-beta equity strategies had not yet regained their July 2024 peak by October 2026.

![Drawdown Curves](outputs/figures/02_drawdown_curves.png)
![Max Drawdown Comparison](outputs/figures/07_max_drawdown_comparison.png)

---

### 5.5 Turnover Reduction and Buffer Efficiency
A central empirical hypothesis of this research is that a **2X retention buffer** reduces portfolio churn without sacrificing momentum factor exposure:
- **Name Turnover**: Strategy 2 experienced an average monthly name turnover of **32.81%** (replacing an average of 6.56 stocks each month; 315 total replacements). Strategy 3 exhibited an average monthly name turnover of **17.60%** (replacing 3.52 stocks each month; 169 total replacements). **The buffer cut portfolio replacement by 46.4%** (Figure 4, `04_turnover_comparison.png`).
- **Transaction Cost Savings**: Strategy 3 saved ₹1,332.33 in transaction costs relative to Strategy 2 (incurring ₹57,848.88 vs ₹59,181.21).
- **Holding Horizon**: As demonstrated in the stock replacement heatmap (Figure 5, `05_replacement_heatmap.png`), top performers were held continuously across multi-year trends (e.g., `ANANDRATHI.NS` held for 28 months, `APARINDS.NS` and `MCX.NS` held for 21 months).

![Turnover Comparison](outputs/figures/04_turnover_comparison.png)
![Replacement Heatmap](outputs/figures/05_replacement_heatmap.png)

---

### 5.6 Trade Statistics and FIFO Win Rates
Using strict First-In, First-Out (FIFO) lot matching:
- **Strategy 2 (Unbuffered)**: 572 completed sell orders, of which 383 were profitable, yielding a **66.96% win rate**. Because unbuffered momentum ruthlessly cuts stocks the instant they fall to rank 21, positions are closed rapidly before deep drawdowns compound.
- **Strategy 3 (Buffered)**: 601 completed sell orders, of which 345 were profitable, yielding a **57.40% win rate**. The 2X buffer holds declining names through ranks 21–40; during market pullbacks, some retained positions experienced deeper losses before being evicted at rank 41.
- **Monthly P&L for Strategy 3**: Across 48 completed months, 26 months were profitable (54.2%) and 22 months recorded losses, generating a cumulative net profit of ₹6,06,154.84 (Figure 3, `03_monthly_pnl_strategy3.png`).

![Monthly P&L Strategy 3](outputs/figures/03_monthly_pnl_strategy3.png)

---

## 6. Research Limitations & Practical Considerations

To ensure institutional and academic rigor, several real-world limitations must be acknowledged:

1. **Survivorship Bias**: The underlying stock universe was defined based on equities active in the Indian market as of 2026. Equities that were delisted, merged, or declared bankrupt during the 2021-2026 period are not present in the historical feed. In cross-sectional momentum, survivorship bias tends to artificially elevate historical backtest returns.
2. **Back-Adjusted Execution Prices**: Price data sourced from yfinance reflects split- and dividend-adjusted closing prices. While daily percentage returns are mathematically preserved, historical market open prices during high-corporate-action events can exhibit micro-discrepancies relative to live unadjusted order books.
3. **Simplified Execution Friction**: The backtest models a fixed 0.15% variable fee and ₹15 fixed fee per sell transaction. In live trading, institutional orders experience **market impact** and **bid-ask slippage**, especially in less liquid mid- and small-cap momentum constituents during sharp selloffs.
4. **Zero Interest on Cash**: Idle cash balances earn 0.00% interest. In professional wealth management, uninvested cash is deployed into overnight liquid funds or collateralized borrowing and lending obligations (CBLO/TREPS), earning ~5–7% annualized.
5. **Non-Stationarity of Alpha**: Historical momentum outperformance over 2022-2026 was supported by strong macroeconomic expansion and retail liquidity inflows in the Indian market. Momentum strategies can experience extended underperformance ("momentum crashes") during sharp macroeconomic reversals.

---

## 7. Project Verification Checklist

| Project Stage | Module | Status | Verification Evidence |
| :--- | :--- | :---: | :--- |
| **Stage 1 & 2: Data Collection & Cleaning** | `data/ohlcv_data.csv` | **Completed & Verified** | 493,874 clean rows; duplicate resolution documented in `data_quality_report.csv`. |
| **Stage 3: Momentum Ranking Engine** | `src/momentum.py` | **Completed & Verified** | 18,732 rankings generated across 48 dates; benchmark strictly excluded; ties broken alphabetically. |
| **Stage 4: Portfolio Simulation** | `src/backtest.py` | **Completed & Verified** | 4 strategies modeled across 983 trading days; cash non-negativity and integer share constraints passed. |
| **Stage 5: Performance Metrics Engine** | `src/metrics.py` | **Completed & Verified** | CAGR, Sharpe, Sortino, Drawdown, and FIFO Win Rate calculated; 4 validation checks passed. |
| **Stage 6: Publication Visualizations** | `src/visualize.py` | **Completed & Verified** | 7 high-resolution PNG charts generated in `outputs/figures/` (300 DPI). |
| **Stage 7: Automated End-to-End Testing** | `tests/test_backtest.py` | **Completed & Verified** | **15 of 15 automated pytest unit tests PASSED (0.88s)** across Tests A, B, C, and D. |
| **Known Limitations Documented** | `PROJECT_REPORT.md` | **Completed & Verified** | Survivorship bias, back-adjusted prices, slippage, and zero cash drag transparently analyzed. |

---

## 8. Academic References

1. **Asness, C. S., Moskowitz, T. J., & Pedersen, L. H.** (2013). Value and Momentum Everywhere. *The Journal of Finance*, 68(3), 929-985.
2. **Barroso, P., & Santa-Clara, P.** (2015). Momentum has its moments. *Journal of Financial Economics*, 116(1), 111-120.
3. **Carhart, M. M.** (1997). On Persistence in Mutual Fund Performance. *The Journal of Finance*, 52(1), 57-82.
4. **Daniel, K., & Moskowitz, T. J.** (2016). Momentum Crashes. *Journal of Financial Economics*, 122(2), 221-247.
5. **Fama, E. F., & French, K. R.** (2012). Size, value, and momentum in international stock returns. *Journal of Financial Economics*, 105(3), 457-472.
6. **Jegadeesh, N.** (1990). Evidence of Predictable Behavior of Security Returns. *The Journal of Finance*, 45(3), 881-898.
7. **Jegadeesh, N., & Titman, S.** (1993). Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency. *The Journal of Finance*, 48(1), 65-91.
8. **Lehmann, B. N.** (1990). Fads, Martingales, and Market Efficiency. *The Quarterly Journal of Economics*, 105(1), 1-28.
9. **Novy-Marx, R., & Velikov, M.** (2016). A Taxonomy of Anomalies and Their Trading Costs. *The Review of Financial Studies*, 29(1), 104-147.
