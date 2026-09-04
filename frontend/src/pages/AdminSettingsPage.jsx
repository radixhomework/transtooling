import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import * as settingsApi from "../api/appSettings";
import "./AdminSettingsPage.css";

export default function AdminSettingsPage() {
  const { t } = useTranslation();
  const [maxFileSizeMb, setMaxFileSizeMb] = useState("");
  const [maxDurationMin, setMaxDurationMin] = useState("");
  const [maxTextLengthChars, setMaxTextLengthChars] = useState("");
  const [previewTruncateChars, setPreviewTruncateChars] = useState("");
  const [maxArchiveSizeMb, setMaxArchiveSizeMb] = useState("");
  const [maxArchiveFilesCount, setMaxArchiveFilesCount] = useState("");
  const [maxArchiveUncompressedMb, setMaxArchiveUncompressedMb] = useState("");
  const [translatableExtensions, setTranslatableExtensions] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    settingsApi
      .getAppSettings()
      .then((data) => {
        setMaxFileSizeMb(String(data.max_file_size_mb));
        setMaxDurationMin(String(data.max_duration_min));
        setMaxTextLengthChars(String(data.max_text_length_chars));
        setPreviewTruncateChars(String(data.preview_truncate_chars));
        setMaxArchiveSizeMb(String(data.max_archive_size_mb));
        setMaxArchiveFilesCount(String(data.max_archive_files_count));
        setMaxArchiveUncompressedMb(String(data.max_archive_uncompressed_mb));
        setTranslatableExtensions(data.translatable_extensions);
      })
      .catch(() => setError(t("adminSettings.errorLoad")))
      .finally(() => setIsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setIsSaving(true);
    try {
      await settingsApi.updateAppSettings({
        max_file_size_mb: Number(maxFileSizeMb),
        max_duration_min: Number(maxDurationMin),
        max_text_length_chars: Number(maxTextLengthChars),
        preview_truncate_chars: Number(previewTruncateChars),
        max_archive_size_mb: Number(maxArchiveSizeMb),
        max_archive_files_count: Number(maxArchiveFilesCount),
        max_archive_uncompressed_mb: Number(maxArchiveUncompressedMb),
        translatable_extensions: translatableExtensions,
      });
      setSuccess(true);
    } catch {
      setError(t("adminSettings.errorSave"));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="admin-settings-page">
      {isLoading ? (
        <p>{t("common.loading")}</p>
      ) : (
        <form onSubmit={handleSubmit} className="card settings-form">
          <div className="settings-columns">
            <div className="settings-column">
              <h2 className="settings-section-title">{t("adminSettings.columnTranscription")}</h2>
              <h3 className="settings-subsection-title">{t("adminSettings.audioSection")}</h3>
              <div className="field">
                <label htmlFor="max-size">{t("adminSettings.maxFileSize")}</label>
                <input
                  id="max-size"
                  type="number"
                  min="1"
                  step="1"
                  required
                  value={maxFileSizeMb}
                  onChange={(e) => setMaxFileSizeMb(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="max-duration">{t("adminSettings.maxDuration")}</label>
                <input
                  id="max-duration"
                  type="number"
                  min="0.1"
                  step="0.1"
                  required
                  value={maxDurationMin}
                  onChange={(e) => setMaxDurationMin(e.target.value)}
                />
              </div>

            </div>

            <div className="settings-column">
              <h2 className="settings-section-title">{t("adminSettings.columnTranslation")}</h2>
              <h3 className="settings-subsection-title">{t("adminSettings.textSection")}</h3>
              <div className="field">
                <label htmlFor="max-text-chars">{t("adminSettings.maxTextLength")}</label>
                <input
                  id="max-text-chars"
                  type="number"
                  min="1"
                  step="1"
                  required
                  value={maxTextLengthChars}
                  onChange={(e) => setMaxTextLengthChars(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="preview-chars">{t("adminSettings.previewChars")}</label>
                <input
                  id="preview-chars"
                  type="number"
                  min="1"
                  step="1"
                  required
                  value={previewTruncateChars}
                  onChange={(e) => setPreviewTruncateChars(e.target.value)}
                />
              </div>

              <h3 className="settings-subsection-title">{t("adminSettings.archiveSection")}</h3>
              <div className="field">
                <label htmlFor="max-archive-size">{t("adminSettings.maxArchiveSize")}</label>
                <input
                  id="max-archive-size"
                  type="number"
                  min="1"
                  step="1"
                  required
                  value={maxArchiveSizeMb}
                  onChange={(e) => setMaxArchiveSizeMb(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="max-archive-files">{t("adminSettings.maxArchiveFiles")}</label>
                <input
                  id="max-archive-files"
                  type="number"
                  min="1"
                  step="1"
                  required
                  value={maxArchiveFilesCount}
                  onChange={(e) => setMaxArchiveFilesCount(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="max-archive-uncompressed">
                  {t("adminSettings.maxArchiveUncompressed")}
                </label>
                <input
                  id="max-archive-uncompressed"
                  type="number"
                  min="1"
                  step="1"
                  required
                  value={maxArchiveUncompressedMb}
                  onChange={(e) => setMaxArchiveUncompressedMb(e.target.value)}
                />
              </div>

              <div className="field">
                <label htmlFor="translatable-extensions">{t("adminSettings.extensions")}</label>
                <input
                  id="translatable-extensions"
                  type="text"
                  required
                  value={translatableExtensions}
                  onChange={(e) => setTranslatableExtensions(e.target.value)}
                />
                <p className="settings-field-hint">{t("adminSettings.extensionsHint")}</p>
              </div>
            </div>
          </div>

          {error && <p className="error-text">{error}</p>}
          {success && <p className="success-text">{t("adminSettings.success")}</p>}

          <button type="submit" className="btn btn-primary" disabled={isSaving}>
            {isSaving ? t("common.saving") : t("common.save")}
          </button>
        </form>
      )}
    </div>
  );
}
