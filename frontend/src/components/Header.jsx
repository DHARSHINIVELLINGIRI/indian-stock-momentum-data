import React from 'react';
import { TrendingUp, ShieldCheck } from 'lucide-react';

export default function Header() {
  return (
    <header className="bg-navy text-white shadow-lg border-b border-blue-900/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="p-2.5 bg-blue-800/80 rounded-xl shadow-inner border border-blue-400/20 text-emerald-400">
              <TrendingUp className="w-7 h-7 text-emerald" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                Quantitative Momentum Strategy Backtesting System
              </h1>
              <p className="text-sm font-medium text-blue-200/90 mt-0.5">
                Indian Equities (NSE), Oct 2022 - Oct 2026
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-xs font-medium text-blue-200 self-start md:self-auto">
            <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-blue-800/60 border border-blue-700/50 text-blue-100">
              <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald" />
              Verified Engine
            </span>
            <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-blue-800/60 border border-blue-700/50 text-blue-100">
              NSE 100 Universe
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
