import { useCallback, useEffect, useState } from "react";
import * as modelsApi from "../api/whisperModels";
import * as translationApi from "../api/translation";
import Waveform from "../components/Waveform.jsx";
import "./AdminModelsPage.css";

const POLL_INTERVAL_MS = 4000;

const STATUS_LABELS = {
  not_downloaded: "Non téléchargé",
  downloading: "Téléchargement…",
  downloaded: "Téléchargé",
  error: "Erreur",
};

// Tailles approximatives, à titre indicatif avant téléchargement ; la taille
// réelle sur disque est remontée par le backend une fois le modèle téléchargé.
const WHISPER_APPROX_SIZE_MB = {
  tiny: 75,
  base: 145,
  small: 465,
  medium: 1500,
  "large-v3": 3000,
};

const DIRECTION_LABELS = {
  "fr-en": "Français → Anglais",
  "en-fr": "Anglais → Français",
};

const DIRECTION_APPROX_SIZE_MB = { "fr-en": 650, "en-fr": 650 };

function formatSizeMB(sizeMB) {
  if (sizeMB == null) return null;
  if (sizeMB >= 1024) {
    return `${(sizeMB / 1024).toFixed(1).replace(".", ",")} Go`;
  }
  return `${sizeMB} Mo`;
}

function ModelStatusLine({ model }) {
  return (
    <div className={`model-status status-${model.status}`}>
      {model.status === "downloading" && <Waveform size="sm" />}
      {STATUS_LABELS[model.status]}
    </div>
  );
}

function useModels(fetcher) {
  const [models, setModels] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyKey, setBusyKey] = useState(null);

  const fetchModels = useCallback(async () => {
    try {
      const data = await fetcher();
      setModels(data);
    } catch {
      setError("Impossible de charger la liste des modèles.");
    } finally {
      setIsLoading(false);
    }
  }, [fetcher]);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  useEffect(() => {
    const hasDownloading = models.some((m) => m.status === "downloading");
    if (hasDownloading) {
      const id = setInterval(fetchModels, POLL_INTERVAL_MS);
      return () => clearInterval(id);
    }
  }, [models, fetchModels]);

  const withBusy = useCallback(
    async (key, action) => {
      setError(null);
      setBusyKey(key);
      try {
        await action();
        await fetchModels();
      } catch (err) {
        setError(err.response?.data?.detail || "Une erreur est survenue.");
      } finally {
        setBusyKey(null);
      }
    },
    [fetchModels]
  );

  return { models, isLoading, error, busyKey, withBusy };
}

