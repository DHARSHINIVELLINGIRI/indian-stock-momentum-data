import React, { useState, useMemo } from 'react';
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Info,
  Award,
  RotateCcw,
} from 'lucide-react';
import {
  formatINR,
  formatPercent,
  formatRatio,
  formatUnsignedPercent,
} from '../utils/format';
import {
  findBestMetricValue,
  isBestValue,
  sortPerformanceRows,
} from '../utils/metrics';

const COLUMNS = [
  {
    key: 'Strategy',
    label: 'Strategy',
    align: 'left',
    numeric: false,
    tooltip: 'The backtesting strategy identifier or model name.',
    render: (row) => (
      <div className="font-semibold text-slate-900 max-w-[240px] truncate" title={row.Strategy}>
        {row.Strategy}
      </div>
    ),
  },
  {
    key: 'Final_Value',
    label: 'Final Equity',
    align: 'right',
    numeric: true,
    direction: 'max',
    tooltip: 'Terminal portfolio value in INR at the conclusion of the 4-year backtest.',
    render: (row) => formatINR(row.Final_Value),
  },
  {
    key: 'Total_Return_%',
    label: 'Total Return %',
    align: 'right',
    numeric: true,
    direction: 'max',
    tooltip: 'Cumulative percentage change in total portfolio equity over the full simulation.',
    render: (row) => formatPercent(row['Total_Return_%']),
  },
  {
    key: 'CAGR_%',
    label: 'CAGR %',
    align: 'right',
    numeric: true,
    direction: 'max',
    tooltip: 'Compound Annual Growth Rate calculated from exact elapsed calendar days.',
    render: (row) => formatPercent(row['CAGR_%']),
  },
  {
    key: 'Volatility_%',
    label: 'Volatility %',
    align: 'right',
    numeric: true,
    direction: 'min',
    tooltip: 'Annualized standard deviation of daily portfolio returns (252 trading days).',
    render: (row) => formatUnsignedPercent(row['Volatility_%']),
  },
  {
    key: 'Sharpe_Ratio',
    label: 'Sharpe (Rf=6.5%)',
    align: 'right',
    numeric: true,
    direction: 'max',
    tooltip: 'Annualized risk-adjusted excess return over 6.50% annual risk-free rate.',
    render: (row) => formatRatio(row.Sharpe_Ratio, 2),
  },
  {
    key: 'Sortino_Ratio',
    label: 'Sortino',
    align: 'right',
    numeric: true,
    direction: 'max',
    tooltip: 'Annualized excess return per unit of downside deviation below risk-free rate.',
    render: (row) => formatRatio(row.Sortino_Ratio, 2),
  },
  {
    key: 'Max_Drawdown_%',
    label: 'Max Drawdown %',
    align: 'right',
    numeric: true,
    direction: 'absMin',
    tooltip: 'Largest peak-to-trough decline in total portfolio equity (lowest magnitude is best).',
    render: (row) => formatPercent(row['Max_Drawdown_%']),
  },
  {
    key: 'Win_Rate_%',
    label: 'Win Rate',
    align: 'right',
    numeric: true,
    direction: 'max',
    tooltip: 'Percentage of completed FIFO round-trip sell trades yielding positive net P&L after fees (null for buy-and-hold).',
    render: (row) => formatUnsignedPercent(row['Win_Rate_%']),
  },
  {
    key: 'Avg_Name_Turnover_%',
    label: 'Avg Turnover %',
    align: 'right',
    numeric: true,
    direction: 'min',
    tooltip: 'Average percentage of portfolio constituent names replaced at each monthly rebalance cycle.',
    render: (row) => formatUnsignedPercent(row['Avg_Name_Turnover_%']),
  },
  {
    key: 'Total_Transaction_Costs_INR',
    label: 'Total Costs',
    align: 'right',
    numeric: true,
    direction: 'min',
    tooltip: 'Cumulative friction fees: 0.15% variable fee on trade volume + ₹15 fixed fee per sell order.',
    render: (row) => formatINR(row.Total_Transaction_Costs_INR),
  },
];

