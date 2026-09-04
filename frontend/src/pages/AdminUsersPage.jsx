import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import * as usersApi from "../api/users";
import "./AdminUsersPage.css";

function emptyNewUser() {
  return { login: "", password: "", role: "user" };
}

export default function AdminUsersPage() {
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newUser, setNewUser] = useState(emptyNewUser());
  const [createError, setCreateError] = useState(null);
  const [isCreating, setIsCreating] = useState(false);

  const [resetTargetId, setResetTargetId] = useState(null);
  const [resetPassword, setResetPassword] = useState("");
  const [resetError, setResetError] = useState(null);

  async function fetchUsers() {
    setIsLoading(true);
    try {
      const data = await usersApi.listUsers();
      data.sort((a, b) => a.login.localeCompare(b.login));
      setUsers(data);
    } catch {
      setError(t("adminUsers.errorLoad"));
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setCreateError(null);
    setIsCreating(true);
    try {
      await usersApi.createUser(newUser.login, newUser.password, newUser.role);
      setNewUser(emptyNewUser());
      setShowCreateForm(false);
      await fetchUsers();
    } catch (err) {
      const status = err.response?.status;
      if (status === 400) {
        setCreateError(t("adminUsers.errorLoginTaken"));
      } else if (status === 422) {
        setCreateError(t("adminUsers.errorPolicy"));
      } else {
        setCreateError(t("adminUsers.errorCreate"));
      }
    } finally {
      setIsCreating(false);
    }
  }

  async function handleToggleActive(user) {
    try {
      await usersApi.updateUser(user.id, { is_active: !user.is_active });
      await fetchUsers();
    } catch {
      setError(t("adminUsers.errorUpdate"));
    }
  }

  async function handleToggleRole(user) {
    const newRole = user.role === "admin" ? "user" : "admin";
    const roleLabel = newRole === "admin" ? t("common.roleAdmin") : t("common.roleUser");
    if (!window.confirm(t("adminUsers.roleChangeConfirm", { login: user.login, role: roleLabel })))
      return;
    try {
      await usersApi.updateUser(user.id, { role: newRole });
      await fetchUsers();
    } catch {
      setError(t("adminUsers.errorRole"));
    }
  }

  async function handleDelete(user) {
    if (!window.confirm(t("adminUsers.deleteConfirm", { login: user.login }))) return;
    try {
      await usersApi.deleteUser(user.id);
      await fetchUsers();
    } catch {
      setError(t("adminUsers.errorDelete"));
    }
  }

  async function handleResetPassword(e) {
    e.preventDefault();
    setResetError(null);
    try {
      await usersApi.resetUserPassword(resetTargetId, resetPassword);
      setResetTargetId(null);
      setResetPassword("");
    } catch (err) {
      const status = err.response?.status;
      setResetError(
        status === 422 ? t("adminUsers.errorPolicy") : t("adminUsers.errorReset")
      );
    }
  }

  return (
    <div className="admin-users-page">
      <div className="admin-page-header">
        <div>
          <h1>{t("adminUsers.title")}</h1>
          <p>{t("adminUsers.subtitle")}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreateForm((v) => !v)}>
          {showCreateForm ? t("common.cancel") : t("adminUsers.add")}
        </button>
      </div>

      {showCreateForm && (
        <form onSubmit={handleCreate} className="card create-user-form">
          <div className="field">
            <label htmlFor="new-login">{t("adminUsers.login")}</label>
            <input
              id="new-login"
              type="text"
              required
              value={newUser.login}
              onChange={(e) => setNewUser({ ...newUser, login: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="new-password">{t("adminUsers.initialPassword")}</label>
            <input
              id="new-password"
              type="password"
              required
              value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="new-role">{t("adminUsers.role")}</label>
            <select
              id="new-role"
              value={newUser.role}
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
            >
              <option value="user">{t("common.roleUser")}</option>
              <option value="admin">{t("common.roleAdmin")}</option>
            </select>
          </div>
          {createError && <p className="error-text">{createError}</p>}
          <button type="submit" className="btn btn-primary" disabled={isCreating}>
            {isCreating ? t("adminUsers.creating") : t("adminUsers.create")}
          </button>
        </form>
      )}

      {error && <p className="error-text">{error}</p>}

      {isLoading ? (
        <p>{t("common.loading")}</p>
      ) : (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>{t("adminUsers.colLogin")}</th>
                <th>{t("adminUsers.colRole")}</th>
                <th>{t("adminUsers.colStatus")}</th>
                <th>{t("adminUsers.colLastLogin")}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.login}</td>
                  <td>
                    <button className="role-toggle" onClick={() => handleToggleRole(user)}>
                      {user.role === "admin" ? t("common.roleAdmin") : t("common.roleUser")}
                    </button>
                  </td>
                  <td>
                    <span className={`badge ${user.is_active ? "badge-done" : "badge-error"}`}>
                      {user.is_active ? t("adminUsers.active") : t("adminUsers.disabled")}
                    </span>
                  </td>
                  <td className="mono">
                    {user.last_login_at
                      ? new Date(user.last_login_at).toLocaleString(
                          navigator.language.startsWith("en") ? "en-GB" : "fr-FR"
                        )
                      : t("adminUsers.never")}
                  </td>
                  <td className="admin-user-actions">
                    <button className="btn btn-secondary btn-sm" onClick={() => handleToggleActive(user)}>
                      {user.is_active ? t("adminUsers.disable") : t("adminUsers.enable")}
                    </button>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        setResetTargetId(user.id);
                        setResetPassword("");
                        setResetError(null);
                      }}
                    >
                      {t("adminUsers.resetPassword")}
                    </button>
                    <button className="btn btn-danger btn-sm" onClick={() => handleDelete(user)}>
                      {t("common.delete")}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {resetTargetId && (
        <div className="modal-backdrop" onClick={() => setResetTargetId(null)}>
          <form
            className="card modal-card"
            onClick={(e) => e.stopPropagation()}
            onSubmit={handleResetPassword}
          >
            <h2>{t("adminUsers.resetTitle")}</h2>
            <div className="field">
              <label htmlFor="reset-password">{t("adminUsers.newPassword")}</label>
              <input
                id="reset-password"
                type="password"
                required
                autoFocus
                value={resetPassword}
                onChange={(e) => setResetPassword(e.target.value)}
              />
            </div>
            {resetError && <p className="error-text">{resetError}</p>}
            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setResetTargetId(null)}
              >
                {t("common.cancel")}
              </button>
              <button type="submit" className="btn btn-primary">
                {t("adminUsers.reset")}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
