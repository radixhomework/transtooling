import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import * as modelsApi from "../api/whisperModels";
import * as translationApi from "../api/translation";
import Waveform from "../components/Waveform.jsx";
import "./AdminModelsPage.css";

const POLL_INTERVAL_MS = 4000;

// Approximate sizes, indicative before download; the actual on-disk
// size is reported by the backend once the model is downloaded.
const WHISPER_APPROX_SIZE_MB = {
  tiny: 75,
  base: 145,
  small: 465,
  medium: 1500,
  "large-v3": 3000,
};

const DIRECTION_APPROX_SIZE_MB = { "fr-en": 650, "en-fr": 650 };

const STATUS_KEYS = {
  not_downloaded: "statusNotDownloaded",
  downloading: "statusDownloading",
  downloaded: "statusDownloaded",
  error: "statusError",
};

const DIRECTION_KEYS = {
  "fr-en": "directionFrEn",
  "en-fr": "directionEnFr",
};

function ModelStatusLine({ model }) {
  const { t } = useTranslation();
  return (
    <div className={`model-status status-${model.status}`}>
      {model.status === "downloading" && <Waveform size="sm" />}
      {t(`adminModels.${STATUS_KEYS[model.status] || model.status}`)}
    </div>
  );
}

function useModels(fetcher) {
  const { t } = useTranslation();
  const [models, setModels] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyKey, setBusyKey] = useState(null);

  const fetchModels = useCallback(async () => {
    try {
      const data = await fetcher();
      setModels(data);
    } catch {
      setError(t("adminModels.errorLoad"));
    } finally {
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        setError(err.response?.data?.detail || t("common.errorGeneric"));
      } finally {
        setBusyKey(null);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [fetchModels]
  );

  return { models, isLoading, error, busyKey, withBusy };
}

function WhisperModelsSection() {
  const { t, i18n } = useTranslation();
  const { models, isLoading, error, busyKey, withBusy } = useModels(modelsApi.listWhisperModels);

  function formatSizeMB(sizeMB) {
    if (sizeMB == null) return null;
    if (sizeMB >= 1024) {
      const go = (sizeMB / 1024).toFixed(1);
      return i18n.language === "en"
        ? `${go} GB`
        : `${go.replace(".", ",")} Go`;
    }
    return `${sizeMB} MB`;
  }

  return (
    <section className="models-section">
      <div className="models-section-header">
        <h2>{t("adminModels.whisperSection")}</h2>
        <p>{t("adminModels.whisperSectionDesc")}</p>
      </div>

      {error && <p className="error-text">{error}</p>}

      {isLoading ? (
        <p>{t("common.loading")}</p>
      ) : (
        <div className="models-grid">
          {models.map((model) => {
            const isBusy = busyKey === model.name;
            const sizeLabel = formatSizeMB(model.disk_size_mb ?? WHISPER_APPROX_SIZE_MB[model.name]);
            return (
              <div key={model.name} className={`card model-card ${model.is_default ? "is-default" : ""}`}>
                <div className="model-card-header">
                  <span className="model-name mono">{model.name}</span>
                  {model.is_default && (
                    <span className="badge badge-done">{t("adminModels.badgeDefault")}</span>
                  )}
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
                      {t("adminModels.download")}
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
                          {t("adminModels.enable")}
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
                            {t("adminModels.set_default")}
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
                            {t("adminModels.disable")}
                          </button>
                        </>
                      )}

                      {model.is_enabled && model.is_default && (
                        <button
                          className="btn btn-secondary btn-sm"
                          disabled
                          title={t("adminModels.disableDefaultHint")}
                        >
                          {t("adminModels.disable")}
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
                          {t("common.delete")}
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
  const { t, i18n } = useTranslation();
  const fetcher = useCallback(() => translationApi.listTranslationModels(), []);
  const { models, isLoading, error, busyKey, withBusy } = useModels(fetcher);

  function formatSizeMB(sizeMB) {
    if (sizeMB == null) return null;
    if (sizeMB >= 1024) {
      const go = (sizeMB / 1024).toFixed(1);
      return i18n.language === "en"
        ? `${go} GB`
        : `${go.replace(".", ",")} Go`;
    }
    return `${sizeMB} MB`;
  }

  return (
    <section className="models-section">
      <div className="models-section-header">
        <h2>{t("adminModels.translationSection")}</h2>
        <p>{t("adminModels.translationSectionDesc")}</p>
      </div>

      {error && <p className="error-text">{error}</p>}

      {isLoading ? (
        <p>{t("common.loading")}</p>
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
                    {t(`adminModels.${DIRECTION_KEYS[model.direction] || model.direction}`)}
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
                      {t("adminModels.download")}
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
                          {t("adminModels.enable")}
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
                          {t("adminModels.disable")}
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
                        {t("common.delete")}
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
  const { t } = useTranslation();
  return (
    <div className="admin-models-page">
      <WhisperModelsSection />
      <TranslationModelsSection />
    </div>
  );
}
