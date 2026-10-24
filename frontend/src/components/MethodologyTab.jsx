import React from 'react';
import {
  BookOpen,
  Sliders,
  TrendingUp,
  Activity,
  Scale,
  ShieldCheck,
  DollarSign,
  AlertTriangle,
  Info,
  Calendar,
  Clock,
  Layers,
  Sparkles,
} from 'lucide-react';
import { formatINR, formatUnsignedPercent, formatDate } from '../utils/format';

/**
 * src/components/MethodologyTab.jsx
 * =================================
 * Academically rigorous explanation of strategy design, mathematical formulations,
 * simulation parameters, execution mechanics, and real-world friction models.
 */
export default function MethodologyTab({ result }) {
  const meta = result?.meta;

  // Dynamic parameters safely resolved with fallbacks
  const capital = meta?.capital != null ? formatINR(meta.capital) : '₹5,00,000.00';
  const targetX = meta?.x != null ? meta.x : 20;

  // Backend stores risk_free_rate as decimal 0.065 (6.50% annual)
  const rfDisplay =
    meta?.risk_free_rate != null
      ? formatUnsignedPercent(meta.risk_free_rate * 100, 2)
      : '6.50%';

  const tradingDaysPerYear = 252; // Verified from engine TRADING_DAYS_PER_YEAR = 252
  const variableCostDisplay = '0.15%'; // Verified from engine VAR_COST = 0.0015
  const fixedSellFeeDisplay = '₹15.00'; // Verified from engine FIXED_SELL_COST = 15.0

  const firstDate = meta?.first_date ? formatDate(meta.first_date) : '31-Oct-2022';
  const lastDate = meta?.last_date ? formatDate(meta.last_date) : '22-Oct-2026';
  const totalTradingDays = meta?.trading_days != null ? meta.trading_days : 983;
  const totalRebalances = meta?.rebalances != null ? meta.rebalances : 48;

  // Rank 1 weight calculation for targetX
  const rank1WeightPct = ((targetX / ((targetX * (targetX + 1)) / 2)) * 100).toFixed(2);
  const rankXWeightPct = ((1 / ((targetX * (targetX + 1)) / 2)) * 100).toFixed(2);

  return (
    <div className="space-y-8 animate-fadeIn text-slate-800">
      {/* =========================================================================
          A. SIMULATION PARAMETERS HEADER GRID
          ========================================================================= */}
      <section className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-7 shadow-xs">
        <div className="flex items-center space-x-3 mb-5">
          <div className="p-2.5 rounded-xl bg-blue-50 text-navy border border-blue-100 flex-shrink-0">
            <Sliders className="w-5 h-5 text-navy" />
          </div>
          <div>
            <h2 className="text-lg sm:text-xl font-bold text-slate-900 tracking-tight">
              Simulation Specifications & Model Parameters
            </h2>
            <p className="text-xs sm:text-sm text-slate-500">
              Point-in-time configuration parameters applied to all strategy runs
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
          {/* Initial Capital */}
          <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Initial Capital
            </div>
            <div className="text-sm sm:text-base font-extrabold text-slate-900 mt-1 font-mono">
              {capital}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Per Strategy</div>
          </div>

          {/* Target Stocks (X) */}
          <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Target Basket (X)
            </div>
            <div className="text-sm sm:text-base font-extrabold text-navy mt-1 font-mono">
              Top {targetX} Equities
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Rank selection</div>
          </div>

          {/* Risk-Free Rate */}
          <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Risk-Free Rate
            </div>
            <div className="text-sm sm:text-base font-extrabold text-slate-900 mt-1 font-mono">
              {rfDisplay}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Annualized Rf</div>
          </div>

          {/* Trading Days Per Year */}
          <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Annualization Base
            </div>
            <div className="text-sm sm:text-base font-extrabold text-slate-900 mt-1 font-mono">
              {tradingDaysPerYear} Days
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Trading sessions</div>
          </div>

          {/* Variable Cost */}
          <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Variable Slippage
            </div>
            <div className="text-sm sm:text-base font-extrabold text-amber-700 mt-1 font-mono">
              {variableCostDisplay}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Gross trade value</div>
          </div>

          {/* Fixed Sell Fee */}
          <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-3.5">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Fixed Sell Fee
            </div>
            <div className="text-sm sm:text-base font-extrabold text-amber-700 mt-1 font-mono">
              {fixedSellFeeDisplay}
            </div>
            <div className="text-[11px] text-slate-500 mt-0.5">Per sell order</div>
          </div>
        </div>

        {/* Backtest Dataset Horizon Bar */}
        <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between text-xs text-slate-500 gap-2">
          <div className="flex items-center space-x-2">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span>
              Evaluation Horizon:{' '}
              <strong className="text-slate-800">{firstDate}</strong> to{' '}
              <strong className="text-slate-800">{lastDate}</strong>
            </span>
          </div>
          <div className="flex items-center space-x-4">
            <span>
              Simulated Sessions: <strong className="text-slate-800">{totalTradingDays}</strong>
            </span>
            <span>
              Monthly Rebalances: <strong className="text-slate-800">{totalRebalances}</strong>
            </span>
          </div>
        </div>
      </section>

      {/* =========================================================================
          B. FIVE METHODOLOGY SECTIONS
          ========================================================================= */}
      <div className="space-y-6">
        {/* 1. 12-1 Month Momentum */}
        <article className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-7 shadow-xs">
          <div className="flex items-start space-x-3.5">
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-navy flex items-center justify-center flex-shrink-0 font-bold border border-blue-100 text-sm">
              1
            </div>
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <h3 className="text-base sm:text-lg font-bold text-slate-900">
                  12-1 Month Momentum Signal Formulation
                </h3>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-navy border border-blue-200">
                  Signal Generation
                </span>
              </div>

              <p className="text-xs sm:text-sm text-slate-600 mt-2 leading-relaxed">
                The momentum factor evaluates historical cross-sectional returns over a 252-trading-day window (~12 calendar months) while skipping the most recent 21 trading days (~1 calendar month). This intermediate momentum design adheres to the empirical framework established by Jegadeesh and Titman (1993) to avoid short-term microstructure reversals, bid-ask bounce, and liquidity shocks.
              </p>

              {/* Mathematical Formula Box */}
              <div className="my-4 p-4 rounded-xl bg-slate-900 text-white font-mono text-xs sm:text-sm shadow-inner overflow-x-auto">
                <div className="text-slate-400 text-[11px] mb-1 font-sans">
                  Raw Momentum Equation (Decision Date t):
                </div>
                <div className="text-emerald-400 font-bold">
                  Raw Momentum(t) = ( Close[t - 21] / Close[t - 252] ) - 1.0
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-600 bg-slate-50/70 p-3.5 rounded-xl border border-slate-200/60">
                <div>
                  <strong className="text-slate-800">Warmup Lookback:</strong> 252 trading sessions required before the first eligible decision date (31 Oct 2022).
                </div>
                <div>
                  <strong className="text-slate-800">Skip Window:</strong> 21 trading sessions omitted immediately prior to rebalance decision.
                </div>
              </div>
            </div>
          </div>
        </article>

        {/* 2. Risk-Adjusted Scaling */}
        <article className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-7 shadow-xs">
          <div className="flex items-start space-x-3.5">
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-navy flex items-center justify-center flex-shrink-0 font-bold border border-blue-100 text-sm">
              2
            </div>
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <h3 className="text-base sm:text-lg font-bold text-slate-900">
                  Risk-Adjusted Volatility Scaling
                </h3>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald/10 text-emerald-800 border border-emerald/20">
                  Risk Control
                </span>
              </div>

              <p className="text-xs sm:text-sm text-slate-600 mt-2 leading-relaxed">
                Raw momentum is divided by historical annualized volatility. Highly volatile equities with erratic price paths are penalized, ensuring that stocks with consistent, steady upward trends achieve higher rank scores than noisy, high-beta speculative names.
              </p>

              {/* Mathematical Formula Box */}
              <div className="my-4 p-4 rounded-xl bg-slate-900 text-white font-mono text-xs sm:text-sm shadow-inner space-y-2 overflow-x-auto">
                <div>
                  <span className="text-slate-400 text-[11px] block font-sans">
                    Annualized Volatility (252-day Rolling Std):
                  </span>
                  <span className="text-blue-300 font-bold">
                    σ_ann(t) = std( Daily_Returns[t-251 ... t], 252 ) × √252
                  </span>
                </div>
                <div className="pt-2 border-t border-slate-800">
                  <span className="text-slate-400 text-[11px] block font-sans">
                    Risk-Adjusted Momentum Score:
                  </span>
                  <span className="text-emerald-400 font-bold">
                    Score(t) = Raw Momentum(t) / σ_ann(t)
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-500">
                Data Hygiene: Tickers with non-positive, zero, or non-finite volatility are masked to NaN, preventing division by zero and false rankings.
              </p>
            </div>
          </div>
        </article>

        {/* 3. Rank-Based Weighting */}
        <article className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-7 shadow-xs">
          <div className="flex items-start space-x-3.5">
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-navy flex items-center justify-center flex-shrink-0 font-bold border border-blue-100 text-sm">
              3
            </div>
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <h3 className="text-base sm:text-lg font-bold text-slate-900">
                  Rank-Based Linear Weighting Formula
                </h3>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
                  Capital Allocation
                </span>
              </div>

              <p className="text-xs sm:text-sm text-slate-600 mt-2 leading-relaxed">
                Strategy 3 dynamically assigns capital according to momentum rank. Instead of equal weights (1/X), top-ranked positions receive linearly higher weights based on their rank order, concentrating capital into highest-conviction momentum leaders.
              </p>

              {/* Mathematical Formula Box */}
              <div className="my-4 p-4 rounded-xl bg-slate-900 text-white font-mono text-xs sm:text-sm shadow-inner overflow-x-auto">
                <div className="text-slate-400 text-[11px] mb-1 font-sans">
                  Target Weight for Position N (where N ∈ [1, X]):
                </div>
                <div className="text-amber-400 font-bold text-sm sm:text-base">
                  Weight(N) = (X + 1 - N) / [ X(X + 1) / 2 ]
                </div>
              </div>

              {/* Formula Explanation Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs bg-slate-50/70 p-4 rounded-xl border border-slate-200/60">
                <ul className="space-y-1.5 text-slate-600 list-disc list-inside">
                  <li>
                    <strong className="text-slate-800">X = {targetX}:</strong> Target number of stocks selected.
                  </li>
                  <li>
                    <strong className="text-slate-800">N ∈ [1, {targetX}]:</strong> Stock's ordinal rank (Rank 1 is highest score).
                  </li>
                  <li>
                    <strong className="text-slate-800">Denominator:</strong> Triangular number sum = { (targetX * (targetX + 1)) / 2 }.
                  </li>
                </ul>

                <ul className="space-y-1.5 text-slate-600 list-disc list-inside">
                  <li>
                    <strong className="text-slate-800">Rank 1 Allocation:</strong> {rank1WeightPct}% target weight.
                  </li>
                  <li>
                    <strong className="text-slate-800">Rank {targetX} Allocation:</strong> {rankXWeightPct}% target weight.
                  </li>
                  <li>
                    <strong className="text-slate-800">Total Sum:</strong> Exactly 100.00% across all {targetX} positions.
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </article>

        {/* 4. The 2X Retention Buffer */}
        <article className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-7 shadow-xs">
          <div className="flex items-start space-x-3.5">
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-navy flex items-center justify-center flex-shrink-0 font-bold border border-blue-100 text-sm">
              4
            </div>
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <h3 className="text-base sm:text-lg font-bold text-slate-900">
                  The 2X Rank Retention Buffer Dynamics
                </h3>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-800 border border-amber-300">
                  Turnover Mitigation
                </span>
              </div>

              <p className="text-xs sm:text-sm text-slate-600 mt-2 leading-relaxed">
                Standard momentum strategies experience severe transaction drag from boundary churn—stocks oscillating around Rank X are repeatedly sold and rebought. The 2X Retention Buffer establishes an asymmetric entry and exit boundary:
              </p>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-4 text-xs">
                <div className="bg-emerald-50/50 border border-emerald-200/80 rounded-xl p-3.5">
                  <div className="font-bold text-emerald-900 mb-1">Entry Threshold (Top X)</div>
                  <p className="text-slate-600">
                    A new stock must achieve a momentum rank of <strong>1 ≤ Rank ≤ {targetX}</strong> to enter the portfolio.
                  </p>
                </div>

                <div className="bg-amber-50/50 border border-amber-200/80 rounded-xl p-3.5">
                  <div className="font-bold text-amber-900 mb-1">Retention Zone (X to 2X)</div>
                  <p className="text-slate-600">
                    Existing holdings whose rank slips between <strong>{targetX + 1} and {2 * targetX}</strong> are held to avoid unnecessary churn.
                  </p>
                </div>

                <div className="bg-rose-50/50 border border-rose-200/80 rounded-xl p-3.5">
                  <div className="font-bold text-rose-900 mb-1">Exit Threshold (&gt; 2X)</div>
                  <p className="text-slate-600">
                    A stock is sold only when its rank drops strictly below <strong>{2 * targetX}</strong>, or when missing from rankings.
                  </p>
                </div>
              </div>

              <p className="text-xs text-slate-500">
                Portfolio Vacancy Rule: If existing retained stocks fill fewer than {targetX} positions, the highest unheld stocks from the Top {targetX} fill the vacant slots.
              </p>
            </div>
          </div>
        </article>

        {/* 5. Realistic Execution and Rebalancing */}
        <article className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-7 shadow-xs">
          <div className="flex items-start space-x-3.5">
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-navy flex items-center justify-center flex-shrink-0 font-bold border border-blue-100 text-sm">
              5
            </div>
            <div className="flex-1">
              <div className="flex items-center space-x-2">
                <h3 className="text-base sm:text-lg font-bold text-slate-900">
                  Realistic Institutional Execution & Portfolio Accounting
                </h3>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-300">
                  Execution Rules
                </span>
              </div>

              <p className="text-xs sm:text-sm text-slate-600 mt-2 leading-relaxed">
                The backtesting engine models real-world execution constraints to eliminate lookahead bias and ensure practical implementability:
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 my-4 text-xs text-slate-700">
                <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50">
                  <div className="font-bold text-slate-900 mb-1">Next-Day Open Execution</div>
                  <p className="text-slate-600">
                    Signals generated at month-end Close are executed at the next trading session's Open price (or Close fallback if Open is unobserved).
                  </p>
                </div>

                <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50">
                  <div className="font-bold text-slate-900 mb-1">Whole-Share Discretization</div>
                  <p className="text-slate-600">
                    No fractional shares allowed for Strategies 2, 3, and 4. Integer shares computed via <code>floor(Target_Capital / Price)</code>.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50">
                  <div className="font-bold text-slate-900 mb-1">Two-Phase Rebalance (Sells First)</div>
                  <p className="text-slate-600">
                    Phase 1 liquidates exits and trims overweight holdings to free cash. Phase 2 executes buy orders sorted by target weight.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl border border-slate-200 bg-slate-50/50">
                  <div className="font-bold text-slate-900 mb-1">Strict Non-Negative Cash</div>
                  <p className="text-slate-600">
                    Buys are capped at affordable whole shares with remaining cash. Cash is guaranteed non-negative at all times; uninvested cash earns 0.00%.
                  </p>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-amber-50/60 border border-amber-200/70 text-xs text-amber-900">
                <strong className="font-bold">Transaction Friction Model:</strong> 0.15% variable fee on all gross traded values (buys and sells) plus a fixed fee of ₹15.00 per stock sell order, accurately reflecting STT, brokerage, exchange fees, and GST.
              </div>
            </div>
          </div>
        </article>
      </div>

      {/* =========================================================================
          C. ACADEMIC LIMITATIONS FOOTER
          ========================================================================= */}
      <section className="bg-slate-100/90 rounded-2xl border border-slate-300/80 p-5 sm:p-6 shadow-2xs">
        <div className="flex items-start space-x-3.5">
          <div className="p-2 rounded-xl bg-slate-200 text-slate-700 flex-shrink-0 mt-0.5">
            <AlertTriangle className="w-4 h-4 text-slate-700" />
          </div>
          <div className="text-xs sm:text-sm text-slate-700 leading-relaxed">
            <h4 className="font-bold text-slate-900 mb-1">Academic Research Disclosures & Assumptions</h4>
            <p className="italic text-slate-600">
              "Limitations: This backtest is subject to survivorship bias, assumes zero interest on idle cash, does not model bid-ask slippage or market impact, and reflects a single 4-year historical period. Past performance does not guarantee future results."
            </p>
            <p className="text-[11px] text-slate-500 mt-2 font-normal">
              Universe note: Equities filtered from the historical Top 100 universe. Fixed execution costs reflect prevailing retail-brokerage tariff structures on the National Stock Exchange of India (NSE).
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