function WhisperModelsSection() {
  const { models, isLoading, error, busyKey, withBusy } = useModels(modelsApi.listWhisperModels);

  return (
    <section className="models-section">
      <div className="models-section-header">
        <h2>Whisper — transcription audio</h2>
        <p>
          Modèles faster-whisper utilisés pour la transcription (français uniquement),
          téléchargés à la demande.
        </p>
      </div>

      {error && <p className="error-text">{error}</p>}

      {isLoading ? (
        <p>Chargement…</p>
      ) : (
        <div className="models-grid">
          {models.map((model) => {
            const isBusy = busyKey === model.name;
            const sizeLabel = formatSizeMB(model.disk_size_mb ?? WHISPER_APPROX_SIZE_MB[model.name]);
            return (
              <div key={model.name} className={`card model-card ${model.is_default ? "is-default" : ""}`}>
                <div className="model-card-header">
                  <span className="model-name mono">{model.name}</span>
                  {model.is_default && <span className="badge badge-done">Par défaut</span>}
                </div>

                <ModelStatusLine model={model} />

                {sizeLabel && (
                  <div className="model-size">
                    {model.status === "downloaded" ? sizeLabel : `≈ ${sizeLabel}`}
                  </div>
                )}

                {model.error_message && <p className="error-text model-error">{model.error_message}</p>}

                <div className="model-actions">
                  {model.status === "not_downloaded" && (
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={isBusy}
                      onClick={() =>
                        withBusy(model.name, () => modelsApi.downloadWhisperModel(model.name))
                      }
                    >
                      Télécharger
                    </button>
                  )}

                  {model.status === "downloaded" && (
                    <>
                      {!model.is_enabled && (
                        <button
                          className="btn btn-secondary btn-sm"
                          disabled={isBusy}
                          onClick={() =>
                            withBusy(model.name, () =>
                              modelsApi.updateWhisperModel(model.name, { is_enabled: true })
                            )
                          }
                        >
                          Activer
                        </button>
                      )}

                      {model.is_enabled && !model.is_default && (
                        <>
                          <button
                            className="btn btn-secondary btn-sm"
                            disabled={isBusy}
                            onClick={() =>
                              withBusy(model.name, () =>
                                modelsApi.updateWhisperModel(model.name, { is_default: true })
                              )
                            }
                          >
                            Définir par défaut
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            disabled={isBusy}
                            onClick={() =>
                              withBusy(model.name, () =>
                                modelsApi.updateWhisperModel(model.name, { is_enabled: false })
                              )
                            }
                          >
                            Désactiver
                          </button>
                        </>
                      )}

                      {model.is_enabled && model.is_default && (
                        <button
                          className="btn btn-secondary btn-sm"
                          disabled
                          title="Changez d'abord le modèle par défaut pour désactiver ce modèle"
                        >
                          Désactiver
                        </button>
                      )}

                      {!model.is_default && (
                        <button
                          className="btn btn-danger btn-sm"
                          disabled={isBusy}
                          onClick={() =>
                            withBusy(model.name, () => modelsApi.deleteWhisperModel(model.name))
                          }
                        >
                          Supprimer
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function TranslationModelsSection() {
  const fetcher = useCallback(() => translationApi.listTranslationModels(), []);
  const { models, isLoading, error, busyKey, withBusy } = useModels(fetcher);

  return (
    <section className="models-section">
      <div className="models-section-header">
        <h2>Traduction</h2>
        <p>
          Modèles utilisés pour la traduction, un par direction, téléchargés à la demande.
        </p>
      </div>

      {error && <p className="error-text">{error}</p>}

      {isLoading ? (
        <p>Chargement…</p>
      ) : (
        <div className="models-grid">
          {models.map((model) => {
            const isBusy = busyKey === model.direction;
            const sizeLabel = formatSizeMB(
              model.disk_size_mb ?? DIRECTION_APPROX_SIZE_MB[model.direction]
            );
            return (
              <div key={model.direction} className="card model-card">
                <div className="model-card-header">
                  <span className="model-name mono">
                    {DIRECTION_LABELS[model.direction] || model.direction}
                  </span>
                </div>

                <ModelStatusLine model={model} />

                {sizeLabel && (
                  <div className="model-size">
                    {model.status === "downloaded" ? sizeLabel : `≈ ${sizeLabel}`}
                  </div>
                )}

                {model.error_message && <p className="error-text model-error">{model.error_message}</p>}

                <div className="model-actions">
                  {model.status === "not_downloaded" && (
                    <button
                      className="btn btn-primary btn-sm"
                      disabled={isBusy}
                      onClick={() =>
                        withBusy(model.direction, () =>
                          translationApi.downloadTranslationModel(model.direction)
                        )
                      }
                    >
                      Télécharger
                    </button>
                  )}

                  {model.status === "downloaded" && (
                    <>
                      {!model.is_enabled && (
                        <button
                          className="btn btn-secondary btn-sm"
                          disabled={isBusy}
                          onClick={() =>
                            withBusy(model.direction, () =>
                              translationApi.updateTranslationModel(model.direction, {
                                is_enabled: true,
                              })
                            )
                          }
                        >
                          Activer
                        </button>
                      )}
                      {model.is_enabled && (
                        <button
                          className="btn btn-secondary btn-sm"
                          disabled={isBusy}
                          onClick={() =>
                            withBusy(model.direction, () =>
                              translationApi.updateTranslationModel(model.direction, {
                                is_enabled: false,
                              })
                            )
                          }
                        >
                          Désactiver
                        </button>
                      )}
                      <button
                        className="btn btn-danger btn-sm"
                        disabled={isBusy}
                        onClick={() =>
                          withBusy(model.direction, () =>
                            translationApi.deleteTranslationModel(model.direction)
                          )
                        }
                      >
                        Supprimer
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default function AdminModelsPage() {
  return (
    <div className="admin-models-page">
      <div className="admin-page-header">
        <div>
          <h1>Modèles</h1>
          <p>
            Téléchargez, activez et supprimez les modèles utilisés par l'application :
            Whisper pour la transcription audio, les modèles de traduction pour la traduction.
          </p>
        </div>
      </div>

      <WhisperModelsSection />
      <TranslationModelsSection />
    </div>
  );
}
