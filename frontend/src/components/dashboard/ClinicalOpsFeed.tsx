import React, { useEffect, useState, useCallback } from 'react';
import { 
  HistoryIcon, 
  ClockIcon, 
  AlertCircleIcon, 
  Loader2Icon,
  Filter
} from 'lucide-react';
import { getQueue, getAuditLog } from '../../services/api';
import { getStatusIcon, getStatusColorClasses } from '../../utils/statusPresentation';
import { type StatusType } from '../../types';

interface FeedItem {
  id: string;
  filename: string;
  status: StatusType;
  flags: string[];
  created_at: string;
}

interface ClinicalOpsFeedProps {
  onItemClick?: (id: string) => void;
}

/**
 * Unified Operations Feed - Replaces both QueueStatusPanel and SystemAuditLog.
 * Provides a single, real-time stream of all pharmacy automation activity.
 */
export const ClinicalOpsFeed: React.FC<ClinicalOpsFeedProps> = ({ onItemClick }) => {
  const [items, setItems] = useState<FeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'ALL' | 'ACTIVE' | 'FAILED'>('ALL');
  const [mode, setMode] = useState<'LIVE' | 'HISTORY'>('LIVE');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchFeed = useCallback(async () => {
    try {
      setError(null);
      const data = mode === 'LIVE' ? await getQueue(25, searchQuery) : await getAuditLog(50, searchQuery);
      setItems(data as FeedItem[]);
    } catch (err) {
      console.error('Failed to fetch operations feed', err);
      setError('Connection interrupted. Unable to sync feed.');
    } finally {
      setLoading(false);
    }
  }, [mode, searchQuery]);

  useEffect(() => {
    fetchFeed();
    const interval = setInterval(fetchFeed, 5000); 

    const handleModeSwitch = ((e: CustomEvent) => {
      if (e.detail?.mode) {
        setItems([]); // Clear local items to prevent flashing stale data
        setLoading(true);
        setMode(e.detail.mode);
        document.getElementById('ops-feed-container')?.scrollIntoView({ behavior: 'smooth' });
      }
    }) as EventListener;

    const handleSearch = ((e: CustomEvent) => {
      if (typeof e.detail?.query === 'string') {
        setSearchQuery(e.detail.query);
      }
    }) as EventListener;

    window.addEventListener('switch-ops-feed-mode', handleModeSwitch);
    window.addEventListener('ops-feed-search', handleSearch);

    return () => {
      clearInterval(interval);
      window.removeEventListener('switch-ops-feed-mode', handleModeSwitch);
      window.removeEventListener('ops-feed-search', handleSearch);
    };
  }, [fetchFeed]);

  const filteredItems = items.filter(item => {
    if (filter === 'ACTIVE') return ['QUEUED', 'PROCESSING', 'INJECTING'].includes(item.status);
    if (filter === 'FAILED') return item.status === 'FAILED';
    return true;
  });

  return (
    <div id="ops-feed-container" className="clinical-card flex flex-col h-full overflow-hidden bg-white border-none shadow-sm">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 bg-slate-50/50">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            {mode === 'LIVE' ? (
              <ClockIcon className="w-4 h-4 text-clinical-blue animate-pulse" />
            ) : (
              <HistoryIcon className="w-4 h-4 text-slate-400" />
            )}
            <h3 className="text-[11px] font-bold text-slate-700 uppercase tracking-widest">
              {mode === 'LIVE' ? 'Operations Feed' : 'Historical Audit'}
            </h3>
          </div>
          <div 
            onClick={() => {
              setItems([]);
              setMode(mode === 'LIVE' ? 'HISTORY' : 'LIVE');
              setLoading(true);
            }}
            className={`flex items-center space-x-1.5 px-2 py-0.5 rounded-full border cursor-pointer group transition-all ${
              mode === 'LIVE' 
                ? 'bg-vibrant-mint/10 border-vibrant-mint/20 text-vibrant-mint hover:bg-vibrant-mint/20' 
                : 'bg-clinical-blue/10 border-clinical-blue/20 text-clinical-blue hover:bg-clinical-blue/20 shadow-sm'
            }`}
          >
            <div className={`w-1.5 h-1.5 rounded-full ${mode === 'LIVE' ? 'bg-vibrant-mint animate-pulse' : 'bg-clinical-blue'}`} />
            <span className="text-[9px] font-black uppercase tracking-tighter">
              {mode === 'LIVE' ? 'Live' : 'History'}
            </span>
          </div>
        </div>

        {/* Quick Filters */}
        <div className="flex items-center space-x-2">
           <Filter className="w-3 h-3 text-slate-300 mr-1" />
           <button 
             onClick={() => setFilter('ALL')}
             className={`text-[9px] font-bold px-2 py-1 rounded-md transition-all ${filter === 'ALL' ? 'bg-slate-700 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-100'}`}
           >
             All
           </button>
           <button 
             onClick={() => setFilter('ACTIVE')}
             className={`text-[9px] font-bold px-2 py-1 rounded-md transition-all ${filter === 'ACTIVE' ? 'bg-clinical-blue text-white shadow-sm' : 'text-slate-500 hover:bg-slate-100'}`}
           >
             Active
           </button>
           <button 
             onClick={() => setFilter('FAILED')}
             className={`text-[9px] font-bold px-2 py-1 rounded-md transition-all ${filter === 'FAILED' ? 'bg-health-red text-white shadow-sm' : 'text-slate-500 hover:bg-slate-100'}`}
           >
             Failed
           </button>
        </div>
      </div>

      {error && (
        <div className="bg-health-red/5 border-b border-health-red/10 px-4 py-2.5 flex items-center space-x-2">
          <AlertCircleIcon className="w-3 h-3 text-health-red" />
          <span className="text-[9px] font-bold text-health-red uppercase tracking-widest">{error}</span>
        </div>
      )}

      {/* Feed List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {loading && items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 space-y-3 opacity-50">
            <Loader2Icon className="w-6 h-6 text-slate-200 animate-spin" />
            <span className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">Syncing Feed...</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 opacity-30 grayscale">
            <HistoryIcon className="w-8 h-8 text-slate-300 mb-2" />
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">No activity found</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {filteredItems.map((item) => (
              <div 
                key={item.id}
                onClick={() => onItemClick?.(item.id)}
                className={`p-4 hover:bg-slate-50 transition-all cursor-pointer group relative overflow-hidden ${['PROCESSING', 'INJECTING'].includes(item.status) ? 'bg-blue-50/20' : ''}`}
              >
                {['PROCESSING', 'INJECTING'].includes(item.status) && (
                  <div className="absolute top-0 left-0 w-1 h-full bg-clinical-blue" />
                )}
                
                <div className="flex items-start justify-between">
                  <div className="min-w-0 pr-4">
                    <div className="flex items-center space-x-2 mb-0.5">
                      {getStatusIcon(item.status)}
                      <span className="text-[11px] font-bold text-slate-800 truncate" title={item.filename}>
                        {item.filename.split('_').pop() || item.filename}
                      </span>
                    </div>
                    <div className="flex items-center space-x-3 text-[9px] text-slate-400 font-medium">
                      <span className="font-mono uppercase text-[8px] bg-slate-100 px-1 py-0.5 rounded">{item.id.split('-')[0]}</span>
                      <span>{new Date(item.created_at).toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
                    </div>
                  </div>
                  
                  <div className="flex flex-col items-end">
                    <span className={`text-[8px] font-black uppercase tracking-tighter px-2 py-0.5 rounded-full border transition-all ${getStatusColorClasses(item.status)}`}>
                      {item.status}
                    </span>
                  </div>
                </div>

                {/* Flags Preview */}
                {item.flags && item.flags.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap gap-1">
                    {item.flags.slice(0, 2).map((flag, i) => (
                      <span key={i} className={`text-[8px] font-bold px-1.5 py-0.5 rounded uppercase tracking-tighter ${
                        flag.toUpperCase().includes('BLOCKING') 
                          ? 'bg-health-red/10 text-health-red border border-health-red/20' 
                          : 'bg-caution-amber/10 text-caution-amber border border-caution-amber/20'
                      }`}>
                        {flag.replace('BLOCKING: ', '').replace('ADVISORY: ', '').substring(0, 20)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer / Stats Summary */}
      <div className="p-3 bg-slate-50 border-t border-slate-100">
        <button 
          onClick={fetchFeed}
          className="w-full py-2 text-[9px] font-bold text-slate-400 hover:text-clinical-blue uppercase tracking-widest transition-all text-center"
        >
          Refresh Control Feed
        </button>
      </div>
    </div>
  );
};
