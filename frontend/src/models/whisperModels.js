import apiClient from "./client";

export function listWhisperModels() {
  return apiClient.get("/admin/whisper-models").then((r) => r.data);
}

// Models usable for a transcription (downloaded + enabled),
// available to any authenticated user (upload selector).
export function listEnabledModels() {
  return apiClient.get("/models").then((r) => r.data);
}

export function downloadWhisperModel(name) {
  return apiClient.post(`/admin/whisper-models/${name}/download`);
}

export function deleteWhisperModel(name) {
  return apiClient.delete(`/admin/whisper-models/${name}`);
}

export function updateWhisperModel(name, payload) {
  return apiClient.patch(`/admin/whisper-models/${name}`, payload).then((r) => r.data);
}
