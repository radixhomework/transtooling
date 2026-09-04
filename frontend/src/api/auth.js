import apiClient from "./client";

export function login(login, password) {
  return apiClient.post("/auth/login", { login, password }).then((r) => r.data);
}

export function changePassword(currentPassword, newPassword) {
  return apiClient
    .post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    })
    .then((r) => r.data);
}

export function getMe() {
  return apiClient.get("/users/me").then((r) => r.data);
}
