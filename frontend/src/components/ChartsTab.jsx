import React, { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
  ReferenceLine,
} from 'recharts';
import {
  TrendingUp,
  Activity,
  ArrowDownRight,
  Repeat,
  Info,
  Calendar,
  Layers,
  Award,
} from 'lucide-react';
import {
  formatINR,
  formatPercent,
  formatRatio,
  formatUnsignedPercent,
  formatCompactINR,
  formatMonthYear,
  formatDate,
} from '../utils/format';
import {
  computeDailyDrawdowns,
  computeStrategy3MonthlyPnL,
  findBestMetricValue,
  isBestValue,
} from '../utils/metrics';

// Palette mapping
const STRATEGY_CONFIG = {
  s1: { id: 1, key: 's1', color: '#2563eb', fallbackName: 'Strategy 1 - Top-X Buy-and-Hold' },
  s2: { id: 2, key: 's2', color: '#10b981', fallbackName: 'Strategy 2 - Top-X Equal-Weight Momentum (Buffer)' },
  s3: { id: 3, key: 's3', color: '#8b5cf6', fallbackName: 'Strategy 3 - Top-X Rank-Weighted Momentum' },
  s4: { id: 4, key: 's4', color: '#64748b', fallbackName: 'Strategy 4 - NIFTYBEES Benchmark Buy-and-Hold' },
};

function ChartCard({ title, subtitle, icon: Icon, children }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 sm:p-6 flex flex-col justify-between">
      <div className="mb-4">
        <div className="flex items-center space-x-2">
          {Icon && <Icon className="w-4 h-4 text-navy" />}
          <h4 className="text-base font-bold text-slate-900">{title}</h4>
        </div>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex-1 w-full">{children}</div>
    </div>
  );
}

function EmptyChartCard({ title, reason }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center my-4 shadow-sm">
      <Info className="w-8 h-8 text-slate-400 mx-auto mb-2" />
      <h4 className="text-base font-bold text-slate-800">No chart data available</h4>
      <p className="text-xs sm:text-sm text-slate-500 mt-1">
        {reason || 'The required dataset was not returned by the backtest engine.'}
      </p>
    </div>
  );
}

