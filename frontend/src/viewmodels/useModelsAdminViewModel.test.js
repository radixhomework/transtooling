import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useModelsAdminViewModel } from "./useModelsAdminViewModel";

const modelsApi = vi.hoisted(() => ({
  listWhisperModels: vi.fn(),
  downloadWhisperModel: vi.fn(),
  updateWhisperModel: vi.fn(),
  deleteWhisperModel: vi.fn(),
}));
const translationApi = vi.hoisted(() => ({
  listTranslationModels: vi.fn(),
  downloadTranslationModel: vi.fn(),
  updateTranslationModel: vi.fn(),
  deleteTranslationModel: vi.fn(),
}));

vi.mock("../models/whisperModels", () => modelsApi);
vi.mock("../models/translation", () => translationApi);

const WHISPER = [
  { name: "tiny", status: "downloaded", is_enabled: true, is_default: true },
  { name: "base", status: "not_downloaded", is_enabled: false, is_default: false },
];
const TRANSLATION = [
  { direction: "fr-en", status: "downloading", is_enabled: false, download_progress: 40 },
];

beforeEach(() => {
  vi.clearAllMocks();
  modelsApi.listWhisperModels.mockResolvedValue(WHISPER.map((m) => ({ ...m })));
  translationApi.listTranslationModels.mockResolvedValue(TRANSLATION.map((m) => ({ ...m })));
});

describe("useModelsAdminViewModel", () => {
  it("loads both model catalogs", async () => {
    const { result } = renderHook(() => useModelsAdminViewModel());

    await waitFor(() => expect(result.current.whisper.models).toHaveLength(2));
    await waitFor(() => expect(result.current.translation.models).toHaveLength(1));
    expect(result.current.whisper.isLoading).toBe(false);
    expect(result.current.translation.isLoading).toBe(false);
  });

  it("wraps a whisper download between busy flags and refreshes", async () => {
    // Deferred promise: keeps the action in flight so the busy flag can be
    // observed before completion.
    let resolveDownload;
    modelsApi.downloadWhisperModel.mockReturnValue(
      new Promise((resolve) => {
        resolveDownload = resolve;
      })
    );
    const { result } = renderHook(() => useModelsAdminViewModel());
    await waitFor(() => expect(result.current.whisper.isLoading).toBe(false));

    let promise;
    act(() => {
      promise = result.current.whisper.download("base");
    });
    await waitFor(() => expect(result.current.whisper.busyKey).toBe("base"));

    await act(async () => {
      resolveDownload();
      await promise;
    });

    expect(modelsApi.downloadWhisperModel).toHaveBeenCalledWith("base");
    await waitFor(() => {
      expect(result.current.whisper.busyKey).toBeNull();
      expect(modelsApi.listWhisperModels).toHaveBeenCalledTimes(2);
    });
  });

  it("reports the backend detail when an action fails", async () => {
    modelsApi.updateWhisperModel.mockRejectedValue({
      response: { data: { detail: "Le modèle doit être téléchargé" } },
    });
    const { result } = renderHook(() => useModelsAdminViewModel());
    await waitFor(() => expect(result.current.whisper.isLoading).toBe(false));

    await result.current.whisper.update("base", { is_enabled: true });
    await waitFor(() => expect(result.current.whisper.error).toBe("Le modèle doit être téléchargé"));
  });

  it("wraps translation model actions the same way", async () => {
    translationApi.deleteTranslationModel.mockResolvedValue({});
    const { result } = renderHook(() => useModelsAdminViewModel());
    await waitFor(() => expect(result.current.translation.isLoading).toBe(false));

    await result.current.translation.remove("fr-en");
    expect(translationApi.deleteTranslationModel).toHaveBeenCalledWith("fr-en");
    await waitFor(() => expect(result.current.translation.busyKey).toBeNull());
  });
});
