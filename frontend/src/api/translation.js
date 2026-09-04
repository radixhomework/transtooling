import apiClient from "./client";

// --- Partie utilisateur ---

export function listEnabledDirections() {
  return apiClient.get("/translation/models").then((r) => r.data);
}

export function createTextJob(direction, text) {
  return apiClient.post("/translation/jobs", { direction, text }).then((r) => r.data);
}

export function createArchiveJob(file, direction, onUploadProgress) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("direction", direction);
  return apiClient
    .post("/translation/jobs/archive", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress,
    })
    .then((r) => r.data);
}

export function listTranslationJobs() {
  return apiClient.get("/translation/jobs").then((r) => r.data);
}

export function downloadTranslationJob(jobId) {
  return apiClient
    .get(`/translation/jobs/${jobId}/download`, { responseType: "blob" })
    .then((r) => r.data);
}

export function deleteTranslationJob(jobId) {
  return apiClient.delete(`/translation/jobs/${jobId}`);
}

export function cancelTranslationJob(jobId) {
  return apiClient.post(`/translation/jobs/${jobId}/cancel`);
}

// --- Admin part (translation models) ---

export function listTranslationModels() {
  return apiClient.get("/admin/translation-models").then((r) => r.data);
}

export function downloadTranslationModel(direction) {
  return apiClient.post(`/admin/translation-models/${direction}/download`);
}

export function deleteTranslationModel(direction) {
  return apiClient.delete(`/admin/translation-models/${direction}`);
}

export function updateTranslationModel(direction, payload) {
  return apiClient
    .patch(`/admin/translation-models/${direction}`, payload)
    .then((r) => r.data);
}
