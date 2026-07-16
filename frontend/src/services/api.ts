import type { AuditLogEntry, ExtractionResult, PrescriptionSchema, Stats } from '../types';
import {
  API_TIMEOUT_MS,
  MAX_RETRIES,
  EVENT_RATE_LIMIT_START,
  EVENT_RATE_LIMIT_END,
} from './config';

// --- Errors ---
export class DuplicateUploadError extends Error {
  existing_id?: string;

  constructor(message: string, existing_id?: string) {
    super(message);
    this.name = 'DuplicateUploadError';
    this.existing_id = existing_id;
  }
}

const API_BASE = import.meta.env.VITE_API_BASE_URL;
const API_KEY = import.meta.env.VITE_MED_PARSER_API_KEY;

// --- Config ---
if (!API_BASE) console.error('[API] VITE_API_BASE_URL is not configured');
if (!API_KEY) console.error('[API] VITE_MED_PARSER_API_KEY is not configured');

const getHeaders = (extra: Record<string, string> = {}) => ({
  'X-API-KEY': API_KEY || '',
  ...extra,
});

/** Fetch wrapper with timeout. */
async function fetchWithTimeout(url: string, init?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

/** Fetch with retry. */
async function fetchWithRetry(url: string, init?: RequestInit, retries = MAX_RETRIES): Promise<Response> {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetchWithTimeout(url, init);
      // Handle Rate Limits (429) specifically
      if (res.status === 429) {
        window.dispatchEvent(new CustomEvent(EVENT_RATE_LIMIT_START, { detail: { active: true } }));
        if (i < retries - 1) {
            await new Promise(resolve => setTimeout(resolve, 5000)); // 5s wait for rate limit
            continue;
        }
        return res;
      }
      if (res.ok || res.status < 500) {
        window.dispatchEvent(new CustomEvent(EVENT_RATE_LIMIT_END, { detail: { active: false } }));
        return res;
      }

      // Server error (5xx) - retry with exponential backoff
      if (i < retries - 1) {
        const delay = Math.pow(2, i) * 1000; // 1s, 2s, 4s
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    } catch (err) {
      // Network error - retry
      if (i < retries - 1) {
        const delay = Math.pow(2, i) * 1000;
        await new Promise(resolve => setTimeout(resolve, delay));
      } else {
        throw err;
      }
    }
  }
  throw new Error('Max retries exceeded');
}

export const uploadFaxImage = async (
  file: File,
): Promise<{ id: string; status: string; existing_id?: string }> => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetchWithRetry(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
    headers: getHeaders(),
  });
  if (!res.ok) {
    if (res.status === 409) {
      const body = await res.json();
      const detail = body.detail || {};
      throw new DuplicateUploadError(
        detail.message || 'This prescription has already been processed.',
        detail.existing_case_id,
      );
    }
    throw new Error('Failed to upload image');
  }
  return res.json();
};

export const getExtractionStatus = async (
  id: string,
): Promise<{ id: string; status: string }> => {
  const res = await fetchWithRetry(`${API_BASE}/prescriptions/${id}/status`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch extraction status');
  return res.json();
};

export const getExtractionResult = async (
  id: string,
): Promise<ExtractionResult> => {
  const res = await fetchWithRetry(`${API_BASE}/prescriptions/${id}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch extraction result');
  return res.json();
};

export const getAuditLog = async (limit = 10, q?: string): Promise<AuditLogEntry[]> => {
  const res = await fetchWithRetry(`${API_BASE}/audit?limit=${limit}${q ? `&q=${q}` : ''}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch audit log');
  return res.json();
};

export const updatePrescriptionData = async (
  id: string,
  data: PrescriptionSchema,
  flags: string[],
): Promise<Record<string, unknown>> => {
  const res = await fetchWithRetry(`${API_BASE}/prescriptions/${id}`, {
    method: 'PUT',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ data, flags }),
  });
  if (!res.ok) throw new Error('Failed to update prescription data');
  return res.json();
};

export const postPharmacistAction = async (
  id: string,
  action: 'APPROVED' | 'REJECTED',
  note = '',
): Promise<{ status: string }> => {
  const res = await fetchWithRetry(`${API_BASE}/prescriptions/${id}/action`, {
    method: 'POST',
    headers: getHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ action, note }),
  });
  if (!res.ok) throw new Error('Failed to record pharmacist action');
  return res.json();
};

export const getStats = async (): Promise<Stats> => {
  const res = await fetchWithRetry(`${API_BASE}/stats`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
};


export const getQueue = async (
  limit = 50,
  q?: string,
): Promise<
  {
    id: string;
    filename: string;
    status: string;
    flags: string[];
    created_at: string;
  }[]
> => {
  const res = await fetchWithRetry(`${API_BASE}/queue?limit=${limit}${q ? `&q=${q}` : ''}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch queue');
  return res.json();
};

export const triggerInjection = async (id: string): Promise<{ status: string }> => {
  const res = await fetchWithRetry(`${API_BASE}/automation/inject/${id}`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Failed to trigger automation bot');
  return res.json();
};

export const getAgentHealth = async (): Promise<{ status: string }> => {
  // Health checks
  // Avoid browser caching
  const agentBase = import.meta.env.VITE_AGENT_BASE_URL || 'http://localhost:8001';
  const agentApiKey = import.meta.env.VITE_AGENT_API_KEY || '';
  try {
    const res = await fetch(`${agentBase}/health?t=${Date.now()}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        ...(agentApiKey ? { 'X-API-KEY': agentApiKey } : {}),
      },
    });
    if (!res.ok) return { status: 'offline' };
    return res.json();
  } catch (err) {
    return { status: 'offline' };
  }
};

export const getBackendHealth = async (): Promise<{ status: string }> => {
  // Backend health check
  try {
    const rootUrl = API_BASE.replace('/api/v1', '');
    const res = await fetch(`${rootUrl}/health?t=${Date.now()}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) return { status: 'offline' };
    return res.json();
  } catch (err) {
    return { status: 'offline' };
  }
};

export const retryExtraction = async (id: string): Promise<{ id: string; status: string }> => {
  const res = await fetchWithRetry(`${API_BASE}/prescriptions/${id}/retry`, {
    method: 'POST',
    headers: getHeaders(),
  });
  if (!res.ok) {
    if (res.status === 410) throw new Error('Source document purged for privacy. Please re-upload.');
    throw new Error('Failed to re-trigger extraction');
  }
  return res.json();
};
