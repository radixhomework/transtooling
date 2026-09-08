import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePasswordChangeViewModel } from "./usePasswordChangeViewModel";

const changePasswordMock = vi.fn();

vi.mock("../models/auth", () => ({
  changePassword: (...args) => changePasswordMock(...args),
}));

beforeEach(() => {
  changePasswordMock.mockReset();
});

function fill(result, { current = "OldPass123", next = "NewPass456", confirm = next } = {}) {
  act(() => {
    result.current.setCurrentPassword(current);
    result.current.setNewPassword(next);
    result.current.setConfirmPassword(confirm);
  });
}

describe("usePasswordChangeViewModel", () => {
  it("rejects mismatched confirmation before calling the API", async () => {
    const { result } = renderHook(() => usePasswordChangeViewModel());
    fill(result, { confirm: "Different456" });

    await act(async () => {
      await result.current.submit();
    });

    expect(changePasswordMock).not.toHaveBeenCalled();
    expect(result.current.error).toBe("account.errorMismatch");
  });

  it("stores the new password and clears the form on success", async () => {
    changePasswordMock.mockResolvedValue({});
    const { result } = renderHook(() => usePasswordChangeViewModel());
    fill(result, {});

    await act(async () => {
      await result.current.submit();
    });

    expect(changePasswordMock).toHaveBeenCalledWith("OldPass123", "NewPass456");
    expect(result.current.success).toBe(true);
    expect(result.current.currentPassword).toBe("");
    expect(result.current.newPassword).toBe("");
    expect(result.current.confirmPassword).toBe("");
  });

  it("maps a 400 response to the wrong-current-password message", async () => {
    changePasswordMock.mockRejectedValue({ response: { status: 400 } });
    const { result } = renderHook(() => usePasswordChangeViewModel());
    fill(result, {});

    await act(async () => {
      await result.current.submit();
    });
    expect(result.current.error).toBe("account.errorCurrent");
  });

  it("maps a 422 response to the policy message", async () => {
    changePasswordMock.mockRejectedValue({ response: { status: 422 } });
    const { result } = renderHook(() => usePasswordChangeViewModel());
    fill(result, {});

    await act(async () => {
      await result.current.submit();
    });
    expect(result.current.error).toBe("account.errorPolicy");
  });
});
