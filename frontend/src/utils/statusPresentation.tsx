import { 
  CheckCircle2Icon, 
  AlertCircleIcon, 
  Loader2Icon, 
  ClockIcon,
  DatabaseIcon
} from 'lucide-react';

import { type StatusType } from '../types';

export const getStatusIcon = (status: StatusType, className = "w-3 h-3") => {
  switch (status) {
    case 'PROCESSED':
    case 'INJECTED': 
      return <div className="p-0.5 bg-vibrant-mint/20 rounded-md"><CheckCircle2Icon className={`${className} text-vibrant-mint`} /></div>;
    case 'FAILED': 
    case 'REJECTED':
      return <div className="p-0.5 bg-health-red/20 rounded-md"><AlertCircleIcon className={`${className} text-health-red`} /></div>;
    case 'PROCESSING':
    case 'INJECTING':
      return <div className="p-0.5 bg-clinical-blue/20 rounded-md"><Loader2Icon className={`${className} text-clinical-blue animate-spin`} /></div>;
    case 'QUEUED':
    case 'PENDING':
      return <div className="p-0.5 bg-caution-amber/20 rounded-md"><ClockIcon className={`${className} text-caution-amber`} /></div>;
    case 'DUPLICATE':
      return <div className="p-0.5 bg-caution-amber/20 rounded-md"><DatabaseIcon className={`${className} text-caution-amber`} /></div>;
    default: 
      return <div className="p-0.5 bg-slate-100 rounded-md"><ClockIcon className={`${className} text-slate-400`} /></div>;
  }
};

export const getStatusColorClasses = (status: StatusType) => {
  switch (status) {
    case 'PROCESSED':
    case 'INJECTED':
      return 'text-vibrant-mint bg-vibrant-mint/5 border-vibrant-mint/10';
    case 'FAILED':
    case 'REJECTED':
      return 'text-health-red bg-health-red/5 border-health-red/10';
    case 'PROCESSING':
    case 'INJECTING':
      return 'text-clinical-blue bg-clinical-blue/5 border-clinical-blue/10 animate-pulse';
    case 'QUEUED':
    case 'PENDING':
    case 'DUPLICATE':
      return 'text-caution-amber bg-caution-amber/5 border-caution-amber/10';
    default:
      return 'text-slate-400 bg-slate-50 border-slate-100';
  }
};

export const getStatusLabel = (status: StatusType) => {
  switch (status) {
    case 'INJECTED': return 'Stored';
    case 'INJECTING': return 'Injecting';
    case 'PROCESSED': return 'Verified';
    case 'FAILED': return 'Failed';
    case 'PROCESSING': return 'Processing';
    case 'QUEUED': return 'Queued';
    case 'PENDING': return 'Pending';
    case 'REJECTED': return 'Rejected';
    case 'DUPLICATE': return 'Duplicate';
    default: return status;
  }
};
