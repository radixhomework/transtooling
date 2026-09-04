import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext.jsx";
import { setLanguage } from "../i18n";
import "./Layout.css";

export default function Layout() {
  const { t, i18n } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  function switchTo(lang) {
    setLanguage(lang);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <div className="app-brand">
            <img className="app-brand-logo" src="/logo-96.png" alt="" aria-hidden="true" />
            <span className="app-brand-name">TransTooLing</span>
          </div>

          <nav className="app-nav">
            <NavLink to="/" end className={({ isActive }) => (isActive ? "is-active" : "")}>
              {t("nav.transcription")}
            </NavLink>
            <NavLink to="/translation" className={({ isActive }) => (isActive ? "is-active" : "")}>
              {t("nav.translation")}
            </NavLink>
            {user?.role === "admin" && (
              <NavLink to="/admin" className={({ isActive }) => (isActive ? "is-active" : "")}>
                {t("nav.admin")}
              </NavLink>
            )}
          </nav>

          <div className="app-account">
            <div className="lang-switch" role="group" aria-label={t("nav.languageSwitch")}>
              <button
                className={i18n.language === "en" ? "is-active" : ""}
                onClick={() => switchTo("en")}
              >
                EN
              </button>
              <button
                className={i18n.language === "fr" ? "is-active" : ""}
                onClick={() => switchTo("fr")}
              >
                FR
              </button>
            </div>
            <NavLink to="/account" className="app-account-email">
              {user?.login}
            </NavLink>
            <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
              {t("nav.logout")}
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