export default function PerformanceTab({ result }) {
  const [sortKey, setSortKey] = useState(null);
  const [sortDirection, setSortDirection] = useState('desc');

  const performance = useMemo(() => {
    return Array.isArray(result?.performance) ? result.performance : [];
  }, [result]);

  // Compute best values for each numeric column
  const bestValues = useMemo(() => {
    const map = {};
    for (const col of COLUMNS) {
      if (col.numeric) {
        map[col.key] = findBestMetricValue(performance, col.key, col.direction);
      }
    }
    return map;
  }, [performance]);

  // Sort rows cleanly
  const sortedRows = useMemo(() => {
    if (!sortKey) return performance;
    return sortPerformanceRows(performance, sortKey, sortDirection);
  }, [performance, sortKey, sortDirection]);

  const handleHeaderClick = (colKey) => {
    if (sortKey === colKey) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(colKey);
      const col = COLUMNS.find((c) => c.key === colKey);
      // Sensible default directions: ascending for costs/turnover/volatility, descending for returns
      if (col?.direction === 'min' || col?.direction === 'absMin' || colKey === 'Strategy') {
        setSortDirection('asc');
      } else {
        setSortDirection('desc');
      }
    }
  };

  const handleResetSort = () => {
    setSortKey(null);
    setSortDirection('desc');
  };

  if (performance.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center my-6">
        <Info className="w-8 h-8 text-slate-400 mx-auto mb-2" />
        <h3 className="text-base font-semibold text-slate-800">No Performance Data Available</h3>
        <p className="text-sm text-slate-500 mt-1">
          Run a simulation to generate the 4-strategy performance comparison matrix.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Header & Sort Control Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Comparative Performance Matrix</h3>
          <p className="text-xs sm:text-sm text-slate-500">
            Standardized financial metrics computed under actual execution, transaction cost, and whole-share constraints.
          </p>
        </div>

        <div className="flex items-center space-x-3 self-start sm:self-auto">
          {sortKey && (
            <button
              onClick={handleResetSort}
              className="inline-flex items-center text-xs font-medium text-slate-600 hover:text-navy bg-slate-100 hover:bg-slate-200 px-2.5 py-1.5 rounded-lg transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5 mr-1 text-slate-500" />
              Reset Order
            </button>
          )}

          {/* Legend */}
          <div className="inline-flex items-center text-xs text-slate-600 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-2xs">
            <span className="w-3 h-3 rounded bg-emerald-100 border border-emerald-300 mr-1.5 flex-shrink-0" />
            <span>Best Observed Value</span>
          </div>
        </div>
      </div>

      {/* Responsive Table Container */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[1000px]">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-[11px] font-bold text-slate-600 uppercase tracking-wider sticky top-0 z-10">
                {COLUMNS.map((col) => {
                  const isSorted = sortKey === col.key;
                  return (
                    <th
                      key={col.key}
                      scope="col"
                      className={`py-3.5 px-4 select-none ${
                        col.align === 'right' ? 'text-right' : 'text-left'
                      }`}
                    >
                      <button
                        type="button"
                        onClick={() => handleHeaderClick(col.key)}
                        className={`inline-flex items-center space-x-1 group hover:text-navy focus:outline-none focus:ring-1 focus:ring-navy rounded px-1 -mx-1 ${
                          col.align === 'right' ? 'justify-end ml-auto' : 'justify-start'
                        } ${isSorted ? 'text-navy font-extrabold' : ''}`}
                        title={col.tooltip}
                      >
                        <span>{col.label}</span>
                        <span className="text-slate-400 group-hover:text-slate-600">
                          {isSorted ? (
                            sortDirection === 'asc' ? (
                              <ArrowUp className="w-3.5 h-3.5 text-navy stroke-[2.5]" />
                            ) : (
                              <ArrowDown className="w-3.5 h-3.5 text-navy stroke-[2.5]" />
                            )
                          ) : (
                            <ArrowUpDown className="w-3 h-3 opacity-40 group-hover:opacity-100" />
                          )}
                        </span>
                      </button>
                    </th>
                  );
                })}
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100 text-xs sm:text-sm font-normal text-slate-800">
              {sortedRows.map((row, rowIdx) => {
                return (
                  <tr
                    key={row.Strategy || rowIdx}
                    className="hover:bg-slate-50/80 transition-colors"
                  >
                    {COLUMNS.map((col) => {
                      const rawVal = row[col.key];
                      const isBest =
                        col.numeric &&
                        isBestValue(rawVal, bestValues[col.key], col.direction);

                      return (
                        <td
                          key={col.key}
                          className={`py-3 px-4 whitespace-nowrap transition-colors ${
                            col.align === 'right' ? 'text-right' : 'text-left'
                          } ${
                            isBest
                              ? 'bg-emerald-100 text-emerald-950 font-bold'
                              : 'text-slate-700'
                          }`}
                        >
                          <div className="flex items-center space-x-1.5 justify-end">
                            {isBest && col.numeric && (
                              <Award
                                className="w-3.5 h-3.5 text-emerald flex-shrink-0"
                                title="Best Value"
                              />
                            )}
                            <span>{col.render(row)}</span>
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Table Footer with Explanatory Notes */}
        <div className="p-4 bg-slate-50/70 border-t border-slate-200 text-xs text-slate-500 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center space-x-1">
            <Info className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
            <span>
              Win Rate applies strictly to completed round-trip liquidation trades. Strategies with zero sells report —.
            </span>
          </div>
          <span className="text-[11px] text-slate-400 font-mono">
            Click any column header to sort
          </span>
        </div>
      </div>
    </div>
  );
}
