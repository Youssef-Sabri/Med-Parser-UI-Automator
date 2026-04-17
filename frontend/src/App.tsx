import { AssistantDashboard } from './components/dashboard/AssistantDashboard';
import { AlertCircleIcon } from 'lucide-react';

function App() {
  const missingBaseUrl = !import.meta.env.VITE_API_BASE_URL;
  const missingApiKey = !import.meta.env.VITE_MED_PARSER_API_KEY;

  if (missingBaseUrl || missingApiKey) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white border border-health-red/20 rounded-xl p-6 shadow-sm flex flex-col items-center text-center space-y-4">
          <div className="w-12 h-12 bg-health-red/10 rounded-full flex items-center justify-center">
            <AlertCircleIcon className="w-6 h-6 text-health-red" />
          </div>
          <h2 className="text-lg font-bold text-slate-800">Configuration Error</h2>
          <p className="text-slate-600 text-sm">
            The dashboard cannot start because critical API configuration is missing.
          </p>
          <div className="bg-slate-50 rounded-lg p-3 w-full text-left font-mono text-xs text-slate-500 space-y-1">
            <div>VITE_API_BASE_URL: {missingBaseUrl ? '❌ Missing' : '✅ OK'}</div>
            <div>VITE_MED_PARSER_API_KEY: {missingApiKey ? '❌ Missing' : '✅ OK'}</div>
          </div>
          <p className="text-slate-500 text-xs mt-4">
            Please check your .env file and restart the development server.
          </p>
        </div>
      </div>
    );
  }

  return (
    <AssistantDashboard />
  );
}

export default App;
