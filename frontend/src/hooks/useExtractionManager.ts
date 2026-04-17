import { useState, useCallback } from 'react';
import { useExtraction } from './useExtraction';
import type { ExtractionResult } from '../types';
import { updatePrescriptionData } from '../services/api';

export const useExtractionManager = () => {
  const [activeExtraction, setActiveExtraction] = useState<ExtractionResult | null>(null);
  
  const { processImage, isProcessing, result, pollInjectionStatus } = useExtraction();

  const handleFileUpload = useCallback(async (file: File) => {
    await processImage(file);
  }, [processImage]);

  const trackExtraction = useCallback((newResult: ExtractionResult) => {
    setActiveExtraction(newResult);
  }, []);

  const updateExtractionStatus = useCallback((id: string, status: ExtractionResult['status']) => {
    setActiveExtraction(prev => 
      prev?.id === id ? { ...prev, status } : prev
    );
  }, []);

  const removeExtraction = useCallback((id: string) => {
    setActiveExtraction(prev => prev?.id === id ? null : prev);
  }, []);

  const saveCorrection = useCallback(async (id: string, data: any, flags: string[]) => {
    const result = await updatePrescriptionData(id, data, flags);
    setActiveExtraction(prev =>
      prev?.id === id ? { ...prev, data: result.data as any, flags: result.flags as string[] } : prev
    );
  }, []);

  return {
    activeExtraction,
    isProcessing,
    extractionResult: result,
    uploadFile: handleFileUpload,
    trackExtraction,
    updateExtractionStatus,
    removeExtraction,
    saveCorrection,
    pollInjectionStatus
  };
};
