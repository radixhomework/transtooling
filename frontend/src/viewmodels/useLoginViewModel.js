import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "./AuthContext/AuthContext.jsx";

/**
 * ViewModel for the login view: credential form state and submission,
 * with HTTP-status-specific error messages.
 */
export function useLoginViewModel() {
  const { t } = useTranslation();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login: doLogin } = useAuth();
  const navigate = useNavigate();

  const submit = useCallback(async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      await doLogin(login, password);
      navigate("/");
    } catch (err) {
      const status = err.response?.status;
      if (status === 429) {
        setError(t("login.errorRateLimited"));
      } else if (status === 403) {
        setError(t("login.errorDisabled"));
      } else {
        setError(t("login.errorInvalid"));
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [doLogin, login, navigate, password, t]);

  return { login, password, error, isSubmitting, setLogin, setPassword, submit };
}
