# Quantitative Momentum Strategy Backtesting System

**An empirical analysis of risk-adjusted cross-sectional momentum and retention buffering in Indian Equities (NSE).**

This project is a full-stack, institutional-grade quantitative research platform designed to evaluate momentum-based equity portfolio strategies. It combines a rigorous Python backtesting engine with a modern React dashboard to simulate, visualize, and analyze portfolio performance under realistic retail trading constraints.

---

## 🎯 Project Objective

The core objective is to test whether a **Volatility-Minimized 12-1 Month Momentum Factor** generates superior risk-adjusted returns compared to the broader Indian market (NIFTYBEES). Furthermore, it evaluates how **rank-based portfolio weighting** and a **2X retention buffer** impact portfolio turnover, transaction costs, and overall capital preservation.

---

## 📊 The Four Investment Strategies

The system dynamically simulates four distinct portfolio construction approaches based on user-defined capital and target stock count ($X$):

1. **Strategy 1: Top-X Buy-and-Hold (Passive Baseline)**
   Selects the initial Top $X$ stocks by momentum rank and holds them indefinitely without rebalancing. Serves as a baseline to prove the value of active management.

2. **Strategy 2: Top-X Equal-Weight WITH 2X Buffer (Turnover Mitigation)**
   Selects the Top $X$ stocks with equal capital allocation. It applies a **2X Retention Buffer**: existing holdings are kept as long as their rank remains $\le 2X$, drastically reducing unnecessary churn and transaction fees.

3. **Strategy 3: Top-X Rank-Weighted, NO Buffer (Aggressive Core)**
   Selects the Top $X$ stocks but applies **Linear Rank-Based Weighting** (Rank 1 gets the most capital, Rank $X$ gets the least). It has **no retention buffer**, ruthlessly exiting any stock that drops out of the Top $X$.

4. **Strategy 4: NIFTYBEES Benchmark (Market Reality Check)**
   Buys and holds the `NIFTYBEES.NS` ETF to represent the Nifty 50 index, providing a passive market benchmark for comparison.

---

## 🧠 Methodology & Signal Generation

*   **12-1 Month Momentum:** Calculates returns from month $t-12$ to $t-1$, skipping the most recent 21 trading days to mitigate short-term mean reversion and bid-ask bounce (Jegadeesh & Titman, 1993).
*   **Volatility Minimization:** Raw momentum is divided by 252-day annualized volatility. This penalizes erratic, high-beta stocks and favors consistent, low-risk winners.
    $$\text{Score} = \frac{\text{Raw Momentum}}{\text{Annualized Volatility}}$$
*   **Rank-Based Weighting Formula:** 
    $$\text{Weight}(N) = \frac{X + 1 - N}{\frac{X(X + 1)}{2}}$$
*   **Realistic Execution:** Next-day Open execution, strict whole-share integer rounding, two-phase liquidation-then-purchase rebalancing, non-negative cash constraints, and explicit transaction costs (0.15% variable + ₹15 fixed sell fee).

---

## 🛠️ Technology Stack

### Backend & Data Science
*   **Python 3.10+**: Core simulation engine.
*   **FastAPI**: High-performance, asynchronous REST API with in-memory caching and concurrency locks.
*   **Pandas & NumPy**: Vectorized financial calculations and data manipulation.
*   **Pytest**: 27 automated unit and integration tests guaranteeing mathematical integrity.

### Frontend & Visualization
*   **React (Vite)**: Fast, modern single-page application.
*   **Tailwind CSS**: Responsive, institutional-grade UI design.
*   **Recharts**: Interactive, dynamic financial charts (Equity Curves, Drawdowns, P&L).
*   **Lucide React**: Professional iconography.

---

## 📁 Project Structure

```text
stock_momentum_strategy/
├── api/                  # FastAPI backend wrapper (main.py)
├── frontend/             # React Vite application
│   ├── src/
│   │   ├── components/   # UI Tabs (Overview, Performance, Charts, Holdings, Methodology)
│   │   ├── utils/        # Formatting and metric calculation helpers
│   │   └── api/          # Fetch client for backend communication
├── src/                  # Core Python engine
│   ├── backtest.py       # Portfolio simulation and execution logic
│   ├── momentum.py       # Factor computation and ranking engine
│   ├── metrics.py        # CAGR, Sharpe, Sortino, Drawdown calculations
│   └── service.py        # Headless API service layer
├── tests/                # Pytest automated test suite (27 tests)
├── data/                 # Processed CSV outputs
└── outputs/              # Generated static PNG figures
