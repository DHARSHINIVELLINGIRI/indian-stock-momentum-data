import React, { useState, useMemo } from 'react';
import {
  Layers,
  Calendar,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  CheckCircle2,
  MinusCircle,
  AlertCircle,
  Info,
  ShieldCheck,
  Search,
} from 'lucide-react';
import { formatDate, formatUnsignedPercent } from '../utils/format';

/**
 * src/components/HoldingsTab.jsx
 * ==============================
 * Interactive month-end holdings analysis for Strategy 3 (Rank-Weighted Momentum).
 * Features:
 * - Chronological month-end date selector with Prev/Next cycling
 * - Summary metric cards: Active Holdings, New Entries, Retained, Exits
 * - Holdings table with Rank, Ticker, Target Weight, Weight visual bar, and Status badges
 * - Amber Buffer badge for retained holdings meeting buffer conditions (rank > X && rank <= 2X)
 * - Search / filter within selected month
 * - Strategy 3 logic & buffer explanation panel
 */
export default function HoldingsTab({ result }) {
  const [searchTerm, setSearchTerm] = useState('');

  // 1. Validate holdings dataset
  const holdings = useMemo(() => {
    return Array.isArray(result?.s3_holdings) ? result.s3_holdings : [];
  }, [result]);

  const targetX = useMemo(() => {
    const xVal = result?.meta?.x;
    return typeof xVal === 'number' && Number.isFinite(xVal) ? xVal : 20;
  }, [result]);

  // 2. Extract unique sorted month-end dates (chronological)
  const availableDates = useMemo(() => {
    if (!holdings.length) return [];
    const dateSet = new Set();
    holdings.forEach((h) => {
      if (h?.date && typeof h.date === 'string') {
        dateSet.add(h.date);
      }
    });
    return Array.from(dateSet).sort();
  }, [holdings]);

  // 3. Track selected date, defaulting to the latest available month-end
  const [selectedDateState, setSelectedDateState] = useState(null);

  // Derive active date safely so changes to result prop cleanly update
  const selectedDate = useMemo(() => {
    if (!availableDates.length) return null;
    if (selectedDateState && availableDates.includes(selectedDateState)) {
      return selectedDateState;
    }
    return availableDates[availableDates.length - 1];
  }, [availableDates, selectedDateState]);

  // Date navigation handlers
  const currentIndex = availableDates.indexOf(selectedDate);
  const handlePrevDate = () => {
    if (currentIndex > 0) {
      setSelectedDateState(availableDates[currentIndex - 1]);
    }
  };
  const handleNextDate = () => {
    if (currentIndex < availableDates.length - 1) {
      setSelectedDateState(availableDates[currentIndex + 1]);
    }
  };

  // 4. Filter and sort rows for the selected month-end
  const monthRows = useMemo(() => {
    if (!selectedDate || !holdings.length) return [];
    return holdings.filter((h) => h?.date === selectedDate);
  }, [holdings, selectedDate]);

  // Summary Metrics for the selected month
  const metrics = useMemo(() => {
    let active = 0;
    let newEntries = 0;
    let retained = 0;
    let exits = 0;
    let bufferRetained = 0;

    monthRows.forEach((row) => {
      const status = row?.status;
      const rank = row?.rank;
      const isBuffer =
        status === 'Retained' &&
        ((typeof rank === 'number' && rank > targetX && rank <= 2 * targetX) ||
          (row?.is_in_buffer === true && typeof rank === 'number' && rank > targetX));

      if (status === 'Exit') {
        exits += 1;
      } else {
        // Active position (New Entry or Retained)
        active += 1;
        if (status === 'New Entry') {
          newEntries += 1;
        } else if (status === 'Retained') {
          retained += 1;
          if (isBuffer) {
            bufferRetained += 1;
          }
        }
      }
    });

    return { active, newEntries, retained, exits, bufferRetained };
  }, [monthRows, targetX]);

  // Sorted and searched table rows
  const sortedTableRows = useMemo(() => {
    const list = [...monthRows];
    // Sort primarily by rank ascending, then by ticker alphabetically
    list.sort((a, b) => {
      const rankA = typeof a.rank === 'number' && Number.isFinite(a.rank) ? a.rank : 999999;
      const rankB = typeof b.rank === 'number' && Number.isFinite(b.rank) ? b.rank : 999999;
      if (rankA !== rankB) {
        return rankA - rankB;
      }
      return String(a.ticker || '').localeCompare(String(b.ticker || ''));
    });

    if (!searchTerm.trim()) {
      return list;
    }
    const q = searchTerm.trim().toLowerCase();
    return list.filter((r) => {
      return (
        String(r.ticker || '').toLowerCase().includes(q) ||
        String(r.status || '').toLowerCase().includes(q) ||
        String(r.rank || '').includes(q)
      );
    });
  }, [monthRows, searchTerm]);

  // Max weight in this month for visual bar scaling
  const maxWeightInMonth = useMemo(() => {
    let maxW = 0;
    monthRows.forEach((r) => {
      const w = typeof r.target_weight_pct === 'number' ? r.target_weight_pct : 0;
      if (w > maxW) maxW = w;
    });
    return maxW > 0 ? maxW : 10;
  }, [monthRows]);

  // 5. Empty State Handling
  if (!result || !holdings.length || !availableDates.length) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200/80 p-8 sm:p-12 text-center my-6 shadow-xs animate-fadeIn">
        <div className="w-12 h-12 rounded-2xl bg-blue-50 text-navy flex items-center justify-center mx-auto mb-4 border border-blue-100">
          <Layers className="w-6 h-6 text-navy" />
        </div>
        <h3 className="text-base sm:text-lg font-bold text-slate-800">
          No Holdings Data Available
        </h3>
        <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-md mx-auto">
          Run a backtest simulation above to view results.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6 sm:space-y-8 animate-fadeIn">
      {/* =========================================================================
          A. MONTH-END CONTROLS & DATE SELECTOR BAR
          ========================================================================= */}
      <section className="bg-white rounded-2xl border border-slate-200/80 p-4 sm:p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          {/* Prominent Current Month Title */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-navy flex items-center justify-center flex-shrink-0 border border-blue-100">
              <Calendar className="w-5 h-5 text-navy" />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Strategy 3 Holdings Cycle
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight">
                Month-End: {formatDate(selectedDate)}
              </h2>
            </div>
          </div>

          {/* Interactive Month Switcher Controls */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <div className="flex items-center rounded-xl border border-slate-200 bg-slate-50/60 p-0.5 shadow-2xs">
              <button
                type="button"
                onClick={handlePrevDate}
                disabled={currentIndex <= 0}
                aria-label="Previous month"
                className="p-2 rounded-lg text-slate-600 hover:text-navy hover:bg-white disabled:opacity-30 disabled:pointer-events-none transition-all cursor-pointer"
                title="Previous Month"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              <select
                id="month-end-selector"
                aria-label="Select month-end date"
                value={selectedDate || ''}
                onChange={(e) => setSelectedDateState(e.target.value)}
                className="bg-transparent text-xs sm:text-sm font-bold text-slate-800 px-3 py-1.5 focus:outline-none cursor-pointer"
              >
                {availableDates.map((date) => (
                  <option key={date} value={date}>
                    {formatDate(date)} ({date})
                  </option>
                ))}
              </select>

              <button
                type="button"
                onClick={handleNextDate}
                disabled={currentIndex >= availableDates.length - 1}
                aria-label="Next month"
                className="p-2 rounded-lg text-slate-600 hover:text-navy hover:bg-white disabled:opacity-30 disabled:pointer-events-none transition-all cursor-pointer"
                title="Next Month"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            <span className="text-xs font-medium text-slate-400 px-1">
              Cycle {currentIndex + 1} of {availableDates.length}
            </span>
          </div>
        </div>
      </section>

      {/* =========================================================================
          B. FOUR COMPACT SUMMARY METRIC CARDS
          ========================================================================= */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Active Holdings */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 mb-1">
            <span>Active Holdings</span>
            <div className="p-1 rounded-md bg-blue-50 text-navy">
              <Layers className="w-3.5 h-3.5 text-navy" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-slate-900 tracking-tight">
            {metrics.active}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Target basket of Top {targetX} equities
          </p>
        </div>

        {/* New Entries */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs hover:border-emerald/30 transition-all">
          <div className="flex items-center justify-between text-xs font-semibold text-emerald-700 mb-1">
            <span>New Entries</span>
            <div className="p-1 rounded-md bg-emerald/10 text-emerald">
              <TrendingUp className="w-3.5 h-3.5 text-emerald" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-emerald-600 tracking-tight">
            {metrics.newEntries}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Newly introduced this rebalance
          </p>
        </div>

        {/* Retained Holdings */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs hover:border-blue-200 transition-all">
          <div className="flex items-center justify-between text-xs font-semibold text-blue-700 mb-1">
            <span>Retained</span>
            <div className="p-1 rounded-md bg-blue-50 text-blue-600">
              <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-blue-900 tracking-tight">
            {metrics.retained}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Carried forward from previous cycle
            {metrics.bufferRetained > 0 && ` (${metrics.bufferRetained} in buffer)`}
          </p>
        </div>

        {/* Exits */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs hover:border-rose/30 transition-all">
          <div className="flex items-center justify-between text-xs font-semibold text-rose-700 mb-1">
            <span>Exits</span>
            <div className="p-1 rounded-md bg-rose/10 text-rose">
              <MinusCircle className="w-3.5 h-3.5 text-rose" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-rose-600 tracking-tight">
            {metrics.exits}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Fully liquidated positions
          </p>
        </div>
      </section>

      {/* =========================================================================
          C. STRATEGY EXPLANATION & BUFFER LOGIC PANEL
          ========================================================================= */}
      <section className="bg-gradient-to-r from-blue-50/70 via-slate-50 to-indigo-50/40 rounded-2xl border border-blue-200/70 p-4 sm:p-5 shadow-2xs">
        <div className="flex items-start space-x-3.5">
          <div className="p-2 bg-blue-100/80 text-navy rounded-xl flex-shrink-0 mt-0.5 border border-blue-200">
            <Info className="w-4 h-4 text-navy" />
          </div>
          <div className="text-xs sm:text-sm text-slate-700 leading-relaxed">
            <p className="font-semibold text-slate-900 mb-1">
              Strategy 3 Model & Buffer Dynamics:
            </p>
            <p>
              Strategy 3 selects the Top X stocks by risk-adjusted 12-1 momentum. It retains existing holdings while their rank remains within the 2X buffer zone, and weights holdings dynamically by rank. Stocks dropping below the 2X threshold are exited.
            </p>
            <div className="mt-2.5 pt-2 border-t border-blue-200/50 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-600">
              <span className="inline-flex items-center">
                <span className="w-2 h-2 rounded-full bg-emerald-500 mr-1.5"></span>
                <strong>New Entry:</strong> Fresh addition to Top {targetX}
              </span>
              <span className="inline-flex items-center">
                <span className="w-2 h-2 rounded-full bg-blue-600 mr-1.5"></span>
                <strong>Retained:</strong> Maintained incumbent position
              </span>
              <span className="inline-flex items-center">
                <span className="w-2 h-2 rounded-full bg-amber-500 mr-1.5"></span>
                <strong>Buffer Badge:</strong> Retained with rank between {targetX + 1} and {2 * targetX}
              </span>
              <span className="inline-flex items-center">
                <span className="w-2 h-2 rounded-full bg-rose-500 mr-1.5"></span>
                <strong>Exit:</strong> Rank &gt; {2 * targetX} or unranked (zero target weight)
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          D. HOLDINGS TABLE WITH SEARCH & WEIGHT BARS
          ========================================================================= */}
      <section className="bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
        {/* Table Header Bar with Search Filter */}
        <div className="p-4 sm:p-5 border-b border-slate-200/80 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Constituents Ledger — {formatDate(selectedDate)}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Showing {sortedTableRows.length} positions sorted by momentum rank ascending
            </p>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search ticker, status, or rank..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-xl border border-slate-200 bg-slate-50/50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-navy/30 focus:border-navy transition-all"
            />
          </div>
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse" role="table">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/75 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                <th scope="col" className="py-3 px-4 sm:px-6">Ticker</th>
                <th scope="col" className="py-3 px-4 text-center">Rank</th>
                <th scope="col" className="py-3 px-4 text-right">Target Weight</th>
                <th scope="col" className="py-3 px-4 sm:px-6 min-w-[140px]">Weight Distribution</th>
                <th scope="col" className="py-3 px-4 sm:px-6 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs sm:text-sm text-slate-700">
              {sortedTableRows.length > 0 ? (
                sortedTableRows.map((row, idx) => {
                  const rank = row?.rank;
                  const weightPct = typeof row?.target_weight_pct === 'number' ? row.target_weight_pct : 0;
                  const isExit = row?.status === 'Exit' || weightPct === 0;

                  // Proportional visual bar width clamped between 0% and 100%
                  const barWidthPct =
                    maxWeightInMonth > 0 && weightPct > 0
                      ? Math.min(100, Math.max(2, (weightPct / maxWeightInMonth) * 100))
                      : 0;

                  // Buffer badge evaluation: strictly for retained positions satisfying rank > X and rank <= 2X
                  const isBufferRetained =
                    row?.status === 'Retained' &&
                    ((typeof rank === 'number' && rank > targetX && rank <= 2 * targetX) ||
                      (row?.is_in_buffer === true && typeof rank === 'number' && rank > targetX));

                  return (
                    <tr
                      key={`${row.ticker}-${row.date}-${idx}`}
                      className={`hover:bg-slate-50/80 transition-colors ${
                        isExit ? 'bg-slate-50/40 text-slate-400' : ''
                      }`}
                    >
                      {/* Ticker */}
                      <td className="py-3 px-4 sm:px-6 font-bold text-slate-900">
                        <div className="flex items-center space-x-2">
                          <span>{row.ticker || '—'}</span>
                          {isExit && (
                            <span className="text-[10px] font-medium text-slate-400">
                              (Liquidated)
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Rank */}
                      <td className="py-3 px-4 text-center font-mono">
                        {typeof rank === 'number' && Number.isFinite(rank) ? (
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold ${
                              rank <= targetX
                                ? 'bg-blue-50 text-navy'
                                : rank <= 2 * targetX
                                ? 'bg-amber-50 text-amber-800 border border-amber-200'
                                : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            #{rank}
                          </span>
                        ) : (
                          <span className="text-slate-400">—</span>
                        )}
                      </td>

                      {/* Target Weight % */}
                      <td className="py-3 px-4 text-right font-mono font-bold">
                        {isExit ? (
                          <span className="text-slate-400">0.00%</span>
                        ) : (
                          <span className="text-slate-900">
                            {formatUnsignedPercent(weightPct, 2)}
                          </span>
                        )}
                      </td>

                      {/* Weight Visualization Bar */}
                      <td className="py-3 px-4 sm:px-6">
                        <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                          <div
                            className={`h-full rounded-full transition-all duration-300 ${
                              isExit
                                ? 'bg-transparent'
                                : row.status === 'New Entry'
                                ? 'bg-emerald-500'
                                : 'bg-navy'
                            }`}
                            style={{ width: `${barWidthPct}%` }}
                            role="progressbar"
                            aria-valuenow={weightPct}
                            aria-valuemin="0"
                            aria-valuemax="100"
                            title={`Allocation: ${weightPct.toFixed(2)}%`}
                          />
                        </div>
                      </td>

                      {/* Status Badges */}
                      <td className="py-3 px-4 sm:px-6 text-center whitespace-nowrap">
                        <div className="inline-flex items-center justify-center gap-1.5">
                          {row.status === 'New Entry' && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald/10 text-emerald-800 border border-emerald/20">
                              New Entry
                            </span>
                          )}

                          {row.status === 'Retained' && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-navy border border-blue-200">
                              Retained
                            </span>
                          )}

                          {row.status === 'Exit' && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                              Exit
                            </span>
                          )}

                          {/* Fallback for unrecognized status string */}
                          {row.status !== 'New Entry' &&
                            row.status !== 'Retained' &&
                            row.status !== 'Exit' && (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                                {row.status || 'Unknown'}
                              </span>
                            )}

                          {/* Buffer badge - strictly for Retained stocks inside the 2X threshold */}
                          {isBufferRetained && (
                            <span
                              className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-900 border border-amber-300 shadow-2xs"
                              title={`Retained via Buffer: Momentum rank (${rank}) is outside the Top ${targetX} selection window but within the 2X buffer zone (<= ${2 * targetX}).`}
                            >
                              Buffer
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan="5" className="py-8 text-center text-slate-400">
                    No holdings match your search filter "{searchTerm}".
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
