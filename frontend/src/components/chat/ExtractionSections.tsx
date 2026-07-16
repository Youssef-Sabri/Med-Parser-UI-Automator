import React from 'react';
import {
  AlertCircleIcon,
  HistoryIcon
} from 'lucide-react';
import type { PrescriptionSchema } from '../../types';

// ── Types ────────────────────────────────────────────────────────────────────

interface ValidationResult {
  valid: boolean;
  error?: string;
}

interface FieldProps {
  label: string;
  value: string | null;
  fieldKey: keyof PrescriptionSchema;
  icon?: React.ComponentType<{ className?: string }>;
  isEditing: boolean;
  formData: Partial<PrescriptionSchema>;
  handleFieldChange: (key: keyof PrescriptionSchema, val: string) => void;
  validate?: (value: string) => ValidationResult;
}

// ── EditableField ─────────────────────────────────────────────────────────────

export const EditableField = ({
  label, value, fieldKey, icon: Icon, isEditing, formData, handleFieldChange, validate
}: FieldProps) => {
  const field = formData[fieldKey];
  // Safely read confidence — field may be undefined or a raw string (legacy shape)
  const confidence: number | undefined =
    field && typeof field === 'object' ? field.confidence : undefined;

  const showConfidence = confidence !== undefined && confidence !== null;
  // Guard: only compare when we have a real number so we never get `undefined < 80`
  const isLowConfidence = showConfidence && (confidence as number) < 80;

  // Safely read the editable value from the FieldExtraction object
  const editableValue: string =
    field && typeof field === 'object'
      ? (field.value ?? '')
      : (typeof field === 'string' ? field : '');

  // validate() returns { valid, error? } — extract the error string separately
  const validationResult: ValidationResult | null =
    isEditing && validate ? validate(editableValue) : null;
  const validationError: string | undefined =
    validationResult && !validationResult.valid ? validationResult.error : undefined;

  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-1.5 opacity-60">
          {Icon && <Icon className="w-2.5 h-2.5" />}
          <label className="text-[8px] font-black uppercase tracking-widest">{label}</label>
        </div>
        {showConfidence && value && (
          <span
            title={
              field && typeof field === 'object' && field.reason
                ? field.reason
                : `AI Confidence: ${confidence}%`
            }
            className={`text-[7px] px-1.5 py-0.5 rounded-sm font-bold tracking-widest uppercase cursor-help transition-all ${
              isLowConfidence
                ? 'bg-amber-100 text-amber-600 hover:bg-amber-200'
                : 'bg-health-green/10 text-health-green hover:bg-health-green/20'
            }`}
          >
            {confidence}% Conf
          </span>
        )}
      </div>

      {isEditing ? (
        <div className="space-y-1">
          <input
            value={editableValue}
            onChange={e => handleFieldChange(fieldKey, e.target.value)}
            className={`w-full text-[11px] h-8 px-2 rounded-lg bg-white border focus:ring-1 outline-none transition-all shadow-inner ${
              validationError
                ? 'border-health-red focus:ring-health-red'
                : 'border-slate-200 focus:ring-clinical-blue'
            }`}
          />
          {/* Render the error *string*, not the whole ValidationResult object */}
          {validationError && (
            <p className="text-[9px] text-health-red font-medium">{validationError}</p>
          )}
        </div>
      ) : (
        <p className={`text-[12px] font-bold leading-tight ${value ? 'text-slate-800' : 'text-slate-300 italic'}`}>
          {value || 'Not detected'}
        </p>
      )}
    </div>
  );
};

// ── SectionHeader ─────────────────────────────────────────────────────────────

export const SectionHeader = ({
  icon: Icon,
  title,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
}) => (
  <div className="flex items-center space-x-2 pb-1 border-b border-slate-200/50">
    <Icon className="w-3 h-3 text-slate-400" />
    <h5 className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{title}</h5>
  </div>
);

// ── CDSSPanel ─────────────────────────────────────────────────────────────────

export const CDSSPanel = ({ flags, isBlocking }: { flags: string[]; isBlocking: boolean }) => {
  if (flags.length === 0) return null;

  return (
    <div
      className={`rounded-2xl p-4 mx-4 mb-4 flex items-start space-x-4 border shadow-sm ${
        isBlocking ? 'bg-health-red/5 border-health-red/10' : 'bg-caution-amber/5 border-caution-amber/10'
      }`}
    >
      <div className={`p-2 rounded-xl h-fit ${isBlocking ? 'bg-health-red/10' : 'bg-caution-amber/10'}`}>
        <AlertCircleIcon
          className={`w-5 h-5 flex-shrink-0 ${isBlocking ? 'text-health-red' : 'text-caution-amber'}`}
        />
      </div>
      <div className="space-y-1.5 flex-1">
        <p className={`text-[10px] font-black uppercase tracking-widest ${isBlocking ? 'text-health-red' : 'text-caution-amber'}`}>
          {isBlocking ? 'Blocking Safety Violation' : 'Clinical Decision Support'}
        </p>
        <div className="flex flex-wrap gap-2">
          {flags.map((flag, i) => {
            const caseId = flag.match(/matches Case ([a-zA-Z0-9-]+)/)?.[1];
            return (
              <div key={i} className="flex items-center space-x-2 group">
                <span
                  className={`text-[9px] px-2.5 py-1 rounded-lg border font-black uppercase tracking-tighter transition-all ${
                    flag.toUpperCase().includes('BLOCKING')
                      ? 'bg-health-red text-white border-health-red shadow-sm'
                      : flag.toUpperCase().includes('ADVISORY')
                        ? 'bg-amber-100/50 text-amber-700 border-amber-200'
                        : 'bg-white text-slate-600 border-slate-100'
                  }`}
                >
                  {flag.replace('BLOCKING: ', '').replace('ADVISORY: ', '')}
                </span>
                {caseId && (
                  <button
                    onClick={() =>
                      window.dispatchEvent(new CustomEvent('focus-audit-id', { detail: caseId }))
                    }
                    className="p-1 hover:bg-slate-200 bg-white rounded-md border border-slate-100 transition-colors shadow-sm"
                    aria-label={`Jump to audit ${caseId}`}
                  >
                    <HistoryIcon className="w-3 h-3 text-slate-400" />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
