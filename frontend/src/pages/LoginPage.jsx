import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext.jsx";
import { setLanguage } from "../i18n";
import "./LoginPage.css";

export default function LoginPage() {
  const { t, i18n } = useTranslation();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login: doLogin } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
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
  }

  return (
    <div className="login-page">
      <div className="login-card card">
        <div className="login-mark" aria-hidden="true">
          <img src="/logo-96.png" alt="" />
        </div>
        <h1>TransTooLing</h1>

        <div className="login-lang-switch" role="group" aria-label={t("nav.languageSwitch")}>
          <button
            className={i18n.language === "en" ? "is-active" : ""}
            onClick={() => setLanguage("en")}
          >
            EN
          </button>
          <button
            className={i18n.language === "fr" ? "is-active" : ""}
            onClick={() => setLanguage("fr")}
          >
            FR
          </button>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="field">
            <label htmlFor="login">{t("login.login")}</label>
            <input
              id="login"
              type="text"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="field">
            <label htmlFor="password">{t("login.password")}</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <p className="error-text">{error}</p>}

          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? t("login.submitting") : t("login.submit")}
          </button>
        </form>
      </div>
    </div>
  );
}
