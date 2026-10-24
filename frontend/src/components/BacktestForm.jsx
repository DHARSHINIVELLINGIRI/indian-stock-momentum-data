import React, { useState, useEffect, useRef, useCallback } from 'react';
import { runBacktest } from '../api/client';
import { formatINR } from '../utils/format';
import {
  Play,
  RotateCcw,
  AlertTriangle,
  Loader2,
  Sliders,
  DollarSign,
  Hash,
  Info,
} from 'lucide-react';

export default function BacktestForm({ onResult }) {
  const [capital, setCapital] = useState(500000);
  const [x, setX] = useState(20);
  const [acknowledged, setAcknowledged] = useState(false);
  const [loading, setLoading] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [error, setError] = useState(null);

  const timerRef = useRef(null);

  // Clean up interval timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  // Validation rules matching backend constraints
  const numCapital = Number(capital);
  const numX = Number(x);

  let validationError = null;
  if (!numCapital || isNaN(numCapital) || numCapital < 10000) {
    validationError = 'Initial capital must be at least ₹10,000.';
  } else if (numCapital > 100000000) {
    validationError = 'Initial capital cannot exceed ₹10,00,00,000.';
  } else if (!numX || isNaN(numX) || numX < 5) {
    validationError = 'Number of stocks (X) must be at least 5.';
  } else if (numX > 50) {
    validationError = 'Number of stocks (X) cannot exceed 50.';
  } else if (!Number.isInteger(numX)) {
    validationError = 'Number of stocks must be a whole number.';
  }

  // Low-capital threshold check: capital / x < 2000
  const capitalPerStock = numCapital > 0 && numX > 0 ? numCapital / numX : 0;
  const isLowCapital = !validationError && capitalPerStock < 2000;

  // The Run button must remain disabled until acknowledged if low capital warning is triggered
  const isButtonDisabled = loading || !!validationError || (isLowCapital && !acknowledged);

  const handleCapitalChange = (e) => {
    const val = e.target.value;
    setCapital(val);
    setAcknowledged(false); // Reset acknowledgement on input change
    setError(null);
  };

  const handleXChange = (e) => {
    const val = e.target.value;
    setX(val);
    setAcknowledged(false); // Reset acknowledgement on input change
    setError(null);
  };

  const handleExecute = useCallback(async () => {
    if (isButtonDisabled || loading) return;

    setError(null);
    setLoading(true);
    setElapsedSeconds(0);

    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTime) / 1000));
    }, 500);

    try {
      const data = await runBacktest(numCapital, numX);
      if (onResult) {
        onResult(data);
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred while executing the simulation.');
    } finally {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      setLoading(false);
    }
  }, [isButtonDisabled, loading, numCapital, numX, onResult]);

  return (
    <section className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 sm:p-8 my-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-6 mb-6 border-b border-slate-100 gap-2">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-blue-50 text-navy rounded-xl">
            <Sliders className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-900">Configure Backtest Simulation</h2>
            <p className="text-xs sm:text-sm text-slate-500">
              Customize initial equity and momentum portfolio breadth across all 4 strategy engines.
            </p>
          </div>
        </div>
        <div className="text-xs text-slate-400">
          Execution Rule: Whole-share, zero fractional allocation
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Initial Capital Input */}
        <div>
          <label
            htmlFor="capital-input"
            className="block text-sm font-semibold text-slate-800 mb-1.5 flex items-center justify-between"
          >
            <span className="flex items-center">
              <DollarSign className="w-4 h-4 mr-1 text-slate-400" />
              Initial Capital (INR)
            </span>
            <span className="text-xs font-medium text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
              {formatINR(numCapital)}
            </span>
          </label>
          <div className="relative rounded-lg shadow-sm">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400 font-semibold">
              ₹
            </div>
            <input
              id="capital-input"
              type="number"
              min="10000"
              max="100000000"
              step="10000"
              value={capital}
              onChange={handleCapitalChange}
              disabled={loading}
              className="block w-full pl-8 pr-4 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-navy focus:border-navy text-sm font-medium transition-colors disabled:bg-slate-50 disabled:text-slate-500"
              placeholder="e.g. 500000"
            />
          </div>
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-slate-400">Min: ₹10,000 | Step: ₹10,000</span>
            <div className="flex space-x-1.5">
              {[250000, 500000, 1000000].map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => {
                    setCapital(preset);
                    setAcknowledged(false);
                    setError(null);
                  }}
                  disabled={loading}
                  className="text-[11px] px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded transition-colors"
                >
                  ₹{preset / 100000}L
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Top X Stocks Input */}
        <div>
          <label
            htmlFor="x-input"
            className="block text-sm font-semibold text-slate-800 mb-1.5 flex items-center justify-between"
          >
            <span className="flex items-center">
              <Hash className="w-4 h-4 mr-1 text-slate-400" />
              Number of Top Stocks to Hold (X)
            </span>
            <span className="text-xs font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
              Buffer (2X): {numX * 2} stocks
            </span>
          </label>
          <div className="relative rounded-lg shadow-sm">
            <input
              id="x-input"
              type="number"
              min="5"
              max="50"
              step="1"
              value={x}
              onChange={handleXChange}
              disabled={loading}
              className="block w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-navy focus:border-navy text-sm font-medium transition-colors disabled:bg-slate-50 disabled:text-slate-500"
              placeholder="e.g. 20"
            />
          </div>
          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-slate-400">Min: 5 | Max: 50 stocks</span>
            <div className="flex space-x-1.5">
              {[10, 20, 30].map((preset) => (
                <button
                  key={preset}
                  type="button"
                  onClick={() => {
                    setX(preset);
                    setAcknowledged(false);
                    setError(null);
                  }}
                  disabled={loading}
                  className="text-[11px] px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded transition-colors"
                >
                  X={preset}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Dynamic Summary Metric: Capital Per Stock */}
      <div className="mt-5 p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 flex flex-col sm:flex-row sm:items-center justify-between text-xs gap-2">
        <div className="flex items-center text-slate-600">
          <Info className="w-4 h-4 mr-2 text-slate-400 flex-shrink-0" />
          <span>
            Capital per stock allocation target:{' '}
            <strong className="text-slate-900 font-semibold">{formatINR(capitalPerStock)}</strong>
          </span>
        </div>
        <span className="text-slate-400">
          Simulation window: 983 trading days (48 monthly rebalances)
        </span>
      </div>

      {/* Validation Error Message */}
      {validationError && (
        <div className="mt-4 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs font-medium text-rose-700 flex items-center">
          <AlertTriangle className="w-4 h-4 mr-2 text-rose flex-shrink-0" />
          {validationError}
        </div>
      )}

      {/* Exact Low-Capital Warning & Checkbox */}
      {isLowCapital && (
        <div className="mt-5 p-4 bg-amber-50 border border-amber-300 rounded-xl text-amber-900 shadow-sm animate-fadeIn">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-bold text-amber-900">Low Capital Allocation Warning</h4>
              <p className="text-xs sm:text-sm text-amber-800 mt-1 leading-relaxed">
                Your capital per stock is very low. Many high-priced stocks will be skipped due to the whole-share execution rule.
              </p>
              <div className="mt-3 flex items-center space-x-2">
                <input
                  id="acknowledge-warning"
                  type="checkbox"
                  checked={acknowledged}
                  onChange={(e) => setAcknowledged(e.target.checked)}
                  disabled={loading}
                  className="w-4 h-4 text-navy rounded border-amber-400 focus:ring-navy focus:ring-offset-amber-50"
                />
                <label
                  htmlFor="acknowledge-warning"
                  className="text-xs sm:text-sm font-semibold text-amber-950 cursor-pointer select-none"
                >
                  I understand and want to proceed
                </label>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Execution Error Card with Retry Button */}
      {error && (
        <div className="mt-6 p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-900 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 text-rose flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-bold text-rose-900">Simulation Run Failed</h4>
              <p className="text-xs sm:text-sm text-rose-700 mt-0.5">{error}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleExecute}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 bg-white border border-rose-300 rounded-lg text-xs sm:text-sm font-semibold text-rose-700 hover:bg-rose-100/50 shadow-sm transition-colors focus:outline-none focus:ring-2 focus:ring-rose-500 self-start sm:self-auto"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
            Retry
          </button>
        </div>
      )}

      {/* Run Simulation Button */}
      <div className="mt-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-4 border-t border-slate-100">
        <div className="text-xs text-slate-500">
          Results are computed in-memory and cached instantly.
        </div>
        <button
          type="button"
          onClick={handleExecute}
          disabled={isButtonDisabled}
          className="inline-flex items-center justify-center px-6 py-3 border border-transparent rounded-xl text-sm font-bold text-white bg-navy hover:bg-blue-900 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-navy shadow-md transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none min-w-[240px]"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin text-white" />
              <span>Running Backtest Simulation ({elapsedSeconds}s)...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 mr-2 fill-current text-white" />
              <span>Run Backtest Simulation</span>
            </>
          )}
        </button>
      </div>
    </section>
  );
}
