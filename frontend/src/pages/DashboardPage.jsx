import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import * as jobsApi from "../api/jobs";
import * as modelsApi from "../api/whisperModels";
import StatusBadge from "../components/StatusBadge.jsx";
import Waveform from "../components/Waveform.jsx";
import "./DashboardPage.css";

const ACCEPTED_EXTENSIONS = [".mp3", ".wav", ".m4a", ".ogg", ".webm"];
const POLL_INTERVAL_MS = 4000;

export default function DashboardPage() {
  const { t, i18n } = useTranslation();
  const [jobs, setJobs] = useState([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [uploadError, setUploadError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [enabledModels, setEnabledModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [downloadMenuJobId, setDownloadMenuJobId] = useState(null);
  const fileInputRef = useRef(null);
  const pollRef = useRef(null);

  function formatDate(isoString) {
    if (!isoString) return "—";
    const locale = i18n.language === "en" ? "en-GB" : "fr-FR";
    return new Date(isoString).toLocaleString(locale, {
      day: "2-digit",
      month: "2-digit",
      year: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

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

  async function handleFiles(fileList) {
    const file = fileList?.[0];
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
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  }

  async function handleCancel(job) {
    try {
      await jobsApi.cancelJob(job.id);
      await fetchJobs();
    } catch {
      setUploadError(t("dashboard.errorCancel"));
    }
  }

  async function handleDownload(job, format) {
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
  }

  async function handleDelete(job) {
    if (!window.confirm(`Supprimer la transcription de « ${job.filename_original} » ?`)) return;
    try {
      await jobsApi.deleteJob(job.id);
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
    } catch {
      setUploadError(t("dashboard.errorDelete"));
    }
  }

  return (
    <div className="dashboard">
      <section className="dashboard-header">
        <h1>{t("dashboard.title")}</h1>
        <p>{t("dashboard.subtitle")}</p>
      </section>

      <section
        className={`upload-zone card ${dragActive ? "is-drag-active" : ""} ${isUploading ? "is-uploading" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
      >
        {isUploading ? (
          <div className="upload-progress">
            <Waveform size="lg" />
            <p>{t("dashboard.uploading", { percent: uploadProgress })}</p>
          </div>
        ) : (
          <>
            <p className="upload-zone-title">{t("dashboard.dropTitle")}</p>
            <p className="upload-zone-subtitle">
              {t("dashboard.or")}{" "}
              <button
                type="button"
                className="upload-zone-browse"
                onClick={() => fileInputRef.current?.click()}
              >
                {t("dashboard.browse")}
              </button>
            </p>
            <p className="upload-zone-formats">{ACCEPTED_EXTENSIONS.join(" · ")}</p>
            {enabledModels.length > 1 && (
              <div className="upload-model-choice">
                <label htmlFor="model-select">{t("dashboard.modelLabel")}</label>
                <select
                  id="model-select"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                >
                  <option value="">
                    {t("dashboard.modelDefault", {
                      name: enabledModels.find((m) => m.is_default)?.name || "—",
                    })}
                  </option>
                  {enabledModels
                    .filter((m) => !m.is_default)
                    .map((m) => (
                      <option key={m.name} value={m.name}>
                        {m.name}
                      </option>
                    ))}
                </select>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS.join(",")}
              onChange={(e) => handleFiles(e.target.files)}
              hidden
            />
          </>
        )}
      </section>

      {uploadError && <p className="error-text upload-error">{uploadError}</p>}

      <section className="jobs-section">
        {isLoadingJobs ? (
          <div className="empty-state">
            <Waveform />
          </div>
        ) : jobs.length === 0 ? (
          <div className="empty-state card">
            <p>{t("dashboard.empty")}</p>
          </div>
        ) : (
          <div className="card">
            <table className="table">
              <thead>
                <tr>
                  <th>{t("dashboard.colFile")}</th>
                  <th>{t("dashboard.colStatus")}</th>
                  <th>{t("dashboard.colModel")}</th>
                  <th>{t("dashboard.colDate")}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td>{job.filename_original}</td>
                    <td>
                      <StatusBadge status={job.status} progress={job.progress} />
                      {job.status === "processing" && job.progress != null && (
                        <div className="progress job-progress">
                          <div className="progress-bar">
                            <div
                              className="progress-fill"
                              style={{
                                "--progress": Math.min(100, Math.max(0, job.progress)) / 100,
                              }}
                            />
                          </div>
                        </div>
                      )}
                      {job.status === "error" && job.error_message && (
                        <div className="job-error-detail">{job.error_message}</div>
                      )}
                    </td>
                    <td className="mono">{job.model_used}</td>
                    <td className="mono">{formatDate(job.created_at)}</td>
                    <td className="job-actions">
                      {["pending", "processing", "cancelling"].includes(job.status) && (
                        <button
                          className="btn btn-secondary btn-sm"
                          disabled={job.status === "cancelling"}
                          onClick={() => handleCancel(job)}
                        >
                          {t("common.cancelJob")}
                        </button>
                      )}
                      {job.status === "done" && (
                        <div className="download-menu">
                          {downloadMenuJobId === job.id && (
                            <div
                              className="download-menu-backdrop"
                              onClick={() => setDownloadMenuJobId(null)}
                            />
                          )}
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() =>
                              setDownloadMenuJobId(downloadMenuJobId === job.id ? null : job.id)
                            }
                          >
                            {t("common.download")} ▾
                          </button>
                          {downloadMenuJobId === job.id && (
                            <div className="download-menu-list">
                              <button
                                onClick={() => {
                                  setDownloadMenuJobId(null);
                                  handleDownload(job, "vtt");
                                }}
                              >
                                {t("dashboard.downloadVtt")}
                              </button>
                              <button
                                onClick={() => {
                                  setDownloadMenuJobId(null);
                                  handleDownload(job, "txt");
                                }}
                              >
                                {t("dashboard.downloadTxt")}
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(job)}>
                        {t("common.delete")}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
