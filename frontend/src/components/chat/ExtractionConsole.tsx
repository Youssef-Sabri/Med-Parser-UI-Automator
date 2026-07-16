import React from 'react';
import { FileUp, Search } from 'lucide-react';
interface ExtractionConsoleProps {
  children: React.ReactNode;
  onUpload: (file: File) => void;
  disabled?: boolean;
}

const MAX_FILE_SIZE_MB = 10;

export const ExtractionConsole: React.FC<ExtractionConsoleProps> = ({ children, onUpload, disabled }) => {
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
        alert(`File too large. Maximum size is ${MAX_FILE_SIZE_MB}MB.`);
        return;
      }
      onUpload(file);
    }
  };

  // Support for custom trigger event
  React.useEffect(() => {
    const handleTrigger = () => fileInputRef.current?.click();
    window.addEventListener('trigger-file-picker', handleTrigger);
    return () => window.removeEventListener('trigger-file-picker', handleTrigger);
  }, []);

  const [sessionId] = React.useState(() => Math.random().toString(36).slice(2, 8).toUpperCase());

  const sanitizeQuery = (value: string): string => {
    return value.replace(/[<>"'&]/g, '').slice(0, 100);
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-3xl border border-clinical-border shadow-sm overflow-hidden">
      {/* Header / Search Bar */}
      <div className="p-4 border-b border-clinical-border bg-slate-50/50 flex items-center justify-between">
        <div className="flex items-center space-x-2 text-slate-800">
          <FileUp className="w-5 h-5 text-clinical-blue" />
          <h2 className="font-bold text-sm tracking-tight">Active Extraction Workspace</h2>
        </div>
        
        {/* Real-time Search Integration */}
        <div className="relative group">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <Search className="w-3.5 h-3.5 text-slate-400 group-focus-within:text-clinical-blue transition-colors" />
          </div>
          <input 
            type="text"
            placeholder="Search patient or drug..."
            onChange={(e) => {
              window.dispatchEvent(new CustomEvent('ops-feed-search', { 
                detail: { query: sanitizeQuery(e.target.value) } 
              }));
            }}
            className="pl-9 pr-4 py-1.5 bg-white border border-slate-200 rounded-lg text-[11px] focus:outline-none focus:ring-2 focus:ring-clinical-blue/20 focus:border-clinical-blue transition-all w-48 shadow-inner"
          />
        </div>
      </div>
      {/* Main Workspace Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-slate-200">
        <input 
          type="file" 
          ref={fileInputRef} 
          className="hidden" 
          onChange={handleFileChange}
          accept="image/png,image/jpeg,image/tiff,application/pdf"
        />
        
        {React.Children.count(children) === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-60">
            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center border border-dashed border-slate-300">
              <FileUp className="w-8 h-8 text-slate-400" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-600">No Active Extractions</p>
              <p className="text-xs text-slate-400 max-w-[200px] mt-1">Upload a prescription to begin clinical data extraction.</p>
            </div>
            <button 
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
              className="px-6 py-2 bg-clinical-blue text-white rounded-xl text-xs font-bold shadow-lg shadow-clinical-blue/20 hover:bg-clinical-blue-hover transition-all"
            >
              Upload Document
            </button>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto w-full space-y-4">
            {children}
          </div>
        )}
      </div>

      {/* Breadcrumbs / Footer Stats */}
      <div className="p-3 border-t border-clinical-border bg-slate-50/30 flex items-center justify-between text-[10px] text-slate-400 font-medium px-6">
        <div className="flex items-center space-x-4">
          <span>Active Session ID: {sessionId}</span>
          <span>•</span>
          <span>Ready for PMS Injection</span>
        </div>
        <div className="flex items-center space-x-2">
        </div>
      </div>
    </div>
  );
};
