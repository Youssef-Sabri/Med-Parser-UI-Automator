import React from 'react';
import { Header } from './Header.tsx';
import { Sidebar } from './Sidebar.tsx';
import { AlertTriangleIcon } from 'lucide-react';

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <div className="flex h-screen bg-clinical-void overflow-hidden selection:bg-clinical-blue/10">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 h-full">
        {/* Rate Limit Banner */}
        <RateLimitBanner />

        {/* Global Header */}
        <Header />

        {/* Main View Area - Industrial Scale */}
        <main className="flex-1 relative overflow-y-auto overflow-x-hidden bg-white/50 backdrop-blur-sm">
          <div className="h-full flex flex-col p-4 sm:p-6 transition-all duration-300">
            {children}
          </div>
        </main>
      </div>

      {/* HIPAA Compliance Status Bar */}
      <div className="fixed bottom-6 right-6 z-50 pointer-events-none">
        <div className="flex items-center space-x-2 bg-slate-900/90 backdrop-blur-xl text-white px-4 py-2 rounded-2xl border border-white/10 shadow-2xl animate-in fade-in slide-in-from-bottom-4 duration-1000">
          <div className="flex space-x-1">
             <div className="w-1 h-1 bg-vibrant-mint rounded-full animate-pulse" />
             <div className="w-1 h-1 bg-vibrant-mint rounded-full animate-pulse delay-75" />
             <div className="w-1 h-1 bg-vibrant-mint rounded-full animate-pulse delay-150" />
          </div>
          <span className="text-[9px] uppercase tracking-widest font-bold opacity-80">
            Secure Node • HIPAA Compliant • AES-256
          </span>
        </div>
      </div>
    </div>
  );
};

const RateLimitBanner: React.FC = () => {
  const [active, setActive] = React.useState(false);

  React.useEffect(() => {
    const handler = (e: any) => setActive(e.detail.active);
    window.addEventListener('med-parser-rate-limit', handler);
    return () => window.removeEventListener('med-parser-rate-limit', handler);
  }, []);

  if (!active) return null;

  return (
    <div className="bg-health-red/10 border-b border-health-red/20 py-1.5 px-6 flex items-center justify-center space-x-2 animate-pulse overflow-hidden">
      <AlertTriangleIcon className="w-3.5 h-3.5 text-health-red" />
      <p className="text-[10px] font-bold text-health-red uppercase tracking-widest truncate">
        Traffic Surge Detected: System is rate limiting requests. Please wait...
      </p>
    </div>
  );
};
