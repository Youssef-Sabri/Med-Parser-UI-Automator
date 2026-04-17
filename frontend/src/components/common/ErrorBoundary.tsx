import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangleIcon, RefreshCwIcon } from 'lucide-react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
          <div className="max-w-md w-full bg-white rounded-3xl shadow-2xl shadow-slate-200 border border-slate-100 p-8 text-center space-y-6">
            <div className="w-20 h-20 bg-health-red/10 rounded-3xl flex items-center justify-center mx-auto">
              <AlertTriangleIcon className="w-10 h-10 text-health-red" />
            </div>
            
            <div className="space-y-2">
              <h2 className="text-2xl font-black text-slate-800 tracking-tight">System Interruption</h2>
              <p className="text-slate-500 text-sm font-medium">
                A non-critical component encountered an unexpected state. Clinical data remains secured.
              </p>
            </div>

            <div className="bg-slate-50 rounded-2xl p-4 text-left overflow-auto max-h-32">
              <code className="text-[10px] text-slate-400 font-mono leading-relaxed">
                {this.state.error?.message || 'Unknown system error'}
              </code>
            </div>

            <button 
              onClick={() => window.location.reload()}
              className="w-full flex items-center justify-center space-x-2 py-4 rounded-2xl bg-clinical-blue text-white font-black text-sm uppercase tracking-widest hover:bg-clinical-blue-hover transition-all active:scale-95 shadow-xl shadow-clinical-blue/20"
            >
              <RefreshCwIcon className="w-5 h-5" />
              <span>Recover Session</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
