import React, { useState, useEffect } from 'react';
import {
  PillIcon,
  Edit3Icon,
  XCircleIcon,
  EyeIcon,
  ArrowRightIcon,
  UserIcon,
  StethoscopeIcon,
  CalendarIcon,
  HashIcon,
  RefreshCw as RefreshCwIcon,
  CheckCircle2Icon,
  SaveIcon,
  DatabaseIcon,
  Loader2Icon
} from 'lucide-react';
import { postPharmacistAction } from '../../services/api';
import { getStatusIcon, getStatusColorClasses, getStatusLabel } from '../../utils/statusPresentation';
import { validateDEA, validateDate, validateDosage, validateQuantity, validateRefills } from '../../utils/validation';
import type { ExtractionResult, PrescriptionSchema, StatusType, PharmacistAction } from '../../types';
import { EditableField, SectionHeader, CDSSPanel } from './ExtractionSections';

interface ExtractionCardProps {
  id: string;
  data: PrescriptionSchema;
  flags: string[];
  onVerify: () => void;
  onRetry?: () => void;
  onReject: () => void;
  onSaveCorrection: (id: string, data: any, flags: string[]) => Promise<void>;
  status?: ExtractionResult['status'];
  retryError?: string | null;
  promptVersion?: string;
  pharmacistActions?: PharmacistAction[];
  rawText?: string;
}

