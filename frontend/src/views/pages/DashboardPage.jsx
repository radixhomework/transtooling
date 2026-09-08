import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useTranscriptionViewModel } from "../../viewmodels/useTranscriptionViewModel";
import StatusBadge from "../components/StatusBadge.jsx";
import Waveform from "../components/Waveform.jsx";
import "./DashboardPage.css";

const ACCEPTED_EXTENSIONS = [".mp3", ".wav", ".m4a", ".ogg", ".webm"];

function formatDate(isoString, language) {
  if (!isoString) return "—";
  const locale = language === "en" ? "en-GB" : "fr-FR";
  return new Date(isoString).toLocaleString(locale, {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DashboardPage() {
  const { t, i18n } = useTranslation();
  const {
    jobs,
    isLoadingJobs,
    uploadError,
    isUploading,
    uploadProgress,
    enabledModels,
    selectedModel,
    fileInputRef,
    setSelectedModel,
    uploadFile,
    cancelJob,
    downloadJob,
    deleteJob,
  } = useTranscriptionViewModel();

  const [dragActive, setDragActive] = useState(false);
  const [downloadMenuJobId, setDownloadMenuJobId] = useState(null);

  function handleDrop(e) {
    e.preventDefault();
    setDragActive(false);
    uploadFile(e.dataTransfer.files?.[0]);
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
              onChange={(e) => uploadFile(e.target.files?.[0])}
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
                    <td className="mono">{formatDate(job.created_at, i18n.language)}</td>
                    <td className="job-actions">
                      {["pending", "processing", "cancelling"].includes(job.status) && (
                        <button
                          className="btn btn-secondary btn-sm"
                          disabled={job.status === "cancelling"}
                          onClick={() => cancelJob(job)}
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
                                  downloadJob(job, "vtt");
                                }}
                              >
                                {t("dashboard.downloadVtt")}
                              </button>
                              <button
                                onClick={() => {
                                  setDownloadMenuJobId(null);
                                  downloadJob(job, "txt");
                                }}
                              >
                                {t("dashboard.downloadTxt")}
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                      <button className="btn btn-danger btn-sm" onClick={() => deleteJob(job)}>
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
