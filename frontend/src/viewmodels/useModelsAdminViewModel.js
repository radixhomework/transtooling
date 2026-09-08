import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import * as modelsApi from "../models/whisperModels";
import * as translationApi from "../models/translation";

const POLL_INTERVAL_MS = 4000;

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

/**
 * ViewModel for the admin models screen: Whisper models and translation
 * models, with download / enable / disable / default / delete actions and
 * polling while a download is in flight.
 */
export function useModelsAdminViewModel() {
  const whisper = useModels(useCallback(() => modelsApi.listWhisperModels(), []));
  const translation = useModels(useCallback(() => translationApi.listTranslationModels(), []));

  const downloadWhisper = useCallback(
    (name) => whisper.withBusy(name, () => modelsApi.downloadWhisperModel(name)),
    [whisper]
  );
  const updateWhisper = useCallback(
    (name, patch) => whisper.withBusy(name, () => modelsApi.updateWhisperModel(name, patch)),
    [whisper]
  );
  const deleteWhisper = useCallback(
    (name) => whisper.withBusy(name, () => modelsApi.deleteWhisperModel(name)),
    [whisper]
  );

  const downloadTranslation = useCallback(
    (direction) =>
      translation.withBusy(direction, () => translationApi.downloadTranslationModel(direction)),
    [translation]
  );
  const updateTranslation = useCallback(
    (direction, patch) =>
      translation.withBusy(direction, () => translationApi.updateTranslationModel(direction, patch)),
    [translation]
  );
  const deleteTranslation = useCallback(
    (direction) =>
      translation.withBusy(direction, () => translationApi.deleteTranslationModel(direction)),
    [translation]
  );

  return {
    whisper: {
      ...whisper,
      download: downloadWhisper,
      update: updateWhisper,
      remove: deleteWhisper,
    },
    translation: {
      ...translation,
      download: downloadTranslation,
      update: updateTranslation,
      remove: deleteTranslation,
    },
  };
}
