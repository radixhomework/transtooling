import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useLoginViewModel } from "./useLoginViewModel";

const loginMock = vi.fn();
const navigateMock = vi.fn();

vi.mock("./AuthContext/AuthContext", () => ({
  useAuth: () => ({ login: loginMock }),
}));

vi.mock("react-router-dom", async (importOriginal) => ({
  ...(await importOriginal()),
  useNavigate: () => navigateMock,
}));

function renderLogin() {
  return renderHook(() => useLoginViewModel(), {
    wrapper: ({ children }) => <MemoryRouter>{children}</MemoryRouter>,
  });
}

beforeEach(() => {
  loginMock.mockReset();
  navigateMock.mockReset();
});

describe("useLoginViewModel", () => {
  it("submits credentials and navigates home on success", async () => {
    loginMock.mockResolvedValue({});
    const { result } = renderLogin();

    act(() => {
      result.current.setLogin("admin");
      result.current.setPassword("Secret123");
    });
    await act(async () => {
      await result.current.submit();
    });

    expect(loginMock).toHaveBeenCalledWith("admin", "Secret123");
    expect(navigateMock).toHaveBeenCalledWith("/");
    expect(result.current.error).toBeNull();
    expect(result.current.isSubmitting).toBe(false);
  });

  it("maps a 429 response to the rate-limited message", async () => {
    loginMock.mockRejectedValue({ response: { status: 429 } });
    const { result } = renderLogin();

    await act(async () => {
      await result.current.submit();
    });
    expect(result.current.error).toBe("login.errorRateLimited");
  });

  it("maps a 403 response to the disabled-account message", async () => {
    loginMock.mockRejectedValue({ response: { status: 403 } });
    const { result } = renderLogin();

    await act(async () => {
      await result.current.submit();
    });
    expect(result.current.error).toBe("login.errorDisabled");
  });

  it("maps any other failure to the invalid-credentials message", async () => {
    loginMock.mockRejectedValue({ response: { status: 401 } });
    const { result } = renderLogin();

    await act(async () => {
      await result.current.submit();
    });
    expect(result.current.error).toBe("login.errorInvalid");
    expect(navigateMock).not.toHaveBeenCalled();
  });
});
