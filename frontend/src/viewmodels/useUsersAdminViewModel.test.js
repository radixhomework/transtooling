import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useUsersAdminViewModel } from "./useUsersAdminViewModel";

const usersApi = vi.hoisted(() => ({
  listUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  deleteUser: vi.fn(),
  resetUserPassword: vi.fn(),
}));

vi.mock("../models/users", () => usersApi);

beforeEach(() => {
  vi.clearAllMocks();
  usersApi.listUsers.mockResolvedValue([]);
});

describe("useUsersAdminViewModel", () => {
  it("loads users sorted by login", async () => {
    usersApi.listUsers.mockResolvedValue([
      { id: 1, login: "zoe" },
      { id: 2, login: "adam" },
    ]);

    const { result } = renderHook(() => useUsersAdminViewModel());

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.users.map((u) => u.login)).toEqual(["adam", "zoe"]);
  });

  it("creates the user, closes the form and refreshes", async () => {
    usersApi.createUser.mockResolvedValue({});
    const { result } = renderHook(() => useUsersAdminViewModel());

    act(() => {
      result.current.setShowCreateForm(true);
      result.current.setNewUser({ login: "new-user", password: "Secret123", role: "user" });
    });
    await act(async () => {
      await result.current.submitCreate();
    });

    expect(usersApi.createUser).toHaveBeenCalledWith("new-user", "Secret123", "user");
    expect(result.current.showCreateForm).toBe(false);
    expect(result.current.newUser).toEqual({ login: "", password: "", role: "user" });
  });

  it("maps a 400 creation failure to the login-taken message", async () => {
    usersApi.createUser.mockRejectedValue({ response: { status: 400 } });
    const { result } = renderHook(() => useUsersAdminViewModel());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.setShowCreateForm(true);
      result.current.setNewUser({ login: "taken", password: "Secret123", role: "user" });
    });
    await act(async () => {
      await result.current.submitCreate();
    });
    expect(result.current.createError).toBe("adminUsers.errorLoginTaken");
    // The form stays open so the admin can fix the login.
    expect(result.current.showCreateForm).toBe(true);
    expect(result.current.isCreating).toBe(false);
  });

  it("maps a 422 creation failure to the password-policy message", async () => {
    usersApi.createUser.mockRejectedValue({ response: { status: 422 } });
    const { result } = renderHook(() => useUsersAdminViewModel());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.setNewUser({ login: "weak", password: "weak", role: "user" });
    });
    await act(async () => {
      await result.current.submitCreate();
    });
    expect(result.current.createError).toBe("adminUsers.errorPolicy");
  });

  it("toggles the active state and refreshes", async () => {
    usersApi.updateUser.mockResolvedValue({});
    const { result } = renderHook(() => useUsersAdminViewModel());

    await act(async () => {
      await result.current.toggleActive({ id: 4, is_active: true });
    });
    expect(usersApi.updateUser).toHaveBeenCalledWith(4, { is_active: false });
  });

  it("confirms before toggling the role", async () => {
    usersApi.updateUser.mockResolvedValue({});
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const { result } = renderHook(() => useUsersAdminViewModel());
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      await result.current.toggleRole({ id: 4, login: "bob", role: "user" });
    });
    expect(usersApi.updateUser).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("deletes after confirmation and refreshes", async () => {
    usersApi.deleteUser.mockResolvedValue({});
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const { result } = renderHook(() => useUsersAdminViewModel());

    await act(async () => {
      await result.current.deleteUser({ id: 5, login: "gone" });
    });
    expect(usersApi.deleteUser).toHaveBeenCalledWith(5);
    confirmSpy.mockRestore();
  });

  it("submits the password reset and closes the modal", async () => {
    usersApi.resetUserPassword.mockResolvedValue({});
    const { result } = renderHook(() => useUsersAdminViewModel());

    act(() => {
      result.current.openResetModal({ id: 6 });
      result.current.setResetPassword("NewPass123");
    });
    await act(async () => {
      await result.current.submitResetPassword();
    });

    expect(usersApi.resetUserPassword).toHaveBeenCalledWith(6, "NewPass123");
    expect(result.current.resetTargetId).toBeNull();
  });

  it("maps a 422 reset failure to the policy message and keeps the modal open", async () => {
    usersApi.resetUserPassword.mockRejectedValue({ response: { status: 422 } });
    const { result } = renderHook(() => useUsersAdminViewModel());

    act(() => {
      result.current.openResetModal({ id: 6 });
      result.current.setResetPassword("weak");
    });
    await act(async () => {
      await result.current.submitResetPassword();
    });
    expect(result.current.resetError).toBe("adminUsers.errorPolicy");
    expect(result.current.resetTargetId).not.toBeNull();
  });
});
