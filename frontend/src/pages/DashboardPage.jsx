import { useCallback, useEffect, useRef, useState } from "react";
import * as jobsApi from "../api/jobs";
import * as modelsApi from "../api/whisperModels";
import StatusBadge from "../components/StatusBadge.jsx";
import Waveform from "../components/Waveform.jsx";
import "./DashboardPage.css";

const ACCEPTED_EXTENSIONS = [".mp3", ".wav", ".m4a", ".ogg", ".webm"];
const POLL_INTERVAL_MS = 4000;

function formatDate(isoString) {
  if (!isoString) return "—";
  const date = new Date(isoString);
  return date.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DashboardPage() {
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

  const fetchJobs = useCallback(async () => {
    try {
      const data = await jobsApi.listJobs();
      data.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setJobs(data);
    } catch {
      // Erreur silencieuse sur le polling périodique : on ne veut pas
      // interrompre l'utilisateur pour un échec réseau transitoire.
    } finally {
      setIsLoadingJobs(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  useEffect(() => {
    // Modèles proposés pour l'upload (sélecteur) : affiché seulement s'il y
    // en a plusieurs, le modèle par défaut couvrant le cas simple.
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

  function validateFile(file) {
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!ACCEPTED_EXTENSIONS.includes(ext)) {
      return `Format non supporté (${ext}). Formats acceptés : ${ACCEPTED_EXTENSIONS.join(", ")}`;
    }
    return null;
  }

  async function handleFiles(fileList) {
    const file = fileList?.[0];
    if (!file) return;

    const validationError = validateFile(file);
    if (validationError) {
      setUploadError(validationError);
      return;
    }

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
      setUploadError(detail || "Échec de l'envoi du fichier. Réessayez.");
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
      setUploadError("Impossible d'annuler cette transcription.");
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
      setUploadError("Impossible de télécharger la transcription.");
    }
  }

  async function handleDelete(job) {
    if (!window.confirm(`Supprimer la transcription de « ${job.filename_original} » ?`)) return;
    try {
      await jobsApi.deleteJob(job.id);
      setJobs((prev) => prev.filter((j) => j.id !== job.id));
    } catch {
      setUploadError("Impossible de supprimer cette transcription.");
    }
  }

  return (
    <div className="dashboard">
      <section className="dashboard-header">
        <h1>Transcription</h1>
        <p>Déposez un fichier audio en français pour obtenir une transcription horodatée.</p>
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
            <p>Envoi en cours… {uploadProgress}%</p>
          </div>
        ) : (
          <>
            <p className="upload-zone-title">Glissez-déposez un fichier audio ici</p>
            <p className="upload-zone-subtitle">
              ou{" "}
              <button
                type="button"
                className="upload-zone-browse"
                onClick={() => fileInputRef.current?.click()}
              >
                parcourez vos fichiers
              </button>
            </p>
            <p className="upload-zone-formats">{ACCEPTED_EXTENSIONS.join(" · ")}</p>
            {enabledModels.length > 1 && (
              <div className="upload-model-choice">
                <label htmlFor="model-select">Modèle :</label>
                <select
                  id="model-select"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                >
                  <option value="">
                    Par défaut ({enabledModels.find((m) => m.is_default)?.name || "—"})
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
            <p>Aucune transcription pour l'instant. Déposez un premier fichier ci-dessus.</p>
          </div>
        ) : (
          <div className="card">
            <table className="table">
              <thead>
                <tr>
                  <th>Fichier</th>
                  <th>Statut</th>
                  <th>Modèle</th>
                  <th>Créée le</th>
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
                          Annuler
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
                            Télécharger ▾
                          </button>
                          {downloadMenuJobId === job.id && (
                            <div className="download-menu-list">
                              <button
                                onClick={() => {
                                  setDownloadMenuJobId(null);
                                  handleDownload(job, "vtt");
                                }}
                              >
                                WebVTT horodaté (.vtt)
                              </button>
                              <button
                                onClick={() => {
                                  setDownloadMenuJobId(null);
                                  handleDownload(job, "txt");
                                }}
                              >
                                Texte brut (.txt)
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(job)}>
                        Supprimer
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
