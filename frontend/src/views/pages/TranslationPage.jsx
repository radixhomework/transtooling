import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useTranslationViewModel } from "../../viewmodels/useTranslationViewModel";
import StatusBadge from "../components/StatusBadge.jsx";
import Waveform from "../components/Waveform.jsx";
import "./TranslationPage.css";

const DIRECTION_KEYS = {
  "fr-en": "directionFrEn",
  "en-fr": "directionEnFr",
};

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

export default function TranslationPage() {
  const { t, i18n } = useTranslation();
  const {
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
    setDirection,
    setText,
    setArchiveFile,
    submitText,
    submitArchive,
    cancelJob,
    downloadJob,
    deleteJob,
  } = useTranslationViewModel();

  const [tab, setTab] = useState("text");

  return (
    <div className="translation-page">
      <section className="translation-header">
        <h1>{t("translation.title")}</h1>
        <p>{t("translation.subtitle")}</p>
      </section>

      {error && <p className="error-text">{error}</p>}

      {!hasActiveModel ? (
        <div className="empty-state card">
          <p>{t("translation.noModel")}</p>
        </div>
      ) : (
        <div className="card translation-form">
          <div className="translation-tabs" role="tablist">
            <button
              type="button"
              className={`translation-tab ${tab === "text" ? "is-active" : ""}`}
              onClick={() => setTab("text")}
            >
              {t("translation.tabText")}
            </button>
            <button
              type="button"
              className={`translation-tab ${tab === "archive" ? "is-active" : ""}`}
              onClick={() => setTab("archive")}
            >
              {t("translation.tabArchive")}
            </button>
          </div>

          <div className="field direction-field">
            <label htmlFor="translation-direction">{t("translation.directionLabel")}</label>
            <select
              id="translation-direction"
              value={direction}
              onChange={(e) => setDirection(e.target.value)}
              disabled={isSubmitting}
            >
              {directions.map((d) => (
                <option key={d} value={d}>
                  {t(`translation.${DIRECTION_KEYS[d] || d}`)}
                </option>
              ))}
            </select>
          </div>

          {tab === "text" ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                submitText();
              }}
              className="translation-text-form"
            >
              <div className="field">
                <label htmlFor="translation-text">{t("translation.textLabel")}</label>
                <textarea
                  id="translation-text"
                  rows={8}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder={t("translation.textPlaceholder")}
                  disabled={isSubmitting}
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary" disabled={isSubmitting || !text.trim()}>
                {isSubmitting ? t("translation.submitting") : t("translation.submitText")}
              </button>
            </form>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                submitArchive();
              }}
              className="translation-archive-form"
            >
              <div className="field">
                <label htmlFor="translation-archive">{t("translation.archiveLabel")}</label>
                <input
                  ref={fileInputRef}
                  id="translation-archive"
                  type="file"
                  accept=".zip"
                  onChange={(e) => setArchiveFile(e.target.files?.[0] || null)}
                  disabled={isSubmitting}
                  required
                />
                <p className="translation-archive-hint">{t("translation.archiveHint")}</p>
                {isSubmitting && uploadPercent > 0 && (
                  <div className="progress">
                    <div className="progress-bar">
                      <div className="progress-fill" style={{ "--progress": uploadPercent / 100 }} />
                    </div>
                    <span className="progress-label">
                      {t("translation.uploading", { percent: uploadPercent })}
                    </span>
                  </div>
                )}
              </div>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isSubmitting || !archiveFile}
              >
                {isSubmitting ? t("translation.submitting") : t("translation.submitArchive")}
              </button>
            </form>
          )}
        </div>
      )}

      <section className="translation-jobs-section">
        {isLoading ? (
          <div className="empty-state">
            <Waveform />
          </div>
        ) : jobs.length === 0 ? (
          <div className="empty-state card">
            <p>{t("translation.empty")}</p>
          </div>
        ) : (
          <div className="translation-jobs-list">
            {jobs.map((job) => (
              <div key={job.id} className="card translation-job-card">
                <div className="translation-job-header">
                  <span className="badge badge-done">
                    {job.job_type === "archive" ? t("translation.badgeArchive") : t("translation.badgeText")}
                  </span>
                  <span className="mono translation-job-direction">
                    {t(`translation.${DIRECTION_KEYS[job.direction] || job.direction}`)}
                  </span>
                  <StatusBadge status={job.status} />
                  <span className="mono translation-job-date">
                    {formatDate(job.created_at, i18n.language)}
                  </span>
                  <span className="translation-job-actions">
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
                      <button className="btn btn-secondary btn-sm" onClick={() => downloadJob(job)}>
                        {job.job_type === "archive"
                          ? t("translation.downloadZip")
                          : t("translation.downloadTxt")}
                      </button>
                    )}
                    <button className="btn btn-danger btn-sm" onClick={() => deleteJob(job)}>
                      {t("common.delete")}
                    </button>
                  </span>
                </div>

                {job.status === "error" && job.error_message && (
                  <p className="error-text">{job.error_message}</p>
                )}

                {job.status === "processing" && (
                  <div className="translation-processing">
                    <Waveform size="sm" />
                    <span>{t("translation.processing")}</span>
                  </div>
                )}

                {job.status === "done" && job.job_type === "text" && (
                  <div className="translation-result">
                    <pre className="translation-result-text">{job.result_preview}</pre>
                    {job.result_truncated && (
                      <p className="translation-truncated">{t("translation.truncated")}</p>
                    )}
                  </div>
                )}

                {job.status === "done" && job.job_type === "archive" && job.report && (
                  <div className="translation-report">
                    <p>
                      {t("translation.reportSummary", {
                        translated: job.report.translated,
                        copied: job.report.copied,
                      })}
                      {job.report.errors > 0 &&
                        " " + t("translation.reportErrorSuffix", { count: job.report.errors })}
                    </p>
                    {job.report.error_details?.length > 0 && (
                      <details className="translation-report-details">
                        <summary>{t("translation.reportDetails")}</summary>
                        <ul>
                          {job.report.error_details.map((detail) => (
                            <li key={detail.file}>
                              <span className="mono">{detail.file}</span> — {detail.error}
                            </li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
