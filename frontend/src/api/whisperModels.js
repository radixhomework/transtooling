import apiClient from "./client";

export function listWhisperModels() {
  return apiClient.get("/admin/whisper-models").then((r) => r.data);
}

// Modèles utilisables pour une transcription (téléchargés + activés),
// accessibles à tout utilisateur authentifié (sélecteur d'upload).
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
