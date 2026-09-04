import { useEffect, useState } from "react";
import * as settingsApi from "../api/appSettings";
import "./AdminSettingsPage.css";

export default function AdminSettingsPage() {
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
      .catch(() => setError("Impossible de charger les paramètres."))
      .finally(() => setIsLoading(false));
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
      setError(
        "Impossible d'enregistrer les paramètres. Vérifiez que les valeurs sont positives " +
          "et qu'au moins une extension traduisible est définie."
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="admin-settings-page">
      <div className="admin-page-header">
        <div>
          <h1>Paramètres</h1>
          <p>
            Taille et durée maximales des fichiers audio, et limites de la traduction
            (texte et archives ZIP).
          </p>
        </div>
      </div>

      {isLoading ? (
        <p>Chargement…</p>
      ) : (
        <form onSubmit={handleSubmit} className="card settings-form">
          <h2 className="settings-section-title">Upload audio</h2>
          <div className="field">
            <label htmlFor="max-size">Taille maximale d'un fichier audio (Mo)</label>
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
            <label htmlFor="max-duration">Durée maximale d'un fichier audio (minutes)</label>
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

          <h2 className="settings-section-title">Traduction — texte</h2>
          <div className="field">
            <label htmlFor="max-text-chars">Longueur maximale du texte (caractères)</label>
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
            <label htmlFor="preview-chars">Aperçu tronqué au-delà de (caractères)</label>
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

          <h2 className="settings-section-title">Traduction — archives ZIP</h2>
          <div className="field">
            <label htmlFor="max-archive-size">Taille maximale de l'archive (Mo)</label>
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
            <label htmlFor="max-archive-files">Nombre maximal de fichiers</label>
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
            <label htmlFor="max-archive-uncompressed">Taille décompressée maximale (Mo)</label>
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
            <label htmlFor="translatable-extensions">Extensions traduisibles (séparées par des virgules)</label>
            <input
              id="translatable-extensions"
              type="text"
              required
              value={translatableExtensions}
              onChange={(e) => setTranslatableExtensions(e.target.value)}
            />
            <p className="settings-field-hint">
              Les fichiers avec ces extensions sont traduits (JSON : valeurs de chaînes, clés
              préservées ; HTML : textes et attributs ; Markdown : syntaxe et chemins
              préservés). Les autres fichiers sont copiés tels quels.
            </p>
          </div>

          {error && <p className="error-text">{error}</p>}
          {success && <p className="success-text">Paramètres enregistrés.</p>}

          <button type="submit" className="btn btn-primary" disabled={isSaving}>
            {isSaving ? "Enregistrement..." : "Enregistrer"}
          </button>
        </form>
      )}
    </div>
  );
}
