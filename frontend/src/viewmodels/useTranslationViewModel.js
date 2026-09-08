import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import * as translationApi from "../models/translation";

const POLL_INTERVAL_MS = 4000;

/**
 * ViewModel for the translation page: enabled directions, form state for
 * text and archive submissions, and the translation job list with polling.
 */
export function useTranslationViewModel() {
  const { t } = useTranslation();
  const [directions, setDirections] = useState([]);
  const [direction, setDirection] = useState("");
  const [text, setText] = useState("");
  const [archiveFile, setArchiveFile] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadPercent, setUploadPercent] = useState(0);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const fetchJobs = useCallback(async () => {
    try {
      const data = await translationApi.listTranslationJobs();
      setJobs(data);
    } catch {
      // Silent failure on periodic polling.
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    translationApi
      .listEnabledDirections()
      .then((dirs) => {
        setDirections(dirs.map((d) => d.direction));
        if (dirs.length > 0) setDirection(dirs[0].direction);
      })
      .catch(() => setDirections([]));
    fetchJobs();
  }, [fetchJobs]);

  useEffect(() => {
    const hasActiveJob = jobs.some(
      (j) => j.status === "pending" || j.status === "processing" || j.status === "cancelling"
    );
    if (hasActiveJob) {
      const id = setInterval(fetchJobs, POLL_INTERVAL_MS);
      return () => clearInterval(id);
    }
  }, [jobs, fetchJobs]);

  const hasActiveModel = directions.length > 0;

  const submitText = useCallback(async () => {
    if (!text.trim() || !direction) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await translationApi.createTextJob(direction, text);
      setText("");
      await fetchJobs();
    } catch (err) {
      setError(err.response?.data?.detail || t("translation.errorCreate"));
    } finally {
      setIsSubmitting(false);
    }
  }, [direction, fetchJobs, t, text]);

  const submitArchive = useCallback(async () => {
    if (!archiveFile || !direction) return;
    setError(null);
    setIsSubmitting(true);
    setUploadPercent(0);
    try {
      await translationApi.createArchiveJob(archiveFile, direction, (progressEvent) => {
        if (progressEvent.total) {
          setUploadPercent(Math.round((progressEvent.loaded / progressEvent.total) * 100));
        }
      });
      setArchiveFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await fetchJobs();
    } catch (err) {
      setError(err.response?.data?.detail || t("translation.errorArchive"));
    } finally {
      setIsSubmitting(false);
      setUploadPercent(0);
    }
  }, [archiveFile, direction, fetchJobs, t]);

  const cancelJob = useCallback(
    async (job) => {
      try {
        await translationApi.cancelTranslationJob(job.id);
        await fetchJobs();
      } catch {
        setError(t("translation.errorCancel"));
      }
    },
    [fetchJobs, t]
  );

  const downloadJob = useCallback(
    async (job) => {
      try {
        const blob = await translationApi.downloadTranslationJob(job.id);
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = job.job_type === "archive" ? "traduction.zip" : "traduction.txt";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      } catch {
        setError(t("translation.errorDownload"));
      }
    },
    [t]
  );

  const deleteJob = useCallback(
    async (job) => {
      if (!window.confirm(t("translation.deleteConfirm"))) return;
      try {
        await translationApi.deleteTranslationJob(job.id);
        setJobs((prev) => prev.filter((j) => j.id !== job.id));
      } catch {
        setError(t("translation.errorDelete"));
      }
    },
    [t]
  );

  return {
    // state
    directions,
    direction,
    text,
    archiveFile,
    jobs,
    isLoading,
    isSubmitting,
    uploadPercent,
    error,
    hasActiveModel,
    fileInputRef,
    // actions / setters
    setDirection,
    setText,
    setArchiveFile,
    submitText,
    submitArchive,
    cancelJob,
    downloadJob,
    deleteJob,
  };
}
