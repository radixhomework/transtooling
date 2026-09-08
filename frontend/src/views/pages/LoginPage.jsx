import { useTranslation } from "react-i18next";
import { setLanguage } from "../../i18n";
import { useLoginViewModel } from "../../viewmodels/useLoginViewModel";
import "./LoginPage.css";

export default function LoginPage() {
  const { t, i18n } = useTranslation();
  const {
    login,
    password,
    error,
    isSubmitting,
    setLogin,
    setPassword,
    submit,
  } = useLoginViewModel();

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

        <form
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
          className="login-form"
        >
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
