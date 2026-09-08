import { useTranslation } from "react-i18next";
import { useModelsAdminViewModel } from "../../viewmodels/useModelsAdminViewModel";
import Waveform from "../components/Waveform.jsx";
import "./AdminModelsPage.css";

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

function formatSizeMB(sizeMB, language) {
  if (sizeMB == null) return null;
  if (sizeMB >= 1024) {
    const go = (sizeMB / 1024).toFixed(1);
    return language === "en" ? `${go} GB` : `${go.replace(".", ",")} Go`;
  }
  return `${sizeMB} MB`;
}

function ModelStatusLine({ model }) {
  const { t } = useTranslation();
  return (
    <div className={`model-status status-${model.status}`}>
      {model.status === "downloading" && <Waveform size="sm" />}
      {t(`adminModels.${STATUS_KEYS[model.status] || model.status}`)}
    </div>
  );
}

function WhisperModelsSection() {
  const { t, i18n } = useTranslation();
  const { models, isLoading, error, busyKey, download, update, remove } =
    useModelsAdminViewModel().whisper;

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
            const sizeLabel = formatSizeMB(
              model.disk_size_mb ?? WHISPER_APPROX_SIZE_MB[model.name],
              i18n.language
            );
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
                      onClick={() => download(model.name)}
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
                          onClick={() => update(model.name, { is_enabled: true })}
                        >
                          {t("adminModels.enable")}
                        </button>
                      )}

                      {model.is_enabled && !model.is_default && (
                        <>
                          <button
                            className="btn btn-secondary btn-sm"
                            disabled={isBusy}
                            onClick={() => update(model.name, { is_default: true })}
                          >
                            {t("adminModels.set_default")}
                          </button>
                          <button
                            className="btn btn-secondary btn-sm"
                            disabled={isBusy}
                            onClick={() => update(model.name, { is_enabled: false })}
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
                          onClick={() => remove(model.name)}
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
  const { models, isLoading, error, busyKey, download, update, remove } =
    useModelsAdminViewModel().translation;

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
              model.disk_size_mb ?? DIRECTION_APPROX_SIZE_MB[model.direction],
              i18n.language
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
                      onClick={() => download(model.direction)}
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
                          onClick={() => update(model.direction, { is_enabled: true })}
                        >
                          {t("adminModels.enable")}
                        </button>
                      )}
                      {model.is_enabled && (
                        <button
                          className="btn btn-secondary btn-sm"
                          disabled={isBusy}
                          onClick={() => update(model.direction, { is_enabled: false })}
                        >
                          {t("adminModels.disable")}
                        </button>
                      )}
                      <button
                        className="btn btn-danger btn-sm"
                        disabled={isBusy}
                        onClick={() => remove(model.direction)}
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
  return (
    <div className="admin-models-page">
      <WhisperModelsSection />
      <TranslationModelsSection />
    </div>
  );
}