export default function ChartsTab({ result }) {
  // Toggle state for multi-series charts
  const [visibleSeries, setVisibleSeries] = useState({
    s1: true,
    s2: true,
    s3: true,
    s4: true,
  });

  const toggleSeries = (dataKey) => {
    // Strip _equity or _dd suffix to get series key s1, s2, etc.
    const key = dataKey.replace('_equity', '').replace('_dd', '');
    setVisibleSeries((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  // Map strategy names dynamically from backend metadata
  const strategyNames = useMemo(() => {
    const names = {
      s1: STRATEGY_CONFIG.s1.fallbackName,
      s2: STRATEGY_CONFIG.s2.fallbackName,
      s3: STRATEGY_CONFIG.s3.fallbackName,
      s4: STRATEGY_CONFIG.s4.fallbackName,
    };
    if (Array.isArray(result?.strategies)) {
      for (const s of result.strategies) {
        if (s.id && names[`s${s.id}`]) {
          names[`s${s.id}`] = s.name;
        }
      }
    }
    return names;
  }, [result]);

  // Strategy 3 name
  const s3Title = strategyNames.s3 || 'Strategy 3';

  // Datasets
  const dailyEquity = useMemo(() => {
    return Array.isArray(result?.daily_equity) ? result.daily_equity : [];
  }, [result]);

  const dailyDrawdowns = useMemo(() => {
    return computeDailyDrawdowns(dailyEquity);
  }, [dailyEquity]);

  const monthlyPnL = useMemo(() => {
    return computeStrategy3MonthlyPnL(result?.monthly);
  }, [result]);

  const performance = useMemo(() => {
    return Array.isArray(result?.performance) ? result.performance : [];
  }, [result]);

  // Overall check for empty state
  if (!result || (dailyEquity.length === 0 && performance.length === 0)) {
    return (
      <EmptyChartCard
        title="Charts"
        reason="Run a simulation above to view interactive equity curves, drawdowns, and comparative metric distributions."
      />
    );
  }

  // 1. Equity Curves Custom Tooltip
  const renderEquityTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white/95 backdrop-blur-xs border border-slate-200 rounded-xl p-3 shadow-lg text-xs z-50">
          <div className="font-bold text-slate-900 border-b border-slate-100 pb-1.5 mb-2">
            {formatDate(label)}
          </div>
          <div className="space-y-1.5">
            {payload.map((entry) => (
              <div key={entry.dataKey} className="flex items-center justify-between gap-4">
                <div className="flex items-center space-x-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: entry.color }}
                  />
                  <span className="text-slate-600 font-medium">{entry.name}</span>
                </div>
                <span className="font-bold text-slate-900 font-mono">
                  {formatINR(entry.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      );
    }
    return null;
  };

  // 2. Drawdown Curves Custom Tooltip
  const renderDrawdownTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white/95 backdrop-blur-xs border border-slate-200 rounded-xl p-3 shadow-lg text-xs z-50">
          <div className="font-bold text-slate-900 border-b border-slate-100 pb-1.5 mb-2">
            {formatDate(label)}
          </div>
          <div className="space-y-1.5">
            {payload.map((entry) => (
              <div key={entry.dataKey} className="flex items-center justify-between gap-4">
                <div className="flex items-center space-x-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: entry.color }}
                  />
                  <span className="text-slate-600 font-medium">{entry.name}</span>
                </div>
                <span className="font-bold text-rose-600 font-mono">
                  {entry.value !== undefined ? `${Number(entry.value).toFixed(2)}%` : '—'}
                </span>
              </div>
            ))}
          </div>
        </div>
      );
    }
    return null;
  };

  // 3. Strategy 3 Monthly P&L Tooltip
  const renderMonthlyPnLTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const isPos = data.pnl >= 0;
      return (
        <div className="bg-white/95 backdrop-blur-xs border border-slate-200 rounded-xl p-3.5 shadow-lg text-xs z-50">
          <div className="font-bold text-slate-900 border-b border-slate-100 pb-1 mb-2">
            {formatDate(data.date)} ({data.month})
          </div>
          <div className="space-y-1">
            <div className="flex justify-between gap-4">
              <span className="text-slate-500">Monthly P&L:</span>
              <span className={`font-bold font-mono ${isPos ? 'text-emerald-700' : 'text-rose-600'}`}>
                {isPos ? '+' : ''}{formatINR(data.pnl)}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-slate-500">Monthly Return:</span>
              <span className={`font-bold font-mono ${isPos ? 'text-emerald-700' : 'text-rose-600'}`}>
                {formatPercent(data.returnPct)}
              </span>
            </div>
            <div className="flex justify-between gap-4 pt-1 border-t border-slate-100 text-slate-400">
              <span>Ending Balance:</span>
              <span className="font-semibold text-slate-700 font-mono">
                {formatINR(data.endingEquity)}
              </span>
            </div>
          </div>
        </div>
      );
    }
    return null;
  };

  // Find best values for comparison charts
  const bestSharpeVal = findBestMetricValue(performance, 'Sharpe_Ratio', 'max');
  const bestMaxDDVal = findBestMetricValue(performance, 'Max_Drawdown_%', 'absMin');

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* =========================================================================
          CHART 1: MULTI-SERIES DAILY EQUITY CURVES (Full Width)
          ========================================================================= */}
      {dailyEquity.length > 0 ? (
        <ChartCard
          title="Daily Portfolio Equity Trajectories"
          subtitle="Cumulative growth of INR capital across all 4 quantitative models (Click legend items to toggle series)."
          icon={TrendingUp}
        >
          <div className="h-[380px] w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={dailyEquity}
                margin={{ top: 15, right: 25, left: 20, bottom: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatMonthYear}
                  minTickGap={45}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={{ stroke: '#cbd5e1' }}
                />
                <YAxis
                  tickFormatter={formatCompactINR}
                  domain={['auto', 'auto']}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={{ stroke: '#cbd5e1' }}
                />
                <Tooltip content={renderEquityTooltip} />
                <Legend
                  onClick={(e) => toggleSeries(e.dataKey)}
                  wrapperStyle={{ paddingTop: '10px', fontSize: '12px', cursor: 'pointer' }}
                />

                <Line
                  type="monotone"
                  dataKey="s1_equity"
                  name={strategyNames.s1}
                  stroke={STRATEGY_CONFIG.s1.color}
                  strokeWidth={2}
                  dot={false}
                  hide={!visibleSeries.s1}
                  connectNulls={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="s2_equity"
                  name={strategyNames.s2}
                  stroke={STRATEGY_CONFIG.s2.color}
                  strokeWidth={2.5}
                  dot={false}
                  hide={!visibleSeries.s2}
                  connectNulls={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="s3_equity"
                  name={strategyNames.s3}
                  stroke={STRATEGY_CONFIG.s3.color}
                  strokeWidth={2}
                  dot={false}
                  hide={!visibleSeries.s3}
                  connectNulls={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="s4_equity"
                  name={strategyNames.s4}
                  stroke={STRATEGY_CONFIG.s4.color}
                  strokeWidth={1.8}
                  strokeDasharray="4 4"
                  dot={false}
                  hide={!visibleSeries.s4}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      ) : (
        <EmptyChartCard title="Daily Equity Curves" reason="Daily portfolio equity records are not available." />
      )}

      {/* =========================================================================
          CHART 2: MULTI-SERIES DAILY DRAWDOWN UNDERWATER PROFILES (Full Width)
          ========================================================================= */}
      {dailyDrawdowns.length > 0 ? (
        <ChartCard
          title="Daily Drawdown Underwater Profiles (%)"
          subtitle="Chronological peak-to-trough equity percentage decline (0% = new all-time equity peak)."
          icon={ArrowDownRight}
        >
          <div className="h-[340px] w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={dailyDrawdowns}
                margin={{ top: 15, right: 25, left: 20, bottom: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatMonthYear}
                  minTickGap={45}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={{ stroke: '#cbd5e1' }}
                />
                <YAxis
                  tickFormatter={(val) => `${Number(val).toFixed(0)}%`}
                  domain={['auto', 0]}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickLine={false}
                  axisLine={{ stroke: '#cbd5e1' }}
                />
                <ReferenceLine y={0} stroke="#94a3b8" strokeWidth={1} />
                <Tooltip content={renderDrawdownTooltip} />
                <Legend
                  onClick={(e) => toggleSeries(e.dataKey)}
                  wrapperStyle={{ paddingTop: '10px', fontSize: '12px', cursor: 'pointer' }}
                />

                <Area
                  type="monotone"
                  dataKey="s1_dd"
                  name={strategyNames.s1}
                  stroke={STRATEGY_CONFIG.s1.color}
                  fill="rgba(37, 99, 235, 0.08)"
                  strokeWidth={1.5}
                  hide={!visibleSeries.s1}
                  connectNulls={false}
                  isAnimationActive={false}
                />
                <Area
                  type="monotone"
                  dataKey="s2_dd"
                  name={strategyNames.s2}
                  stroke={STRATEGY_CONFIG.s2.color}
                  fill="rgba(16, 185, 129, 0.12)"
                  strokeWidth={2}
                  hide={!visibleSeries.s2}
                  connectNulls={false}
                  isAnimationActive={false}
                />
                <Area
                  type="monotone"
                  dataKey="s3_dd"
                  name={strategyNames.s3}
                  stroke={STRATEGY_CONFIG.s3.color}
                  fill="rgba(139, 92, 246, 0.08)"
                  strokeWidth={1.5}
                  hide={!visibleSeries.s3}
                  connectNulls={false}
                  isAnimationActive={false}
                />
                <Area
                  type="monotone"
                  dataKey="s4_dd"
                  name={strategyNames.s4}
                  stroke={STRATEGY_CONFIG.s4.color}
                  fill="rgba(100, 116, 139, 0.06)"
                  strokeWidth={1.2}
                  strokeDasharray="3 3"
                  hide={!visibleSeries.s4}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>
      ) : (
        <EmptyChartCard title="Daily Drawdowns" reason="Daily drawdown data cannot be computed." />
      )}

      {/* =========================================================================
          2-COLUMN GRID FOR COMPARATIVE STRATEGY METRICS
          ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CHART 3: STRATEGY 3 MONTHLY P&L BARS */}
        {monthlyPnL.length > 0 ? (
          <ChartCard
            title={`${s3Title} Monthly P&L`}
            subtitle="Completed monthly rupee profit/loss bars (Green = gain, Red = loss)."
            icon={Calendar}
          >
            <div className="h-[300px] w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={monthlyPnL}
                  margin={{ top: 10, right: 15, left: 15, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={formatMonthYear}
                    minTickGap={30}
                    tick={{ fontSize: 10, fill: '#64748b' }}
                    tickLine={false}
                    axisLine={{ stroke: '#cbd5e1' }}
                  />
                  <YAxis
                    tickFormatter={formatCompactINR}
                    tick={{ fontSize: 10, fill: '#64748b' }}
                    tickLine={false}
                    axisLine={{ stroke: '#cbd5e1' }}
                  />
                  <ReferenceLine y={0} stroke="#cbd5e1" />
                  <Tooltip content={renderMonthlyPnLTooltip} />
                  <Bar dataKey="pnl" name="Monthly P&L (INR)" isAnimationActive={false}>
                    {monthlyPnL.map((entry) => (
                      <Cell
                        key={entry.date}
                        fill={entry.pnl >= 0 ? '#10b981' : '#ef4444'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        ) : (
          <EmptyChartCard title="Strategy 3 Monthly P&L" reason="Monthly returns dataset is unavailable." />
        )}

        {/* CHART 4: AVERAGE NAME TURNOVER COMPARISON */}
        {performance.length > 0 ? (
          <ChartCard
            title="Average Name Turnover Comparison (%)"
            subtitle="Percentage of stock holdings replaced at each monthly rebalance cycle (lower = less portfolio churn)."
            icon={Repeat}
          >
            <div className="h-[300px] w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={performance}
                  layout="vertical"
                  margin={{ top: 10, right: 25, left: 80, bottom: 10 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                  <XAxis
                    type="number"
                    tickFormatter={(val) => `${Number(val).toFixed(0)}%`}
                    tick={{ fontSize: 10, fill: '#64748b' }}
                    tickLine={false}
                    axisLine={{ stroke: '#cbd5e1' }}
                  />
                  <YAxis
                    type="category"
                    dataKey="Strategy"
                    tickFormatter={(strat) => {
                      if (strat.includes('Strategy 1')) return 'Strategy 1';
                      if (strat.includes('Strategy 2')) return 'Strategy 2 (Buffer)';
                      if (strat.includes('Strategy 3')) return 'Strategy 3';
                      if (strat.includes('Strategy 4')) return 'Benchmark';
                      return strat.slice(0, 15);
                    }}
                    tick={{ fontSize: 11, fill: '#334155' }}
                    tickLine={false}
                    axisLine={{ stroke: '#cbd5e1' }}
                  />
                  <Tooltip
                    formatter={(val, name, item) => [
                      formatUnsignedPercent(val),
                      `${item.payload.Strategy} Turnover`,
                    ]}
                    contentStyle={{ borderRadius: '0.75rem', fontSize: '12px', border: '1px solid #e2e8f0' }}
                  />
                  <Bar
                    dataKey="Avg_Name_Turnover_%"
                    name="Name Turnover %"
                    fill="#3b82f6"
                    radius={[0, 4, 4, 0]}
                    isAnimationActive={false}
                  >
                    {performance.map((entry, idx) => {
                      // Strategy 2 with buffer typically achieves the lowest turnover
                      const isLowest = entry['Avg_Name_Turnover_%'] === Math.min(
                        ...performance.map((p) => p['Avg_Name_Turnover_%'])
                      );
                      return (
                        <Cell
                          key={entry.Strategy || idx}
                          fill={isLowest ? '#10b981' : '#1e3a8a'}
                        />
                      );
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        ) : (
          <EmptyChartCard title="Turnover Comparison" reason="No turnover data available." />
        )}

        {/* CHART 5: SHARPE RATIO COMPARISON */}
        {performance.length > 0 ? (
          <ChartCard
            title="Annualized Sharpe Ratio Comparison"
            subtitle="Risk-adjusted return above 6.50% annual risk-free rate (Emerald indicates highest efficiency)."
            icon={Activity}
          >
            <div className="h-[300px] w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={performance}
                  margin={{ top: 15, right: 20, left: 10, bottom: 25 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey="Strategy"
                    tickFormatter={(strat) => {
                      if (strat.includes('Strategy 1')) return 'S1 (Hold)';
                      if (strat.includes('Strategy 2')) return 'S2 (Buffer)';
                      if (strat.includes('Strategy 3')) return 'S3 (Rank)';
                      if (strat.includes('Strategy 4')) return 'S4 (Bench)';
                      return strat.slice(0, 10);
                    }}
                    tick={{ fontSize: 11, fill: '#334155' }}
                    tickLine={false}
                    axisLine={{ stroke: '#cbd5e1' }}
                  />
                  <YAxis
                    domain={[0, 'auto']}
                    tickFormatter={(val) => Number(val).toFixed(2)}
                    tick={{ fontSize: 10, fill: '#64748b' }}
                    tickLine={false}
                    axisLine={{ stroke: '#cbd5e1' }}
                  />
                  <Tooltip
                    formatter={(val, name, item) => [
                      formatRatio(val, 2),
                      `${item.payload.Strategy} Sharpe`,
                    ]}
                    contentStyle={{ borderRadius: '0.75rem', fontSize: '12px', border: '1px solid #e2e8f0' }}
                  />
                  <Bar
                    dataKey="Sharpe_Ratio"
                    name="Sharpe Ratio"
                    radius={[4, 4, 0, 0]}
                    isAnimationActive={false}
                  >
                    {performance.map((entry, idx) => {
                      const isBest = isBestValue(entry.Sharpe_Ratio, bestSharpeVal, 'max');
                      return (
                        <Cell
                          key={entry.Strategy || idx}
                          fill={isBest ? '#10b981' : '#1e3a8a'}
                        />
                      );
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        ) : (
          <EmptyChartCard title="Sharpe Ratio Comparison" reason="No performance summary records found." />
        )}

        {/* CHART 6: MAXIMUM DRAWDOWN COMPARISON */}
        {performance.length > 0 ? (
          <ChartCard
            title="Maximum Drawdown Comparison (%)"
            subtitle="Largest peak-to-trough capital decline (Emerald indicates smallest drawdown magnitude)."
            icon={ArrowDownRight}
          >
            <div className="h-[300px] w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={performance}
                  margin={{ top: 15, right: 20, left: 10, bottom: 25 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis
                    dataKey="Strategy"
                    tickFormatter={(strat) => {
                      if (strat.includes('Strategy 1')) return 'S1 (Hold)';
                      if (strat.includes('Strategy 2')) return 'S2 (Buffer)';
                      if (strat.includes('Strategy 3')) return 'S3 (Rank)';
                      if (strat.includes('Strategy 4')) return 'S4 (Bench)';
                      return strat.slice(0, 10);
                    }}
                    tick={{ fontSize: 11, fill: '#334155' }}
                    tickLine={false}
                    axisLine={{ stroke: '#cbd5e1' }}
                  />
                  <YAxis
                    domain={['auto', 0]}
                    tickFormatter={(val) => `${Number(val).toFixed(0)}%`}
                    tick={{ fontSize: 10, fill: '#64748b' }}
                    tickLine={false}
                    axisLine={{ stroke: '#cbd5e1' }}
                  />
                  <ReferenceLine y={0} stroke="#94a3b8" />
                  <Tooltip
                    formatter={(val, name, item) => [
                      `${Number(val).toFixed(2)}%`,
                      `${item.payload.Strategy} Max Drawdown`,
                    ]}
                    contentStyle={{ borderRadius: '0.75rem', fontSize: '12px', border: '1px solid #e2e8f0' }}
                  />
                  <Bar
                    dataKey="Max_Drawdown_%"
                    name="Max Drawdown %"
                    radius={[0, 0, 4, 4]}
                    isAnimationActive={false}
                  >
                    {performance.map((entry, idx) => {
                      const isBest = isBestValue(entry['Max_Drawdown_%'], bestMaxDDVal, 'absMin');
                      return (
                        <Cell
                          key={entry.Strategy || idx}
                          fill={isBest ? '#10b981' : '#ef4444'}
                        />
                      );
                    })}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        ) : (
          <EmptyChartCard title="Max Drawdown Comparison" reason="No drawdown data available." />
        )}
      </div>
    </div>
  );
}
