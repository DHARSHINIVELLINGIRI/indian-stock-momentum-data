import React from 'react';
import { Clock } from 'lucide-react';

export default function TabPlaceholder({ title, description, icon: Icon }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-8 sm:p-12 text-center my-6 shadow-sm animate-fadeIn">
      <div className="w-14 h-14 bg-blue-50 text-navy rounded-2xl flex items-center justify-center mx-auto mb-4 border border-blue-100">
        {Icon ? <Icon className="w-7 h-7" /> : <Clock className="w-7 h-7" />}
      </div>
      <h3 className="text-lg font-bold text-slate-900 mb-1">{title} Module</h3>
      <p className="text-sm text-slate-500 max-w-md mx-auto leading-relaxed mb-4">
        {description}
      </p>
      <div className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200">
        <Clock className="w-3.5 h-3.5 mr-1.5 text-slate-400" />
        This section will be implemented next
      </div>
    </div>
  );
}
