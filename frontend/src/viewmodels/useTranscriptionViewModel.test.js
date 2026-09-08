import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useTranscriptionViewModel } from "./useTranscriptionViewModel";

const jobsApi = vi.hoisted(() => ({
  listJobs: vi.fn(),
  createJob: vi.fn(),
  cancelJob: vi.fn(),
  deleteJob: vi.fn(),
  downloadJobUrl: vi.fn(),
}));
const modelsApi = vi.hoisted(() => ({
  listEnabledModels: vi.fn(),
}));

vi.mock("../models/jobs", () => jobsApi);
vi.mock("../models/whisperModels", () => modelsApi);

function recentJob(id, createdAt, status = "done") {
  return {
    id,
    filename_original: `audio${id}.wav`,
    status,
    created_at: createdAt,
    progress: null,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  jobsApi.listJobs.mockResolvedValue([]);
  modelsApi.listEnabledModels.mockResolvedValue([]);
});

describe("useTranscriptionViewModel", () => {
  it("loads the job list sorted by descending creation date", async () => {
    jobsApi.listJobs.mockResolvedValue([
      recentJob(1, "2026-01-01T10:00:00Z"),
      recentJob(2, "2026-01-02T10:00:00Z"),
    ]);

    const { result } = renderHook(() => useTranscriptionViewModel());

    await waitFor(() => expect(result.current.isLoadingJobs).toBe(false));
    expect(result.current.jobs.map((j) => j.id)).toEqual([2, 1]);
  });

  it("keeps polling silent on network errors and clears the loading state", async () => {
    jobsApi.listJobs.mockRejectedValue(new Error("network down"));

    const { result } = renderHook(() => useTranscriptionViewModel());

    await waitFor(() => expect(result.current.isLoadingJobs).toBe(false));
    expect(result.current.jobs).toEqual([]);
  });

  it("uploads the selected file with the chosen model then refreshes", async () => {
    jobsApi.createJob.mockResolvedValue({});
    modelsApi.listEnabledModels.mockResolvedValue([
      { name: "tiny", is_default: true },
      { name: "small", is_default: false },
    ]);

    const { result } = renderHook(() => useTranscriptionViewModel());
    await waitFor(() => expect(result.current.enabledModels).toHaveLength(2));

    const file = new File(["audio"], "audio.wav");
    await act(async () => {
      await result.current.uploadFile(file);
    });

    expect(jobsApi.createJob).toHaveBeenCalledWith(file, expect.any(Function), undefined);
    expect(jobsApi.listJobs).toHaveBeenCalled();
    expect(result.current.isUploading).toBe(false);
    expect(result.current.uploadProgress).toBe(0);
  });

  it("surfaces the backend error detail when the upload is rejected", async () => {
    jobsApi.createJob.mockRejectedValue({
      response: { data: { detail: "Fichier trop volumineux" } },
    });

    const { result } = renderHook(() => useTranscriptionViewModel());
    await act(async () => {
      await result.current.uploadFile(new File(["audio"], "audio.wav"));
    });

    expect(result.current.uploadError).toBe("Fichier trop volumineux");
  });

  it("falls back to the generic upload error without a backend detail", async () => {
    jobsApi.createJob.mockRejectedValue({});
    const { result } = renderHook(() => useTranscriptionViewModel());

    await act(async () => {
      await result.current.uploadFile(new File(["audio"], "audio.wav"));
    });
    expect(result.current.uploadError).toBe("dashboard.errorUpload");
  });

  it("cancels a job then refreshes the list", async () => {
    jobsApi.cancelJob.mockResolvedValue({});
    const { result } = renderHook(() => useTranscriptionViewModel());

    await act(async () => {
      await result.current.cancelJob({ id: 7 });
    });
    expect(jobsApi.cancelJob).toHaveBeenCalledWith(7);
    expect(jobsApi.listJobs).toHaveBeenCalled();
  });

  it("deletes a job locally after confirmation", async () => {
    jobsApi.listJobs.mockResolvedValue([recentJob(3, "2026-01-03T10:00:00Z")]);
    jobsApi.deleteJob.mockResolvedValue({});
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    const { result } = renderHook(() => useTranscriptionViewModel());
    await waitFor(() => expect(result.current.jobs).toHaveLength(1));

    await act(async () => {
      await result.current.deleteJob(result.current.jobs[0]);
    });
    expect(jobsApi.deleteJob).toHaveBeenCalledWith(3);
    expect(result.current.jobs).toHaveLength(0);
    confirmSpy.mockRestore();
  });

  it("keeps the job when the user dismisses the confirmation", async () => {
    jobsApi.listJobs.mockResolvedValue([recentJob(3, "2026-01-03T10:00:00Z")]);
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

    const { result } = renderHook(() => useTranscriptionViewModel());
    await waitFor(() => expect(result.current.jobs).toHaveLength(1));

    await act(async () => {
      await result.current.deleteJob(result.current.jobs[0]);
    });
    expect(jobsApi.deleteJob).not.toHaveBeenCalled();
    expect(result.current.jobs).toHaveLength(1);
    confirmSpy.mockRestore();
  });

  it("downloads the blob under the expected file name", async () => {
    jobsApi.downloadJobUrl.mockResolvedValue(new Blob(["vtt data"]));
    if (!window.URL.createObjectURL) {
      window.URL.createObjectURL = () => "blob:mock";
      window.URL.revokeObjectURL = () => {};
    }
    const urlSpy = vi
      .spyOn(window.URL, "createObjectURL")
      .mockReturnValue("blob:mock");
    const revokeSpy = vi.spyOn(window.URL, "revokeObjectURL").mockImplementation(() => {});

    const { result } = renderHook(() => useTranscriptionViewModel());
    await act(async () => {
      await result.current.downloadJob(
        { id: 5, filename_original: "meeting.wav" },
        "txt"
      );
    });

    expect(jobsApi.downloadJobUrl).toHaveBeenCalledWith(5, "txt");
    urlSpy.mockRestore();
    revokeSpy.mockRestore();
  });
});
