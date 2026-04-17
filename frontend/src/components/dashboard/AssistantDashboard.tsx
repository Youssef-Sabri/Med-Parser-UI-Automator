import React, { useEffect, useState } from 'react';
import { AppLayout } from '../layout/AppLayout';
import { ExtractionConsole } from '../chat/ExtractionConsole';
import { ExtractionCard } from '../chat/ExtractionCard';
import { useExtractionManager } from '../../hooks/useExtractionManager';
import { triggerInjection, getExtractionResult, retryExtraction, postPharmacistAction } from '../../services/api';
import { ClinicalStatsPanel } from './ClinicalStatsPanel';
import { ClinicalOpsFeed } from './ClinicalOpsFeed';
import { 
  Loader2Icon, 
  FileStackIcon, 
  ArrowUpRightIcon,
  MousePointer2Icon
} from 'lucide-react';

export const AssistantDashboard: React.FC = () => {
  const { 
    activeExtraction,
    isProcessing, 
    extractionResult, 
    uploadFile,
    trackExtraction,
    updateExtractionStatus,
    removeExtraction,
    pollInjectionStatus,
    saveCorrection
  } = useExtractionManager();

  const [isRateLimited, setIsRateLimited] = useState(false);
  const [injectionAlert, setInjectionAlert] = useState<string | null>(null);
  const [retryError, setRetryError] = useState<string | null>(null);

  // Handle New Extraction Result (Triggered after AI finishes)
  useEffect(() => {
    if (extractionResult && extractionResult.id) {
      trackExtraction(extractionResult);
    }
  }, [extractionResult, trackExtraction]);

  // Rate limit warning banner
  useEffect(() => {
    const handleRateLimit = (e: any) => setIsRateLimited(e.detail?.active === true);
    window.addEventListener('med-parser-rate-limit', handleRateLimit);
    return () => window.removeEventListener('med-parser-rate-limit', handleRateLimit);
  }, []);

  // Handle Workspace Management (Deselect/Remove/Focus)
  useEffect(() => {
    const handleRemove = (e: any) => removeExtraction(e.detail);
    window.addEventListener('med-parser-remove-card', handleRemove);

    const handleFocusAudit = async (e: any) => {
      const auditId = e.detail;
      if (!auditId) return;
      try {
        const res = await getExtractionResult(auditId);
        trackExtraction(res);
      } catch (err) {
        console.error("Failed to load historical audit record", err);
      }
    };
    window.addEventListener('focus-audit-id', handleFocusAudit);

    return () => {
      window.removeEventListener('med-parser-remove-card', handleRemove);
      window.removeEventListener('focus-audit-id', handleFocusAudit);
    };
  }, [removeExtraction, trackExtraction]);

  const isAnyInjecting = activeExtraction?.status === 'INJECTING';
  
  const handleRetryAI = async (id: string) => {
    try {
      setRetryError(null);
      updateExtractionStatus(id, 'QUEUED');
      await retryExtraction(id);
    } catch (err: any) {
      updateExtractionStatus(id, 'FAILED');
      setRetryError(err.message || 'AI Retry Failed');
      console.error('AI Retry Failed', err);
    }
  };

  return (
    <AppLayout>
      {isRateLimited && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[200] animate-in slide-in-from-top duration-300">
          <div className="flex items-center space-x-3 px-5 py-2.5 bg-caution-amber text-white rounded-xl shadow-lg text-xs font-bold">
            <span>⚠️ Rate limit reached — requests are being throttled. Please wait.</span>
          </div>
        </div>
      )}

      {injectionAlert && (
        <div className="fixed top-24 left-1/2 -translate-x-1/2 z-[250] animate-in zoom-in-95 fade-in duration-300">
          <div className="flex items-center justify-between p-4 bg-white border border-red-100 rounded-[20px] shadow-2xl shadow-red-500/10 min-w-[400px]">
            <div className="flex items-center space-x-4">
              <div className="flex items-center justify-center min-w-10 h-10 bg-red-50 text-health-red rounded-full text-lg">
                ⚠️
              </div>
              <div className="flex flex-col pr-4">
                <span className="text-[11px] font-black text-slate-800 uppercase tracking-widest pl-0.5">Injection Interrupted</span>
                <span className="text-[11px] font-semibold text-slate-500 leading-snug mt-1 pl-0.5">{injectionAlert}</span>
              </div>
            </div>
            <button 
              onClick={() => setInjectionAlert(null)}
              className="px-4 py-2 bg-slate-100 text-slate-600 rounded-xl text-[10px] font-black tracking-wider uppercase hover:bg-slate-200 transition-colors"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}
      {isAnyInjecting && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-[100] animate-in slide-in-from-top duration-500">
           <div className="flex items-center space-x-3 px-6 py-3 bg-clinical-blue text-white rounded-2xl shadow-2xl shadow-clinical-blue/40 border border-white/20">
              <Loader2Icon className="w-4 h-4 animate-spin" />
              <div className="flex flex-col">
                 <span className="text-[10px] font-black uppercase tracking-widest leading-none mb-0.5">Live Automation Sequence</span>
                 <span className="text-[8px] font-bold opacity-80 uppercase tracking-tight">Active Pulse Synchronization in progress...</span>
              </div>
           </div>
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-full min-h-[600px]">
        {/* Main Document Workspace (Takes 3/4 on large screens for better focus) */}
        <div className="lg:col-span-3 flex flex-col h-full">
          <ExtractionConsole 
            onUpload={uploadFile} 
            disabled={isProcessing}
          >
            <div className="space-y-4">
              {activeExtraction && (
                <ExtractionCard 
                  key={activeExtraction.id}
                  id={activeExtraction.id}
                  data={activeExtraction.data}
                  flags={activeExtraction.flags || []}
                  status={activeExtraction.status}
                  promptVersion={activeExtraction.prompt_version}
                  pharmacistActions={activeExtraction.pharmacist_actions}
                  rawText={activeExtraction.raw_text}
                  onSaveCorrection={(id, data, flags) => saveCorrection(id, data, flags)}
                  onReject={async () => {
                    try {
                      await postPharmacistAction(activeExtraction.id, 'REJECTED', '');
                    } catch (err) {
                      console.error('Failed to record rejection on backend', err);
                    } finally {
                      removeExtraction(activeExtraction.id);
                    }
                  }}
                  onRetry={() => handleRetryAI(activeExtraction.id)}
                  retryError={retryError}
                  onVerify={async () => {
                    try {
                      updateExtractionStatus(activeExtraction.id, 'INJECTING');
                      await triggerInjection(activeExtraction.id);
                      
                      pollInjectionStatus(activeExtraction.id, (finalStatus) => {
                        updateExtractionStatus(activeExtraction.id, finalStatus as any);
                        
                        // If it fell back to PROCESSED, the bot encountered an error
                        if (finalStatus === 'PROCESSED') {
                          setInjectionAlert("The bot encountered an issue or was safely stopped. No data was lost and the record is ready to be retried.");
                        }
                      });
                    } catch (err: any) {
                      updateExtractionStatus(activeExtraction.id, 'FAILED');
                      console.error('RPA Trigger Failed', err);
                    }
                  }}
                />
              )}

              {!activeExtraction && !isProcessing && (
                <div className="flex flex-col items-center justify-center p-20 bg-slate-50/30 rounded-[40px] border border-dashed border-slate-200/60 animate-in fade-in zoom-in duration-700">
                  <div className="relative mb-8">
                    <div className="absolute inset-0 bg-clinical-blue/5 rounded-full scale-150 animate-pulse" />
                    <div className="relative w-20 h-20 bg-white rounded-3xl shadow-xl border border-slate-100 flex items-center justify-center">
                      <FileStackIcon className="w-10 h-10 text-slate-300" />
                    </div>
                    <div className="absolute -bottom-2 -right-2 w-8 h-8 bg-clinical-blue text-white rounded-full flex items-center justify-center shadow-lg border-2 border-white animate-bounce">
                       <MousePointer2Icon className="w-4 h-4" />
                    </div>
                  </div>
                  <h3 className="text-sm font-black text-slate-800 uppercase tracking-widest mb-2">Ready for Clinical Audit</h3>
                  <p className="text-[11px] text-slate-400 font-bold max-w-xs text-center leading-relaxed uppercase tracking-tight">
                    Select a queued record from the feed or upload a new prescription fax to begin verification.
                  </p>
                  <div className="mt-8 flex items-center space-x-2 text-[9px] font-black text-clinical-blue uppercase tracking-widest opacity-40">
                     <span>Waiting for Selection</span>
                     <div className="flex space-x-1">
                        <div className="w-1 h-1 bg-clinical-blue rounded-full animate-pulse" />
                        <div className="w-1 h-1 bg-clinical-blue rounded-full animate-pulse [animation-delay:200ms]" />
                        <div className="w-1 h-1 bg-clinical-blue rounded-full animate-pulse [animation-delay:400ms]" />
                     </div>
                  </div>
                </div>
              )}
              
              {isProcessing && (
                <div className="p-12 flex flex-col items-center justify-center space-y-4 bg-slate-50/50 rounded-3xl border border-dashed border-slate-200">
                  <div className="flex space-x-2">
                    <div className="w-3 h-3 bg-clinical-blue rounded-full animate-bounce [animation-delay:-0.3s]" />
                    <div className="w-3 h-3 bg-clinical-blue rounded-full animate-bounce [animation-delay:-0.15s]" />
                    <div className="w-3 h-3 bg-clinical-blue rounded-full animate-bounce" />
                  </div>
                  <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">AI Extraction in Progress...</p>
                </div>
              )}
            </div>
          </ExtractionConsole>
        </div>

        {/* Right Col: Dashboard Context & Monitoring */}
        <div className="hidden lg:flex flex-col space-y-6">
          <ClinicalStatsPanel />
          <div className="flex-1 min-h-0">
            <ClinicalOpsFeed 
              onItemClick={async (id) => {
                try {
                  const res = await getExtractionResult(id);
                  trackExtraction(res);
                } catch (err) {
                  console.error("Failed to load queued item", err);
                }
              }} 
            />
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
