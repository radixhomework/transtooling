import { useTranslation } from "react-i18next";
import { useSettingsAdminViewModel } from "../../viewmodels/useSettingsAdminViewModel";
import "./AdminSettingsPage.css";

export default function AdminSettingsPage() {
  const { t } = useTranslation();
  const {
    maxFileSizeMb,
    maxDurationMin,
    maxTextLengthChars,
    previewTruncateChars,
    maxArchiveSizeMb,
    maxArchiveFilesCount,
    maxArchiveUncompressedMb,
    translatableExtensions,
    isLoading,
    isSaving,
    error,
    success,
    setMaxFileSizeMb,
    setMaxDurationMin,
    setMaxTextLengthChars,
    setPreviewTruncateChars,
    setMaxArchiveSizeMb,
    setMaxArchiveFilesCount,
    setMaxArchiveUncompressedMb,
    setTranslatableExtensions,
    save,
  } = useSettingsAdminViewModel();

  return (
    <div className="admin-settings-page">
      {isLoading ? (
        <p>{t("common.loading")}</p>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            save();
          }}
          className="card settings-form"
        >
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
