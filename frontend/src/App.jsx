import React, { useState } from 'react';
import Header from './components/Header';
import StrategyCards from './components/StrategyCards';
import BacktestForm from './components/BacktestForm';
import OverviewTab from './components/OverviewTab';
import PerformanceTab from './components/PerformanceTab';
import ChartsTab from './components/ChartsTab';
import HoldingsTab from './components/HoldingsTab';
import MethodologyTab from './components/MethodologyTab';
import { formatINR } from './utils/format';
import {
  CheckCircle2,
  Clock,
  Calendar,
  ShieldCheck,
  TrendingUp,
  BarChart2,
  Sparkles,
  LayoutDashboard,
  Table,
  LineChart,
  Layers,
  BookOpen,
} from 'lucide-react';

const TABS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'performance', label: 'Performance', icon: Table },
  { id: 'charts', label: 'Charts', icon: LineChart },
  { id: 'holdings', label: 'Holdings', icon: Layers },
  { id: 'methodology', label: 'Methodology', icon: BookOpen },
];

export default function App() {
  const [backtestResult, setBacktestResult] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');

  const passedChecks = backtestResult?.validation
    ? backtestResult.validation.filter((c) => c.status === 'PASS').length
    : 0;
  const totalChecks = backtestResult?.validation ? backtestResult.validation.length : 0;

  return (
    <div className="min-h-screen bg-background flex flex-col selection:bg-blue-100 selection:text-navy">
      {/* 1. Institutional Header */}
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 2. Dashboard Introduction */}
        <section className="mb-8">
          <div className="bg-gradient-to-r from-blue-900 to-navy text-white rounded-2xl p-6 sm:p-8 shadow-md relative overflow-hidden">
            <div className="absolute right-0 top-0 translate-x-12 -translate-y-8 opacity-10 pointer-events-none">
              <TrendingUp className="w-80 h-80 text-white" />
            </div>

            <div className="relative z-10 max-w-3xl">
              <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-800/80 text-blue-200 text-xs font-semibold mb-3 border border-blue-600/30">
                <Sparkles className="w-3.5 h-3.5 mr-1.5 text-emerald" />
                Point-in-Time Quantitative Engine
              </div>
              <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white mb-3">
                Systematic Momentum Backtesting & Buffer Analysis
              </h2>
              <p className="text-sm sm:text-base text-blue-100/90 leading-relaxed font-normal">
                Evaluate cross-sectional 12-1 month risk-adjusted momentum strategies on the NSE Top 100 universe from October 2022 to October 2026. This platform models whole-share portfolio execution, 2X rank retention buffer dynamics, and realistic institutional friction costs.
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-5 border-t border-blue-800/60">
                <div>
                  <div className="text-xs text-blue-300 font-medium">Universe</div>
                  <div className="text-sm font-bold text-white mt-0.5">NSE 100 Equities</div>
                </div>
                <div>
                  <div className="text-xs text-blue-300 font-medium">Rebalances</div>
                  <div className="text-sm font-bold text-white mt-0.5">48 Monthly Cycles</div>
                </div>
                <div>
                  <div className="text-xs text-blue-300 font-medium">Friction Model</div>
                  <div className="text-sm font-bold text-white mt-0.5">0.15% + ₹15/Sell</div>
                </div>
                <div>
                  <div className="text-xs text-blue-300 font-medium">Risk-Free Rate</div>
                  <div className="text-sm font-bold text-white mt-0.5">6.50% Annualized</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* 3. Strategy Definitions Cards */}
        <StrategyCards />

        {/* 4. Dynamic Parameter Backtest Form */}
        <BacktestForm onResult={setBacktestResult} />

        {/* 5. Results Section (Only once backtestResult exists) */}
        {backtestResult ? (
          <section className="space-y-6 mt-10">
            {/* Quick Run Confirmation Banner */}
            <div className="bg-white rounded-2xl border border-emerald/30 shadow-md p-6 sm:p-7 animate-fadeIn transition-all">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">
                <div className="flex items-start space-x-3.5">
                  <div className="p-2.5 bg-emerald/10 text-emerald rounded-xl flex-shrink-0">
                    <CheckCircle2 className="w-6 h-6 text-emerald" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <h3 className="text-base sm:text-lg font-bold text-slate-900">
                        Simulation Completed Successfully
                      </h3>
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald/10 text-emerald-800 border border-emerald/20">
                        Status: Ready
                      </span>
                    </div>
                    <p className="text-xs sm:text-sm text-slate-600 mt-1">
                      Completed 4-strategy simulation run with{' '}
                      <strong>{formatINR(backtestResult.meta?.capital)}</strong> capital across Top{' '}
                      <strong>{backtestResult.meta?.x}</strong> stocks in{' '}
                      <strong>{backtestResult.meta?.runtime_seconds}s</strong>.
                    </p>
                  </div>
                </div>

                {/* Simulation Summary Badges */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
                  <div className="bg-slate-50 border border-slate-200/80 rounded-lg px-3 py-2">
                    <div className="flex items-center text-slate-400 font-medium">
                      <Calendar className="w-3.5 h-3.5 mr-1" />
                      Trading Days
                    </div>
                    <div className="font-bold text-slate-800 mt-0.5">
                      {backtestResult.meta?.trading_days} Sessions
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200/80 rounded-lg px-3 py-2">
                    <div className="flex items-center text-slate-400 font-medium">
                      <Clock className="w-3.5 h-3.5 mr-1" />
                      Rebalances
                    </div>
                    <div className="font-bold text-slate-800 mt-0.5">
                      {backtestResult.meta?.rebalances} Cycles
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200/80 rounded-lg px-3 py-2 col-span-2 sm:col-span-1">
                    <div className="flex items-center text-slate-400 font-medium">
                      <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald" />
                      Validation Suite
                    </div>
                    <div className="font-bold text-emerald-700 mt-0.5">
                      {passedChecks}/{totalChecks} Passed
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Responsive Tab Navigation Bar */}
            <div className="border-b border-slate-200">
              <nav
                className="flex space-x-2 sm:space-x-4 overflow-x-auto pb-px"
                aria-label="Backtest Analysis Tabs"
                role="tablist"
              >
                {TABS.map((tab) => {
                  const Icon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      id={`tab-${tab.id}`}
                      role="tab"
                      aria-selected={isActive}
                      aria-controls={`tabpanel-${tab.id}`}
                      onClick={() => setActiveTab(tab.id)}
                      className={`inline-flex items-center px-4 py-3 text-sm font-semibold rounded-t-xl border-b-2 transition-all whitespace-nowrap focus:outline-none focus:ring-2 focus:ring-navy focus:ring-offset-1 cursor-pointer select-none ${
                        isActive
                          ? 'border-navy text-navy bg-white shadow-2xs font-bold'
                          : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                      }`}
                    >
                      <Icon
                        className={`w-4 h-4 mr-2 ${
                          isActive ? 'text-navy stroke-[2.2]' : 'text-slate-400'
                        }`}
                      />
                      {tab.label}
                    </button>
                  );
                })}
              </nav>
            </div>

            {/* Active Tab Panel */}
            <div
              id={`tabpanel-${activeTab}`}
              role="tabpanel"
              aria-labelledby={`tab-${activeTab}`}
              className="mt-6"
            >
              {activeTab === 'overview' && <OverviewTab result={backtestResult} />}
              {activeTab === 'performance' && <PerformanceTab result={backtestResult} />}
              {activeTab === 'charts' && <ChartsTab result={backtestResult} />}
              {activeTab === 'holdings' && <HoldingsTab result={backtestResult} />}
              {activeTab === 'methodology' && <MethodologyTab result={backtestResult} />}
            </div>
          </section>
        ) : (
          /* Empty Initial State Banner */
          <section className="bg-slate-50 border border-slate-200/80 rounded-2xl p-8 text-center text-slate-500 my-8">
            <BarChart2 className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-700">
              Run a backtest simulation above to view results.
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Configure initial capital and top-X parameter, then execute to unlock the Overview, Performance, and Analytics tabs.
            </p>
          </section>
        )}
      </main>

      {/* 6. Clean Institutional Footer */}
      <footer className="border-t border-slate-200 bg-white py-6 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500 gap-3">
          <p>© 2026 Quantitative Momentum Strategy Engine. Indian Equities Backtest System.</p>
          <p className="text-slate-400">
            For quantitative research & academic portfolio analysis only. Non-custodial research platform.
          </p>
        </div>
      </footer>
    </div>
  );
}
