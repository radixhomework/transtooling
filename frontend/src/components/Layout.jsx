import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import "./Layout.css";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <div className="app-brand">
            <span className="app-brand-mark" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
            <span className="app-brand-name">TransTooLing</span>
          </div>

          <nav className="app-nav">
            <NavLink to="/" end className={({ isActive }) => (isActive ? "is-active" : "")}>
              Transcription
            </NavLink>
            <NavLink to="/translation" className={({ isActive }) => (isActive ? "is-active" : "")}>
              Traduction
            </NavLink>
            {user?.role === "admin" && (
              <>
                <NavLink to="/admin/users" className={({ isActive }) => (isActive ? "is-active" : "")}>
                  Utilisateurs
                </NavLink>
                <NavLink to="/admin/models" className={({ isActive }) => (isActive ? "is-active" : "")}>
                  Modèles
                </NavLink>
                <NavLink to="/admin/settings" className={({ isActive }) => (isActive ? "is-active" : "")}>
                  Paramètres
                </NavLink>
              </>
            )}
          </nav>

          <div className="app-account">
            <NavLink to="/account" className="app-account-email">
              {user?.login}
            </NavLink>
            <button className="btn btn-secondary btn-sm" onClick={handleLogout}>
              Déconnexion
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
