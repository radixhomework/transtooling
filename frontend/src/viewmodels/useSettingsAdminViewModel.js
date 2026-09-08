import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import * as settingsApi from "../models/appSettings";

/**
 * ViewModel for the admin settings screen: loads the singleton settings,
 * holds the form state and saves it back.
 */
export function useSettingsAdminViewModel() {
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

  const save = useCallback(async () => {
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
  }, [
    maxArchiveFilesCount,
    maxArchiveSizeMb,
    maxArchiveUncompressedMb,
    maxDurationMin,
    maxFileSizeMb,
    maxTextLengthChars,
    previewTruncateChars,
    t,
    translatableExtensions,
  ]);

  return {
    // state
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
    // actions / setters
    setMaxFileSizeMb,
    setMaxDurationMin,
    setMaxTextLengthChars,
    setPreviewTruncateChars,
    setMaxArchiveSizeMb,
    setMaxArchiveFilesCount,
    setMaxArchiveUncompressedMb,
    setTranslatableExtensions,
    save,
  };
}
