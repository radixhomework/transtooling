import apiClient from "./client";

export function listUsers() {
  return apiClient.get("/users").then((r) => r.data);
}

export function createUser(login, password, role) {
  return apiClient.post("/users", { login, password, role }).then((r) => r.data);
}

export function updateUser(userId, payload) {
  return apiClient.patch(`/users/${userId}`, payload).then((r) => r.data);
}

export function resetUserPassword(userId, newPassword) {
  return apiClient.post(`/users/${userId}/reset-password`, { new_password: newPassword });
}

export function deleteUser(userId) {
  return apiClient.delete(`/users/${userId}`);
}
