import React, { useEffect, useState } from 'react';
import { ActivityIcon, BarChart3Icon, ShieldAlertIcon } from 'lucide-react';
import { getStats } from '../../services/api';

interface Stats {
  scripts_today: number;
  total_processed: number;
  approval_rate: number;
  blocking_count: number;
  total_decisions: number;
  total_records: number;
  total_capacity: number;
  daily_capacity: number;  // denominator for daily gauge
}

export const ClinicalStatsPanel: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);

  const fetchStats = React.useCallback(async () => {
    try {
      const data = await getStats();
      // Guard: if backend hasn't been rebuilt yet, daily_capacity may be missing.
      // Default to 200 (MAX_DAILY_CAPACITY default) so gauge shows a real % not NaN.
      setStats({ ...data, daily_capacity: data.daily_capacity ?? 200 });

    } catch (err) {
      console.error('Failed to fetch stats', err);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Poll every 30s
    return () => clearInterval(interval);
  }, []);

  if (!stats) return null;

  return (
    <div className="clinical-card p-5 space-y-6">
      <div className="flex items-center space-x-2">
        <ActivityIcon className="w-5 h-5 text-clinical-blue" />
        <h3 className="font-display font-bold text-sm text-slate-800 uppercase tracking-tight">System Performance</h3>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex flex-col items-center justify-center text-center">
          <span className="text-[9px] font-bold text-slate-400 uppercase mb-1">Processed Today</span>
          <span className="text-xl font-display font-bold text-slate-800">{stats.scripts_today}</span>
        </div>
        <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex flex-col items-center justify-center text-center">
          <span className="text-[9px] font-bold text-slate-400 uppercase mb-1">Approval Rate</span>
          <span className="text-xl font-display font-bold text-vibrant-mint">{stats.approval_rate}%</span>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between p-3 bg-health-red/5 rounded-xl border border-health-red/10">
          <div className="flex items-center space-x-2">
            <ShieldAlertIcon className="w-4 h-4 text-health-red" />
            <span className="text-xs font-bold text-slate-700">Safety Flag Blocks</span>
          </div>
          <span className="text-sm font-bold text-health-red">{stats.blocking_count}</span>
        </div>

        <div className="flex items-center justify-between p-3 bg-clinical-blue/5 rounded-xl border border-clinical-blue/10">
          <div className="flex items-center space-x-2">
            <BarChart3Icon className="w-4 h-4 text-clinical-blue" />
            <span className="text-xs font-bold text-slate-700">Audit Chain Throughput</span>
          </div>
          <span className="text-sm font-bold text-clinical-blue">{stats.total_decisions}</span>
        </div>

        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100">
          <div className="flex items-center space-x-2">
            <BarChart3Icon className="w-4 h-4 text-slate-400" />
            <span className="text-xs font-bold text-slate-700">Total Clinical Records</span>
          </div>
          <span className="text-sm font-bold text-slate-800">{stats.total_records}</span>
        </div>
      </div>

      <div className="pt-2 border-t border-slate-100 flex flex-col space-y-3">
         <div className="flex flex-col space-y-1.5 px-2">
            <div className="flex justify-between items-end">
               <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Daily Capacity Usage</span>
               {/* Use daily_capacity (e.g. 200 rx/day) not total_capacity (50,000 lifetime) */}
               <span className="text-[10px] font-black text-slate-800">
                 {(Math.min((stats.scripts_today / stats.daily_capacity) * 100, 100)).toFixed(1)}%
               </span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
               <div
                  className={`h-full rounded-full transition-all duration-1000 ${
                     (stats.scripts_today / stats.daily_capacity) > 0.8 ? 'bg-health-red' : 'bg-clinical-blue'
                  }`}
                  style={{ width: `${Math.min((stats.scripts_today / stats.daily_capacity) * 100, 100)}%` }}
               />
            </div>
            <p className="text-[8px] text-slate-400 text-right">
              {stats.scripts_today} / {stats.daily_capacity} today
            </p>
         </div>
         <p className="text-[9px] text-slate-400 leading-relaxed text-center px-2">
           Real-time metrics provided by <span className="text-clinical-blue font-bold">Med-Parser Core</span>. Data is encrypted and compliant with HIPAA visibility standards.
         </p>
      </div>
    </div>
  );
};
