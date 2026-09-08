import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import * as authApi from "../models/auth";

/**
 * ViewModel for the account view: password change form state and submission.
 */
export function usePasswordChangeViewModel() {
  const { t } = useTranslation();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const submit = useCallback(async () => {
    setError(null);
    setSuccess(false);

    if (newPassword !== confirmPassword) {
      setError(t("account.errorMismatch"));
      return;
    }

    setIsSubmitting(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      setSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      const status = err.response?.status;
      if (status === 400) {
        setError(t("account.errorCurrent"));
      } else if (status === 422) {
        setError(t("account.errorPolicy"));
      } else {
        setError(t("account.errorGeneric"));
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [confirmPassword, currentPassword, newPassword, t]);

  return {
    currentPassword,
    newPassword,
    confirmPassword,
    error,
    success,
    isSubmitting,
    setCurrentPassword,
    setNewPassword,
    setConfirmPassword,
    submit,
  };
}