export const ExtractionCard: React.FC<ExtractionCardProps> = ({
  id, data, flags, onVerify, onRetry, onReject, onSaveCorrection, status = 'PENDING', retryError, promptVersion, pharmacistActions = [], rawText
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<PrescriptionSchema>(data);
  const [note, setNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [uiError, setUiError] = useState<string | null>(null);
  const [isLocalRetrying, setIsLocalRetrying] = useState(false);
  const [showRawText, setShowRawText] = useState(false);

  useEffect(() => {
    if (!isEditing) setFormData(data);
  }, [data, isEditing]);

  // Reset local loading state when backend reporting updates
  useEffect(() => {
    if (status !== 'FAILED') {
      setIsLocalRetrying(false);
    }
  }, [status]);

  const handleFieldChange = (key: keyof PrescriptionSchema, val: string) => {
    setFormData(prev => ({
      ...prev,
      [key]: {
        ...prev[key],
        value: val,
        confidence: 100,
        reason: 'Manually corrected'
      }
    }));
  };

  const validateForm = (): boolean => {
    const errors: string[] = [];
    if (!formData.patient_name?.value?.trim()) errors.push("Patient Name is required.");
    if (!formData.drug_name?.value?.trim()) errors.push("Medication Name is required.");

    // Removed functional-dead DOB regex validation block

    if (errors.length > 0) {
      setUiError(errors.join(' '));
      return false;
    }
    return true;
  };

  const handleSave = async () => {
    setUiError(null);
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      await onSaveCorrection(id, formData, flags);
      setIsEditing(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err) {
      setUiError('Failed to persist corrections.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const isBlocking = flags.some(f => f.toUpperCase().includes('BLOCKING'));
  const isAIWorking = status === 'PROCESSING' || status === 'QUEUED' || isLocalRetrying;

  return (
    <div className={`flex flex-col h-[600px] w-full bg-slate-50 border-2 rounded-3xl overflow-hidden transition-all shadow-2xl ${isBlocking ? 'border-health-red' : 'border-slate-800'
      }`}>

      {/* Header */}
      <div className="bg-white p-4 border-b border-slate-100 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className={`w-10 h-10 ${isBlocking ? 'bg-health-red/10' : 'bg-clinical-blue/10'} rounded-2xl flex items-center justify-center shadow-inner`}>
            <PillIcon className={`w-6 h-6 ${isBlocking ? 'text-health-red' : 'text-clinical-blue'}`} />
          </div>
          <div>
            <h4 className="text-sm font-black text-slate-800 leading-none mb-1 uppercase">
              {isEditing ? 'Correction Mode' : 'Clinical Entry'}
            </h4>
            <div className="flex items-center space-x-2">
              <span className="text-[9px] text-slate-400 font-bold uppercase tracking-widest">Case: {id.split('-')[0]}</span>
              {promptVersion && (
                <>
                  <span className="text-[9px] text-slate-300">•</span>
                  <span className="text-[9px] text-slate-400 font-bold uppercase tracking-widest">Model: {promptVersion}</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {!isEditing && ['PENDING', 'PROCESSED', 'FAILED'].includes(status || '') && (
            <button
              onClick={() => setIsEditing(true)}
              className="p-2 text-slate-400 hover:text-clinical-blue rounded-xl transition-all"
              aria-label="Edit clinical entry"
            >
              <Edit3Icon className="w-4 h-4" />
            </button>
          )}
          <div
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-full border ${getStatusColorClasses(status as StatusType)}`}
            role="status"
            aria-label={`Status: ${getStatusLabel(status as StatusType)}`}
          >
            {getStatusIcon(status as StatusType, "w-3.5 h-3.5")}
            <span className="text-[10px] font-black uppercase tracking-widest">{getStatusLabel(status as StatusType)}</span>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide">
        <CDSSPanel flags={flags} isBlocking={isBlocking} />

        <div className="px-4 pb-2 flex justify-end">
          {rawText && (
            <button
              onClick={() => setShowRawText(!showRawText)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-[9px] font-black uppercase tracking-widest transition-colors ${showRawText ? 'bg-clinical-blue text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                }`}
              aria-label="Toggle Original OCR Text"
            >
              <EyeIcon className="w-3 h-3" />
              <span>{showRawText ? 'Show Structured Data' : 'View Original OCR Text'}</span>
            </button>
          )}
        </div>

        {showRawText ? (
          <div className="px-4 pb-6 animate-in fade-in zoom-in duration-300">
            <SectionHeader icon={EyeIcon} title="Raw AI Optical Character Extraction" />
            <div className="mt-3 bg-slate-800 text-slate-300 p-4 rounded-2xl font-mono text-[11px] leading-relaxed whitespace-pre-wrap shadow-inner overflow-x-auto">
              {rawText}
            </div>
          </div>
        ) : (
          <div className="p-4 pt-0 space-y-6 animate-in fade-in zoom-in duration-300">
            {/* Identity */}
            <div className="space-y-3">
              <SectionHeader icon={UserIcon} title="Patient Identity" />
              <div className="grid grid-cols-2 gap-4">
                <EditableField label="Patient Name" value={data.patient_name?.value} fieldKey="patient_name" isEditing={isEditing} formData={formData} handleFieldChange={handleFieldChange} />
                <EditableField label="Date of Birth" value={data.date_of_birth?.value} fieldKey="date_of_birth" icon={CalendarIcon} isEditing={isEditing} formData={formData} handleFieldChange={handleFieldChange} />
              </div>
            </div>

            {/* Medication */}
            <div className="space-y-3">
              <SectionHeader icon={PillIcon} title="Medication Details" />
              <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                <div className="col-span-2">
                  <EditableField label="Medication Name" value={data.drug_name?.value} fieldKey="drug_name" isEditing={isEditing} formData={formData} handleFieldChange={handleFieldChange} />
                </div>
                <EditableField label="Strength/Dosage" value={data.strength_dosage?.value} fieldKey="strength_dosage" isEditing={isEditing} formData={formData} handleFieldChange={handleFieldChange} />
                <EditableField label="Route of Admin" value={data.route?.value} fieldKey="route" isEditing={isEditing} formData={formData} handleFieldChange={handleFieldChange} />
                <EditableField label="Quantity" value={data.quantity?.value} fieldKey="quantity" isEditing={isEditing} formData={formData} handleFieldChange={handleFieldChange} />
                <EditableField label="Refills" value={data.refills?.value} fieldKey="refills" isEditing={isEditing} formData={formData} handleFieldChange={handleFieldChange} />
                <div className="col-span-2">
                  <EditableField label="Date Written" value={data.date_written?.value} fieldKey="date_written" icon={CalendarIcon} isEditing={isEditing} formData={formData} handleFieldChange={handleFieldChange} />
                </div>
              </div>
            </div>

            {/* Instructions */}
            <div className="space-y-3">
              <SectionHeader icon={ArrowRightIcon} title="Clinical Instructions" />
              <div className="col-span-2">
                {isEditing ? (
                  <textarea
                    value={formData.frequency?.value || ''}
                    onChange={e => handleFieldChange('frequency', e.target.value)}
                    className="w-full text-[11px] p-2 rounded bg-white border border-slate-200 outline-none"
                    rows={2}
                  />
                ) : (
                  <div className="bg-white border p-3 rounded-xl border-l-4 border-l-clinical-blue shadow-sm italic text-[13px] font-bold text-slate-700">
                    {data.frequency?.value ? `"${data.frequency.value}"` : 'No instructions detected.'}
                  </div>
                )}
              </div>
            </div>

            {/* Prescriber */}
            <div className="space-y-3">
              <SectionHeader icon={StethoscopeIcon} title="Prescriber Info" />
              <div className="grid grid-cols-2 gap-4">
                <EditableField label="Prescriber Name" value={data.prescriber_name?.value} fieldKey="prescriber_name" isEditing={isEditing} formData={formData} handleFieldChange={handleFieldChange} />
                <EditableField label="DEA / License" value={data.prescriber_dea?.value} fieldKey="prescriber_dea" icon={HashIcon} isEditing={isEditing} formData={formData} handleFieldChange={handleFieldChange} />
              </div>
            </div>

            {/* Audit Trail */}
            {pharmacistActions && pharmacistActions.length > 0 && (
              <div className="space-y-3 pt-4 border-t border-slate-100">
                <SectionHeader icon={DatabaseIcon} title="Clinical Audit Trail" />
                <div className="space-y-2">
                  {pharmacistActions.map((action, idx) => (
                    <div key={idx} className={`p-3 rounded-xl border text-[10px] ${action.action === 'APPROVED' ? 'bg-health-green/5 border-health-green/20' : 'bg-health-red/5 border-health-red/20'}`}>
                      <div className="flex justify-between items-center mb-1">
                        <span className={`font-black tracking-widest uppercase ${action.action === 'APPROVED' ? 'text-health-green' : 'text-health-red'}`}>
                          {action.action}
                        </span>
                        <span className="text-slate-400 font-bold">{new Date(action.timestamp).toLocaleString()}</span>
                      </div>
                      {action.pharmacist_note && (
                        <p className="text-slate-600 font-medium italic">"{action.pharmacist_note}"</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 bg-white border-t border-slate-100">
        {uiError && (
          <div className="mb-3 p-2 bg-health-red/5 border border-health-red/20 rounded-xl text-[10px] text-health-red font-bold flex items-center">
            <XCircleIcon className="w-3.5 h-3.5 mr-2" />
            {uiError}
          </div>
        )}
        {isEditing ? (
          <div className="flex space-x-2">
            <button
              onClick={handleSave}
              disabled={isSubmitting}
              className="flex-1 bg-clinical-blue text-white py-3 rounded-2xl font-black uppercase text-[10px] shadow-lg flex items-center justify-center"
              aria-label="Save corrections"
            >
              {isSubmitting ? <Loader2Icon className="w-4 h-4 animate-spin" /> : <><SaveIcon className="w-4 h-4 mr-2" />Save Changes</>}
            </button>
            <button
              onClick={() => setIsEditing(false)}
              className="px-6 bg-slate-100 text-slate-400 py-3 rounded-2xl font-black uppercase text-[10px]"
              aria-label="Cancel editing"
            >
              Cancel
            </button>
          </div>
        ) : status === 'INJECTED' ? (
          <div className="flex items-center justify-center p-3 bg-health-green/10 border border-health-green/20 rounded-2xl text-health-green font-black uppercase text-[10px] tracking-widest">
            <CheckCircle2Icon className="w-4 h-4 mr-2" />
            Document Injected Successfully
          </div>
        ) : isAIWorking ? (
          <div className="flex items-center justify-center p-3 bg-slate-100 border border-slate-200 rounded-2xl text-slate-400 font-bold italic text-[10px] tracking-widest">
            <Loader2Icon className="w-4 h-4 mr-2 animate-spin" />
            AI Extraction Engine Busy...
          </div>
        ) : status === 'FAILED' ? (
          <div className="flex space-x-2">
            <button
              onClick={() => {
                if (onRetry) {
                  setIsLocalRetrying(true);
                  onRetry();
                }
              }}
              className="flex-1 bg-health-red text-white py-3 rounded-2xl font-black uppercase text-[10px] shadow-lg flex items-center justify-center group"
              aria-label="Retry AI Extraction"
            >
              <RefreshCwIcon className="w-4 h-4 mr-2 group-hover:rotate-180 transition-transform duration-500" />
              Retry AI Extraction
            </button>
            {retryError && (
              <p className="mt-2 text-[9px] text-health-red font-bold text-center uppercase tracking-tight">
                ⚠️ {retryError}
              </p>
            )}
          </div>
        ) : (
          <div className="flex space-x-2">
            <button
              onClick={onVerify}
              disabled={isBlocking || status === 'INJECTING'}
              className={`flex-1 py-3 rounded-2xl font-black uppercase text-[10px] shadow-lg flex items-center justify-center transition-all ${isBlocking || status === 'INJECTING'
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  : 'bg-slate-800 text-white hover:bg-slate-900 group'
                }`}
              aria-label="Approve and Inject to PMS"
            >
              {status === 'INJECTING' ? (
                <Loader2Icon className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <DatabaseIcon className="w-4 h-4 mr-2 group-hover:scale-110 transition-transform" />
              )}
              {status === 'INJECTING' ? 'Processing...' : 'Approve & Inject'}
            </button>
            <button
              onClick={onReject}
              className="px-6 bg-health-red/10 text-health-red border border-health-red/20 py-3 rounded-2xl font-black uppercase text-[10px] hover:bg-health-red hover:text-white transition-all"
              aria-label="Reject prescription"
            >
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
