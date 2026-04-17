import { useState, useCallback, useRef } from 'react';
import type { ExtractionResult, StatusType } from '../types';
import {
  uploadFaxImage,
  getExtractionResult,
  getExtractionStatus,
  DuplicateUploadError,
} from '../services/api';
import {
  MAX_STATUS_POLL_ATTEMPTS,
  STATUS_POLL_BACKOFF_FACTOR,
  INJECTION_POLL_INTERVAL_MS,
  INJECTION_MAX_ATTEMPTS,
  INJECTION_POLL_BACKOFF_FACTOR,
  INJECTION_POLL_MAX_DELAY_MS,
} from '../services/config';

export const useExtraction = () => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Polling controller
  const abortControllerRef = useRef<AbortController | null>(null);

  const processImage = useCallback(async (file: File) => {
    // Cancel existing
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const currentAbort = new AbortController();
    abortControllerRef.current = currentAbort;

    setIsProcessing(true);
    setResult(null);
    setError(null);

    try {
      const uploadRes = await uploadFaxImage(file);
      const extractionId = uploadRes.id;

      let isDone = false;
      let attempts = 0;

      while (!isDone && attempts < MAX_STATUS_POLL_ATTEMPTS) {
        if (currentAbort.signal.aborted) return;

        const statusRes = await getExtractionStatus(extractionId);
        if (statusRes.status === 'PROCESSED' || statusRes.status === 'DUPLICATE') {
          isDone = true;
        } else if (statusRes.status === 'FAILED' || statusRes.status === 'REJECTED') {
          throw new Error('Extraction stopped: ' + statusRes.status);
        } else {
          // Status backoff
          const delay = Math.min(2000 * Math.pow(STATUS_POLL_BACKOFF_FACTOR, attempts), 10000);
          await new Promise((resolve) => setTimeout(resolve, delay));
          attempts++;
        }
      }

      if (!isDone) {
        throw new Error('Extraction timed out. Large files may take up to 2 minutes. Please try again.');
      }

      if (currentAbort.signal.aborted) return;

      const extraction = await getExtractionResult(extractionId);
      setResult(extraction);
    } catch (err: unknown) {
      if (currentAbort.signal.aborted) return;

      // Load duplicate case
      if (err instanceof DuplicateUploadError && err.existing_id) {
        try {
          const existing = await getExtractionResult(err.existing_id);
          setResult(existing);
          setError('⚠️ Duplicate upload — showing previously processed case.');
          return;
        } catch {
          setError('Duplicate document detected, but the original case could not be loaded.');
          return;
        }
      }

      const message = err instanceof Error ? err.message : 'An error occurred during extraction.';
      setError(message);
    } finally {
      if (!currentAbort.signal.aborted) {
        setIsProcessing(false);
      }
    }
  }, []);

  // --- Load Result ---
  const loadResult = useCallback((data: ExtractionResult) => {
    // Check fields
    if (!data.id || !data.data || !Array.isArray(data.flags)) {
      setError('Invalid extraction result format');
      return;
    }
    setError(null);
    setResult(data);
  }, []);

  const pollInjectionStatus = useCallback(async (id: string, onComplete: (status: StatusType) => void) => {
    let attempts = 0;
    let isDone = false;
    let delay = INJECTION_POLL_INTERVAL_MS;

    while (!isDone && attempts < INJECTION_MAX_ATTEMPTS) {
      try {
        const res = await getExtractionStatus(id);
        if (['INJECTED', 'FAILED', 'PROCESSED', 'REJECTED', 'DUPLICATE'].includes(res.status)) {
          onComplete(res.status as StatusType); // Cast: API returns string, callback expects StatusType
          isDone = true;
        } else {
          // Injection backoff
          await new Promise(r => setTimeout(r, delay));
          delay = Math.min(delay * INJECTION_POLL_BACKOFF_FACTOR, INJECTION_POLL_MAX_DELAY_MS);
          attempts++;
        }
      } catch (e) {
        await new Promise(r => setTimeout(r, delay));
        delay = Math.min(delay * INJECTION_POLL_BACKOFF_FACTOR, INJECTION_POLL_MAX_DELAY_MS);
        attempts++;
      }
    }
  }, []);

  return {
    processImage,
    pollInjectionStatus,
    isProcessing,
    result,
    error,
    setResult: loadResult,
    loadResult,
  };
};
