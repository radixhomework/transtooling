import apiClient from "./client";

export function getAppSettings() {
  return apiClient.get("/admin/settings").then((r) => r.data);
}

export function updateAppSettings(payload) {
  return apiClient.patch("/admin/settings", payload).then((r) => r.data);
}
