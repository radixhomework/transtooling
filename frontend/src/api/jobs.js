import apiClient from "./client";

export function listJobs() {
  return apiClient.get("/jobs").then((r) => r.data);
}

export function getJob(jobId) {
  return apiClient.get(`/jobs/${jobId}`).then((r) => r.data);
}

export function createJob(file, onUploadProgress, modelName) {
  const formData = new FormData();
  formData.append("file", file);
  if (modelName) {
    formData.append("model", modelName);
  }
  return apiClient
    .post("/jobs", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress,
    })
    .then((r) => r.data);
}

export function deleteJob(jobId) {
  return apiClient.delete(`/jobs/${jobId}`);
}

export function cancelJob(jobId) {
  return apiClient.post(`/jobs/${jobId}/cancel`);
}

export function downloadJobUrl(jobId, format = "vtt") {
  // A token is required, so we download through a blob rather than a direct link.
  return apiClient
    .get(`/jobs/${jobId}/download`, { params: { format }, responseType: "blob" })
    .then((r) => r.data);
}
