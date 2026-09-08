import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useSettingsAdminViewModel } from "./useSettingsAdminViewModel";

const settingsApi = vi.hoisted(() => ({
  getAppSettings: vi.fn(),
  updateAppSettings: vi.fn(),
}));

vi.mock("../models/appSettings", () => settingsApi);

const SETTINGS = {
  max_file_size_mb: 500,
  max_duration_min: 120,
  max_text_length_chars: 20000,
  preview_truncate_chars: 4000,
  max_archive_size_mb: 200,
  max_archive_files_count: 300,
  max_archive_uncompressed_mb: 800,
  translatable_extensions: "json,html,htm,md",
};

beforeEach(() => {
  vi.clearAllMocks();
  settingsApi.getAppSettings.mockResolvedValue({ ...SETTINGS });
  settingsApi.updateAppSettings.mockResolvedValue({});
});

describe("useSettingsAdminViewModel", () => {
  it("populates the form from the loaded settings", async () => {
    const { result } = renderHook(() => useSettingsAdminViewModel());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.maxFileSizeMb).toBe("500");
    expect(result.current.maxDurationMin).toBe("120");
    expect(result.current.translatableExtensions).toBe("json,html,htm,md");
    expect(result.current.error).toBeNull();
  });

  it("surfaces a load error", async () => {
    settingsApi.getAppSettings.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useSettingsAdminViewModel());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.error).toBe("adminSettings.errorLoad");
  });

  it("sends numeric values on save and reports success", async () => {
    const { result } = renderHook(() => useSettingsAdminViewModel());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.setMaxFileSizeMb("256");
    });
    await act(async () => {
      await result.current.save();
    });

    expect(settingsApi.updateAppSettings).toHaveBeenCalledWith({
      ...SETTINGS,
      max_file_size_mb: 256,
    });
    expect(result.current.success).toBe(true);
  });

  it("surfaces a save error", async () => {
    settingsApi.updateAppSettings.mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useSettingsAdminViewModel());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.save();
    });
    expect(result.current.error).toBe("adminSettings.errorSave");
    expect(result.current.success).toBe(false);
  });
});
