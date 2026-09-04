import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext.jsx";
import * as authApi from "../api/auth";
import "./AccountPage.css";

export default function AccountPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
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
  }

  return (
    <div className="account-page">
      <h1>{t("account.title")}</h1>

      <div className="card account-info">
        <div>
          <span className="account-info-label">{t("account.loginLabel")}</span>
          <span className="mono">{user?.login}</span>
        </div>
        <div>
          <span className="account-info-label">{t("account.roleLabel")}</span>
          <span className="mono">
            {user?.role === "admin" ? t("common.roleAdmin") : t("common.roleUser")}
          </span>
        </div>
      </div>

      <div className="card account-form-card">
        <h2>{t("account.changeTitle")}</h2>
        <form onSubmit={handleSubmit} className="account-form">
          <div className="field">
            <label htmlFor="current-password">{t("account.currentPassword")}</label>
            <input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="new-password">{t("account.newPassword")}</label>
            <input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="confirm-password">{t("account.confirmPassword")}</label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          {error && <p className="error-text">{error}</p>}
          {success && <p className="success-text">{t("account.success")}</p>}

          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? t("account.submitting") : t("account.submit")}
          </button>
        </form>
      </div>
    </div>
  );
}
