import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "./AuthContext";

const authApi = vi.hoisted(() => ({
  login: vi.fn(),
  getMe: vi.fn(),
}));

vi.mock("../../models/auth", () => authApi);

function useTestAuth() {
  return useAuth();
}

function renderAuthProvider(initialUser = null) {
  return renderHook(() => useTestAuth(), {
    wrapper: ({ children }) => <AuthProvider>{children}</AuthProvider>,
  });
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe("AuthContext", () => {
  it("starts unauthenticated without a stored token", async () => {
    const { result } = renderAuthProvider();

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toBeNull();
    expect(authApi.getMe).not.toHaveBeenCalled();
  });

  it("restores the session from a stored token", async () => {
    localStorage.setItem("access_token", "token-abc");
    authApi.getMe.mockResolvedValue({ id: 1, login: "admin" });

    const { result } = renderAuthProvider();

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toEqual({ id: 1, login: "admin" });
  });

  it("clears the stored tokens when the session restore is rejected", async () => {
    localStorage.setItem("access_token", "expired");
    localStorage.setItem("refresh_token", "expired-refresh");
    authApi.getMe.mockRejectedValue(new Error("401"));

    const { result } = renderAuthProvider();

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.user).toBeNull();
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });

  it("login stores the tokens and loads the profile", async () => {
    authApi.login.mockResolvedValue({ access_token: "at", refresh_token: "rt" });
    authApi.getMe.mockResolvedValue({ id: 2, login: "bob" });

    const { result } = renderAuthProvider();
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.login("bob", "Secret123");
    });

    expect(localStorage.getItem("access_token")).toBe("at");
    expect(localStorage.getItem("refresh_token")).toBe("rt");
    expect(result.current.user).toEqual({ id: 2, login: "bob" });
  });

  it("logout clears the tokens and the user", async () => {
    localStorage.setItem("access_token", "at");
    localStorage.setItem("refresh_token", "rt");
    authApi.getMe.mockResolvedValue({ id: 1, login: "admin" });

    const { result } = renderAuthProvider();
    await waitFor(() => expect(result.current.user).not.toBeNull());

    act(() => {
      result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });
});
