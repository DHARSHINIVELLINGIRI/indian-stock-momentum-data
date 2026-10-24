import React from 'react';
import {
  TrendingUp,
  Activity,
  ArrowDownRight,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Sparkles,
  Info,
  Award,
} from 'lucide-react';
import { formatINR, formatPercent, formatRatio } from '../utils/format';
import { findWinningStrategy, generateKeyObservations } from '../utils/metrics';

export default function OverviewTab({ result }) {
  if (!result || !Array.isArray(result.performance) || result.performance.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center my-6">
        <Info className="w-8 h-8 text-slate-400 mx-auto mb-2" />
        <h3 className="text-base font-semibold text-slate-800">No Overview Data Available</h3>
        <p className="text-sm text-slate-500 mt-1">
          Run a simulation to generate performance analytics and validation results.
        </p>
      </div>
    );
  }

  const performance = result.performance;
  const validation = Array.isArray(result.validation) ? result.validation : [];

  // Calculate Winners Dynamically
  const bestCAGR = findWinningStrategy(performance, 'CAGR_%', 'max');
  const bestSharpe = findWinningStrategy(performance, 'Sharpe_Ratio', 'max');
  const lowestDrawdown = findWinningStrategy(performance, 'Max_Drawdown_%', 'absMin');
  const lowestCost = findWinningStrategy(performance, 'Total_Transaction_Costs_INR', 'min');

  // Validation summary
  const passedCount = validation.filter((v) => v.status === 'PASS').length;
  const totalCount = validation.length;
  const allSevenPassed = totalCount === 7 && passedCount === 7;

  // Key Observations
  const observations = generateKeyObservations(performance);

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* =========================================================================
          A. KPI CARDS (4 Prominent Cards)
          ========================================================================= */}
      <section>
        <div className="mb-4">
          <h3 className="text-lg font-bold text-slate-900">Executive Performance Highlights</h3>
          <p className="text-xs sm:text-sm text-slate-500">
            Top performing momentum models across compound return, risk-adjusted efficiency, drawdown control, and execution cost.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
          {/* 1. Best CAGR */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-2">
              <span className="flex items-center">
                <TrendingUp className="w-4 h-4 mr-1 text-emerald" />
                Best CAGR
              </span>
              <Award className="w-4 h-4 text-emerald" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-emerald tracking-tight">
              {bestCAGR ? formatPercent(bestCAGR.value) : '—'}
            </div>
            <div className="text-xs font-medium text-slate-700 mt-2 truncate" title={bestCAGR?.strategy}>
              {bestCAGR?.strategy || '—'}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Annualized compound growth
            </div>
          </div>

          {/* 2. Best Sharpe Ratio */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-2">
              <span className="flex items-center">
                <Activity className="w-4 h-4 mr-1 text-blue-600" />
                Best Sharpe Ratio
              </span>
              <Award className="w-4 h-4 text-blue-600" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {bestSharpe ? formatRatio(bestSharpe.value) : '—'}
            </div>
            <div className="text-xs font-medium text-slate-700 mt-2 truncate" title={bestSharpe?.strategy}>
              {bestSharpe?.strategy || '—'}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Risk-free hurdle: 6.50% p.a.
            </div>
          </div>

          {/* 3. Lowest Maximum Drawdown */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-2">
              <span className="flex items-center">
                <ArrowDownRight className="w-4 h-4 mr-1 text-emerald" />
                Lowest Max Drawdown
              </span>
              <Award className="w-4 h-4 text-emerald" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-emerald tracking-tight">
              {lowestDrawdown ? `${lowestDrawdown.value.toFixed(2)}%` : '—'}
            </div>
            <div className="text-xs font-medium text-slate-700 mt-2 truncate" title={lowestDrawdown?.strategy}>
              {lowestDrawdown?.strategy || '—'}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Peak-to-trough capital decline
            </div>
          </div>

          {/* 4. Lowest Total Transaction Cost */}
          <div className="bg-white rounded-xl border border-slate-200/90 p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden">
            <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-2">
              <span className="flex items-center">
                <ShieldCheck className="w-4 h-4 mr-1 text-indigo-600" />
                Lowest Transaction Cost
              </span>
              <Award className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {lowestCost ? formatINR(lowestCost.value) : '—'}
            </div>
            <div className="text-xs font-medium text-slate-700 mt-2 truncate" title={lowestCost?.strategy}>
              {lowestCost?.strategy || '—'}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              0.15% fee + ₹15/sell order
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          B. VALIDATION SUITE (Programmatic Checklist)
          ========================================================================= */}
      <section className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-7 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-5 mb-5 border-b border-slate-100 gap-3">
          <div>
            <h3 className="text-lg font-bold text-slate-900 flex items-center">
              <ShieldCheck className="w-5 h-5 mr-2 text-navy" />
              Programmatic Accounting & Integrity Suite
            </h3>
            <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
              Every simulation pass is rigorously verified by 7 mathematical integrity checks before results are rendered.
            </p>
          </div>

          {/* Prominent Verification Banner */}
          {allSevenPassed ? (
            <div className="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-bold bg-emerald-50 text-emerald-800 border border-emerald-300 shadow-sm">
              <CheckCircle2 className="w-4 h-4 mr-1.5 text-emerald" />
              All 7 Programmatic Checks Passed
            </div>
          ) : (
            <div className={`inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-bold border shadow-sm ${
              passedCount === totalCount
                ? 'bg-blue-50 text-blue-800 border-blue-200'
                : 'bg-rose-50 text-rose-800 border-rose-300'
            }`}>
              <AlertTriangle className="w-4 h-4 mr-1.5 text-rose" />
              {passedCount} of {totalCount} Programmatic Checks Passed
            </div>
          )}
        </div>

        {/* Validation Checks Checklist */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {validation.map((item) => {
            const isPass = item.status === 'PASS';
            return (
              <div
                key={item.id || item.name}
                className={`p-3.5 rounded-xl border flex items-start space-x-3 transition-colors ${
                  isPass
                    ? 'bg-slate-50/70 border-slate-200/80 hover:bg-slate-50'
                    : 'bg-rose-50/60 border-rose-200 hover:bg-rose-50'
                }`}
              >
                {isPass ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald flex-shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-5 h-5 text-rose flex-shrink-0 mt-0.5" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs sm:text-sm font-semibold text-slate-900 truncate">
                      {item.name}
                    </span>
                    <span
                      className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                        isPass
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {item.status || 'UNKNOWN'}
                    </span>
                  </div>
                  {item.message && (
                    <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                      {item.message}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* =========================================================================
          C. KEY OBSERVATIONS (Dynamically Derived from Performance)
          ========================================================================= */}
      {observations.length > 0 && (
        <section className="bg-slate-50 rounded-2xl border border-slate-200/90 p-6 sm:p-7">
          <div className="flex items-center space-x-2.5 mb-4">
            <div className="p-2 bg-blue-100/80 text-navy rounded-lg">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Key Observations</h3>
              <p className="text-xs text-slate-500">
                Empirical comparative findings derived automatically from simulated portfolio trajectories.
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {observations.map((obs, idx) => (
              <div
                key={idx}
                className="bg-white rounded-xl border border-slate-200/70 p-4 text-xs sm:text-sm text-slate-700 leading-relaxed shadow-xs flex items-start space-x-3"
              >
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-100 text-slate-600 font-bold text-xs flex-shrink-0 mt-0.5">
                  {idx + 1}
                </span>
                <p className="flex-1">{obs}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* =========================================================================
          D. ACADEMIC LIMITATIONS FOOTER
          ========================================================================= */}
      <div className="text-center pt-2 pb-4">
        <p className="text-xs text-slate-400 italic">
          Limitations: Survivorship bias, zero interest on idle cash, no slippage, single 4-year historical period.
        </p>
      </div>
    </div>
  );
}
