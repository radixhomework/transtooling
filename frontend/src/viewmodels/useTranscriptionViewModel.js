import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import * as jobsApi from "../models/jobs";
import * as modelsApi from "../models/whisperModels";

const POLL_INTERVAL_MS = 4000;

/**
 * ViewModel for the transcription dashboard: exposes the observable state
 * (jobs, enabled models, upload progress) and the actions operating on it.
 * The view only renders this state and triggers the actions.
 */
export function useTranscriptionViewModel() {
  const { t } = useTranslation();
  const [jobs, setJobs] = useState([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [uploadError, setUploadError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [enabledModels, setEnabledModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const fileInputRef = useRef(null);
  const pollRef = useRef(null);

  const fetchJobs = useCallback(async () => {
    try {
      const data = await jobsApi.listJobs();
      data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setJobs(data);
    } catch {
      // Silent failure on periodic polling: we do not want to
      // interrupt the user for a transient network failure.
    } finally {
      setIsLoadingJobs(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  useEffect(() => {
    // Models offered for upload (selector): displayed only when there are
    // several; the default model covers the simple case.
    modelsApi
      .listEnabledModels()
      .then((models) => setEnabledModels(models))
      .catch(() => setEnabledModels([]));
  }, []);

  useEffect(() => {
    const hasActiveJob = jobs.some(
      (j) => j.status === "pending" || j.status === "processing" || j.status === "cancelling"
    );
    if (hasActiveJob) {
      pollRef.current = setInterval(fetchJobs, POLL_INTERVAL_MS);
      return () => clearInterval(pollRef.current);
    }
  }, [jobs, fetchJobs]);

  const uploadFile = useCallback(
    async (file) => {
      if (!file) return;

      setUploadError(null);
      setIsUploading(true);
      setUploadProgress(0);

      try {
        await jobsApi.createJob(
          file,
          (progressEvent) => {
            if (progressEvent.total) {
              setUploadProgress(Math.round((progressEvent.loaded / progressEvent.total) * 100));
            }
          },
          selectedModel || undefined
        );
        await fetchJobs();
      } catch (err) {
        const detail = err.response?.data?.detail;
        setUploadError(detail || t("dashboard.errorUpload"));
      } finally {
        setIsUploading(false);
        setUploadProgress(0);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    },
    [fetchJobs, selectedModel, t]
  );

  const cancelJob = useCallback(
    async (job) => {
      try {
        await jobsApi.cancelJob(job.id);
        await fetchJobs();
      } catch {
        setUploadError(t("dashboard.errorCancel"));
      }
    },
    [fetchJobs, t]
  );

  const downloadJob = useCallback(
    async (job, format) => {
      try {
        const blob = await jobsApi.downloadJobUrl(job.id, format);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        const baseName = job.filename_original.replace(/\.[^.]+$/, "");
        a.download = `${baseName}.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } catch {
        setUploadError(t("dashboard.errorDownload"));
      }
    },
    [t]
  );

  const deleteJob = useCallback(
    async (job) => {
      if (!window.confirm(`Supprimer la transcription de « ${job.filename_original} » ?`)) return;
      try {
        await jobsApi.deleteJob(job.id);
        setJobs((prev) => prev.filter((j) => j.id !== job.id));
      } catch {
        setUploadError(t("dashboard.errorDelete"));
      }
    },
    [t]
  );

  return {
    // state
    jobs,
    isLoadingJobs,
    uploadError,
    isUploading,
    uploadProgress,
    enabledModels,
    selectedModel,
    fileInputRef,
    // actions
    setSelectedModel,
    uploadFile,
    cancelJob,
    downloadJob,
    deleteJob,
  };
}
