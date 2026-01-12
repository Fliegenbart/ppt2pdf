import { useState, useCallback } from 'react';
import axios from 'axios';
import { Job, Slide, AccessibilityReport, ElementUpdate } from '../types';

const API_BASE = '/api';

export function useConversion() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [slides, setSlides] = useState<Slide[]>([]);
  const [report, setReport] = useState<AccessibilityReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uploadFile = useCallback(async (file: File) => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_BASE}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setJobId(response.data.job_id);
      return response.data.job_id;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Upload failed';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchJobStatus = useCallback(async (id: string) => {
    try {
      const response = await axios.get(`${API_BASE}/job/${id}`);
      setJob(response.data);
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch job status';
      setError(message);
      throw err;
    }
  }, []);

  const startAnalysis = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);

    try {
      await axios.post(`${API_BASE}/analyze`, {
        job_id: id,
        generate_alt_text: true,
        analyze_reading_order: true,
        check_contrast: true,
        detect_languages: true,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Analysis failed';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchSlides = useCallback(async (id: string) => {
    try {
      const response = await axios.get(`${API_BASE}/job/${id}/slides`);
      setSlides(response.data.slides);
      return response.data.slides;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch slides';
      setError(message);
      throw err;
    }
  }, []);

  const fetchReport = useCallback(async (id: string) => {
    try {
      const response = await axios.get(`${API_BASE}/job/${id}/report`);
      setReport(response.data);
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch report';
      setError(message);
      throw err;
    }
  }, []);

  const updateElements = useCallback(async (id: string, updates: ElementUpdate[]) => {
    try {
      await axios.post(`${API_BASE}/job/${id}/update`, {
        job_id: id,
        updates,
      });
      // Refresh slides after update
      await fetchSlides(id);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update elements';
      setError(message);
      throw err;
    }
  }, [fetchSlides]);

  const startConversion = useCallback(async (id: string, includeSpeakerNotes: boolean = false) => {
    setLoading(true);
    setError(null);

    try {
      await axios.post(`${API_BASE}/convert`, {
        job_id: id,
        include_speaker_notes: includeSpeakerNotes,
        pdf_ua_compliant: true,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Conversion failed';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const downloadPdf = useCallback((id: string) => {
    window.open(`${API_BASE}/download/${id}`, '_blank');
  }, []);

  const getElementImage = useCallback(async (id: string, elementId: string) => {
    try {
      const response = await axios.get(`${API_BASE}/job/${id}/element/${elementId}/image`);
      return response.data.image_base64;
    } catch {
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    setJobId(null);
    setJob(null);
    setSlides([]);
    setReport(null);
    setError(null);
  }, []);

  return {
    jobId,
    job,
    slides,
    report,
    loading,
    error,
    uploadFile,
    fetchJobStatus,
    startAnalysis,
    fetchSlides,
    fetchReport,
    updateElements,
    startConversion,
    downloadPdf,
    getElementImage,
    reset,
  };
}
