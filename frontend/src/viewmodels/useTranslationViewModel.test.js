import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useTranslationViewModel } from "./useTranslationViewModel";

const translationApi = vi.hoisted(() => ({
  listEnabledDirections: vi.fn(),
  listTranslationJobs: vi.fn(),
  createTextJob: vi.fn(),
  createArchiveJob: vi.fn(),
  cancelTranslationJob: vi.fn(),
  deleteTranslationJob: vi.fn(),
  downloadTranslationJob: vi.fn(),
}));

vi.mock("../models/translation", () => translationApi);

beforeEach(() => {
  vi.clearAllMocks();
  translationApi.listEnabledDirections.mockResolvedValue([]);
  translationApi.listTranslationJobs.mockResolvedValue([]);
});

describe("useTranslationViewModel", () => {
  it("loads directions and preselects the first one", async () => {
    translationApi.listEnabledDirections.mockResolvedValue([
      { direction: "fr-en" },
      { direction: "en-fr" },
    ]);

    const { result } = renderHook(() => useTranslationViewModel());

    await waitFor(() => expect(result.current.directions).toHaveLength(2));
    expect(result.current.direction).toBe("fr-en");
    expect(result.current.hasActiveModel).toBe(true);
  });

  it("reports no active model when the API returns nothing", async () => {
    const { result } = renderHook(() => useTranslationViewModel());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.hasActiveModel).toBe(false);
  });

  it("submits the text job then clears the textarea and refreshes", async () => {
    translationApi.listEnabledDirections.mockResolvedValue([{ direction: "fr-en" }]);
    translationApi.createTextJob.mockResolvedValue({});

    const { result } = renderHook(() => useTranslationViewModel());
    await waitFor(() => expect(result.current.direction).toBe("fr-en"));

    act(() => {
      result.current.setText("Bonjour");
    });
    await act(async () => {
      await result.current.submitText();
    });

    expect(translationApi.createTextJob).toHaveBeenCalledWith("fr-en", "Bonjour");
    expect(result.current.text).toBe("");
    expect(result.current.error).toBeNull();
  });

  it("does not submit an empty text", async () => {
    translationApi.listEnabledDirections.mockResolvedValue([{ direction: "fr-en" }]);

    const { result } = renderHook(() => useTranslationViewModel());
    await waitFor(() => expect(result.current.direction).toBe("fr-en"));

    act(() => {
      result.current.setText("   ");
    });
    await act(async () => {
      await result.current.submitText();
    });

    expect(translationApi.createTextJob).not.toHaveBeenCalled();
  });

  it("surfaces the backend detail when the text job is rejected", async () => {
    translationApi.listEnabledDirections.mockResolvedValue([{ direction: "fr-en" }]);
    translationApi.createTextJob.mockRejectedValue({
      response: { data: { detail: "Texte trop long" } },
    });

    const { result } = renderHook(() => useTranslationViewModel());
    await waitFor(() => expect(result.current.direction).toBe("fr-en"));

    act(() => {
      result.current.setText("Bonjour");
    });
    await act(async () => {
      await result.current.submitText();
    });
    expect(result.current.error).toBe("Texte trop long");
  });

  it("uploads the archive with progress reporting then refreshes", async () => {
    translationApi.listEnabledDirections.mockResolvedValue([{ direction: "en-fr" }]);
    translationApi.createArchiveJob.mockImplementation(
      (file, direction, onProgress) => {
        onProgress({ loaded: 50, total: 100 });
        return Promise.resolve({});
      }
    );

    const { result } = renderHook(() => useTranslationViewModel());
    await waitFor(() => expect(result.current.direction).toBe("en-fr"));

    const file = new File(["zip"], "archive.zip");
    act(() => {
      result.current.setArchiveFile(file);
    });
    await act(async () => {
      await result.current.submitArchive();
    });

    expect(translationApi.createArchiveJob).toHaveBeenCalledWith(
      file,
      "en-fr",
      expect.any(Function)
    );
    expect(result.current.archiveFile).toBeNull();
    expect(result.current.uploadPercent).toBe(0);
  });

  it("deletes a job locally after confirmation", async () => {
    translationApi.listTranslationJobs.mockResolvedValue([
      { id: 9, status: "done", job_type: "text", direction: "fr-en", created_at: "2026-01-01" },
    ]);
    translationApi.deleteTranslationJob.mockResolvedValue({});
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    const { result } = renderHook(() => useTranslationViewModel());
    await waitFor(() => expect(result.current.jobs).toHaveLength(1));

    await act(async () => {
      await result.current.deleteJob(result.current.jobs[0]);
    });
    expect(translationApi.deleteTranslationJob).toHaveBeenCalledWith(9);
    expect(result.current.jobs).toHaveLength(0);
    confirmSpy.mockRestore();
  });
});
