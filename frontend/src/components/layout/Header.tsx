import React, { useState, useEffect } from 'react';
import { ShieldCheck, UserCircle, CpuIcon, ServerIcon } from 'lucide-react';
import { getAgentHealth, getBackendHealth } from '../../services/api';

export const Header: React.FC = () => {
  const [agentStatus, setAgentStatus] = useState<'online' | 'offline'>('offline');
  const [backendStatus, setBackendStatus] = useState<'online' | 'offline'>('offline');

  useEffect(() => {
    const checkStatus = async () => {
      const dbHealth = await getBackendHealth();
      setBackendStatus(dbHealth.status === 'healthy' ? 'online' : 'offline');

      const rpaHealth = await getAgentHealth();
      setAgentStatus(rpaHealth.status === 'online' ? 'online' : 'offline');
    };
    checkStatus();
    const interval = setInterval(checkStatus, 10000); // Check every 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 bg-white border-b border-clinical-border flex items-center justify-between px-6 z-30 shadow-sm">
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 bg-clinical-blue rounded-lg flex items-center justify-center shadow-md shadow-clinical-blue/20">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <span className="font-display font-bold text-lg text-slate-800 tracking-tight">
            Clinical <span className="text-clinical-blue">Assistant</span>
          </span>
        </div>

        <div className="h-4 w-[1px] bg-slate-200 hidden sm:block" />

        <div className="hidden sm:flex items-center space-x-3 text-[11px] font-bold uppercase tracking-wider text-slate-600 bg-white/80 backdrop-blur-sm px-5 py-2 rounded-full border border-slate-200/60 shadow-sm">
          <div className={`flex items-center space-x-2`} title="Backend API & DB Engine">
            <div className={`w-2.5 h-2.5 rounded-full transition-all duration-500 ${backendStatus === 'online' ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.6)]' : 'bg-slate-300'}`} />
            <span className="text-slate-700 font-semibold">
              {backendStatus === 'online' ? 'API Online' : 'API Offline'}
            </span>
          </div>
          <div className="w-px h-4 bg-slate-300" />
          <div className={`flex items-center space-x-2`} title="Desktop UI Automation Engine">
            <div className={`w-2.5 h-2.5 rounded-full transition-all duration-500 ${agentStatus === 'online' ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.6)]' : 'bg-slate-300'}`} />
            <span className="text-slate-700 font-semibold">
              {agentStatus === 'online' ? 'RPA Online' : 'RPA Offline'}
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-3 pl-2">
          <div className="text-right hidden md:block">
            <p className="text-xs font-bold text-slate-800 leading-tight">Authorized Clinician</p>
            <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">Health Node Access</p>
          </div>
          <div className="w-9 h-9 bg-slate-100 rounded-full flex items-center justify-center border border-slate-200">
            <UserCircle className="w-6 h-6 text-slate-400" />
          </div>
        </div>
      </div>
    </header>
  );
};
