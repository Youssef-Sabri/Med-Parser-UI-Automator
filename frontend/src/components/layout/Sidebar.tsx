import React, { useEffect, useState } from 'react';
import { 
  History, 
  LayoutDashboard, 
  PlusCircle,
  DatabaseIcon
} from 'lucide-react';
import { getStats } from '../../services/api';

interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
  onClick?: () => void;
}

const NavItem: React.FC<NavItemProps> = ({ icon, label, active, onClick }) => (
  <button 
    onClick={onClick}
    className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
      active 
        ? 'bg-clinical-blue text-white shadow-lg shadow-clinical-blue/20' 
        : 'text-slate-500 hover:bg-slate-50 hover:text-clinical-blue'
    }`}
  >
    <span className={`${active ? 'text-white' : 'group-hover:scale-110 transition-transform'}`}>{icon}</span>
    <span className="font-medium text-sm">{label}</span>
  </button>
);

export const Sidebar: React.FC = () => {
  const [stats, setStats] = useState<{ total_records: number; total_capacity: number } | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getStats();
        setStats({ total_records: data.total_records, total_capacity: data.total_capacity });
      } catch (err) {
        console.error('Sidebar stats fetch failed', err);
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 60000); // Poll every minute
    return () => clearInterval(interval);
  }, []);

  const scrollToAudit = () => {
    window.dispatchEvent(new CustomEvent('switch-ops-feed-mode', { detail: { mode: 'HISTORY' } }));
  };

  const usagePercent = stats ? Math.min(Math.round((stats.total_records / stats.total_capacity) * 100), 100) : 0;

  return (
    <aside className="w-64 bg-white border-r border-clinical-border flex flex-col h-full z-40">
      <div className="p-6">
        <button 
          onClick={() => window.dispatchEvent(new CustomEvent('trigger-file-picker'))}
          className="w-full bg-clinical-blue text-white rounded-xl py-3.5 flex items-center justify-center space-x-2 font-bold shadow-lg shadow-clinical-blue/20 hover:bg-clinical-blue-hover active:scale-[0.98] transition-all"
        >
          <PlusCircle className="w-5 h-5" />
          <span>New Extraction</span>
        </button>
      </div>

      <nav className="flex-1 px-4 space-y-2 py-2">
        <NavItem icon={<LayoutDashboard className="w-5 h-5" />} label="Live Dashboard" active />
      </nav>

      <div className="p-4 border-t border-clinical-border">
        <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100">
          <div className="flex items-center space-x-2 mb-2">
            <DatabaseIcon className="w-3.5 h-3.5 text-clinical-blue" />
            <span className="text-[10px] font-bold text-slate-800 uppercase tracking-wider">Storage Node</span>
          </div>
          <div className="h-1.5 w-full bg-slate-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-clinical-blue rounded-full transition-all duration-1000" 
              style={{ width: `${usagePercent}%` }} 
            />
          </div>
          <p className="mt-2 text-[10px] text-slate-500 font-medium">
            {stats ? `${stats.total_records.toLocaleString()} / ${stats.total_capacity.toLocaleString()} records` : 'fetching...'}
          </p>
        </div>
      </div>
    </aside>
  );
};
