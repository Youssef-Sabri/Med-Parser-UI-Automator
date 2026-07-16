export type StatusType = 'PENDING' | 'QUEUED' | 'PROCESSING' | 'PROCESSED' | 'FAILED' | 'INJECTING' | 'INJECTED' | 'REJECTED' | 'DUPLICATE';

export interface FieldExtraction {
  value: string | null;
  confidence: number;
  reason?: string;
}

export interface PrescriptionSchema {
  patient_name: FieldExtraction;
  date_of_birth: FieldExtraction;
  drug_name: FieldExtraction;
  strength_dosage: FieldExtraction;
  route: FieldExtraction;
  frequency: FieldExtraction;
  quantity: FieldExtraction;
  refills: FieldExtraction;
  date_written: FieldExtraction;
  prescriber_name: FieldExtraction;
  prescriber_dea: FieldExtraction;
}

export interface PharmacistAction {
  action: 'APPROVED' | 'REJECTED';
  pharmacist_note: string;
  timestamp: string;
}

export interface ExtractionResult {
  id: string;
  filename: string;
  raw_text: string;
  data: PrescriptionSchema;
  flags: string[];
  prompt_version?: string;
  created_at: string;
  status: StatusType;
  pharmacist_actions?: PharmacistAction[];
}

export interface AuditLogEntry {
  id: string;
  filename: string;
  flags: string[];
  created_at: string;
  status?: string;
}

export interface Stats {
  scripts_today: number;
  total_processed: number;
  approval_rate: number;
  blocking_count: number;
  total_decisions: number;
  total_records: number;
  total_capacity: number;
  daily_capacity: number;
}
