import React, { useEffect, useState, useCallback } from 'react';
import { getStrategies } from '../api/client';
import { RefreshCw, AlertTriangle, Layers, Award } from 'lucide-react';

const STRATEGY_THEMES = {
  1: { badge: 'bg-blue-50 text-blue-700 border-blue-200', border: 'border-t-blue-600', iconColor: 'text-blue-600' },
  2: { badge: 'bg-emerald-50 text-emerald-700 border-emerald-200', border: 'border-t-emerald-600', iconColor: 'text-emerald-600' },
  3: { badge: 'bg-indigo-50 text-indigo-700 border-indigo-200', border: 'border-t-indigo-600', iconColor: 'text-indigo-600' },
  4: { badge: 'bg-amber-50 text-amber-700 border-amber-200', border: 'border-t-amber-600', iconColor: 'text-amber-600' },
};

export default function StrategyCards() {
  const [strategies, setStrategies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStrategies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getStrategies();
      setStrategies(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || 'Failed to fetch strategy definitions from server.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  if (loading) {
    return (
      <section className="my-8">
        <div className="flex items-center justify-between mb-4">
          <div className="h-6 w-48 bg-slate-200 rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-3 animate-pulse"
            >
              <div className="flex justify-between items-center">
                <div className="h-5 w-20 bg-slate-200 rounded-full" />
                <div className="h-6 w-6 bg-slate-100 rounded-full" />
              </div>
              <div className="h-6 w-3/4 bg-slate-200 rounded" />
              <div className="space-y-2 pt-2">
                <div className="h-4 w-full bg-slate-100 rounded" />
                <div className="h-4 w-5/6 bg-slate-100 rounded" />
                <div className="h-4 w-4/6 bg-slate-100 rounded" />
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (error) {
    return (
      <section className="my-8">
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-6 text-rose-800 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-6 h-6 text-rose flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-base font-semibold text-rose-900">
                Failed to Load Strategy Models
              </h3>
              <p className="text-sm text-rose-700 mt-1">{error}</p>
            </div>
          </div>
          <button
            onClick={fetchStrategies}
            className="inline-flex items-center justify-center px-4 py-2 border border-rose-300 rounded-lg text-sm font-medium bg-white text-rose-700 hover:bg-rose-100/50 shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-rose-500"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </button>
        </div>
      </section>
    );
  }

  if (strategies.length === 0) {
    return (
      <section className="my-8">
        <div className="bg-white border border-slate-200 rounded-xl p-8 text-center shadow-sm">
          <Layers className="w-10 h-10 text-slate-400 mx-auto mb-2" />
          <h3 className="text-base font-semibold text-slate-800">No Strategies Available</h3>
          <p className="text-sm text-slate-500 mt-1">
            The server returned an empty strategy list.
          </p>
          <button
            onClick={fetchStrategies}
            className="mt-4 inline-flex items-center px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 shadow-sm"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="my-8">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Backtested Strategy Models</h2>
          <p className="text-xs sm:text-sm text-slate-500">
            Four comparative quantitative models backtested simultaneously under identical market conditions.
          </p>
        </div>
        <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full border border-slate-200">
          {strategies.length} Strategies Active
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {strategies.map((strat) => {
          const theme = STRATEGY_THEMES[strat.id] || {
            badge: 'bg-slate-50 text-slate-700 border-slate-200',
            border: 'border-t-slate-600',
            iconColor: 'text-slate-600',
          };

          return (
            <div
              key={strat.id}
              className={`bg-white rounded-xl border border-slate-200/90 shadow-sm hover:shadow-md transition-all duration-200 p-5 flex flex-col justify-between border-t-4 ${theme.border}`}
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold border ${theme.badge}`}
                  >
                    Strategy {strat.id}
                  </span>
                  <Award className={`w-4 h-4 ${theme.iconColor}`} />
                </div>
                <h3 className="text-base font-bold text-slate-900 leading-snug mb-2">
                  {strat.name}
                </h3>
                <div className="text-xs text-slate-600 leading-relaxed whitespace-pre-line font-normal">
                  {strat.description}
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                <span>Model ID: #{strat.id}</span>
                <span className="font-medium text-slate-500">NSE 100</span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
