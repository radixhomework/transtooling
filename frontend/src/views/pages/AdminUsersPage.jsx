import { useTranslation } from "react-i18next";
import { useUsersAdminViewModel } from "../../viewmodels/useUsersAdminViewModel";
import "./AdminUsersPage.css";

export default function AdminUsersPage() {
  const { t } = useTranslation();
  const {
    users,
    isLoading,
    error,
    showCreateForm,
    newUser,
    createError,
    isCreating,
    resetTargetId,
    resetPassword,
    resetError,
    setShowCreateForm,
    setNewUser,
    setResetTargetId,
    setResetPassword,
    submitCreate,
    toggleActive,
    toggleRole,
    deleteUser,
    submitResetPassword,
    openResetModal,
  } = useUsersAdminViewModel();

  return (
    <div className="admin-users-page">
      <div className="admin-users-toolbar">
        <p className="admin-section-desc">{t("adminUsers.subtitle")}</p>
        <button className="btn btn-primary" onClick={() => setShowCreateForm((v) => !v)}>
          {showCreateForm ? t("common.cancel") : t("adminUsers.add")}
        </button>
      </div>

      {showCreateForm && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            submitCreate();
          }}
          className="card create-user-form"
        >
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
                    <button className="role-toggle" onClick={() => toggleRole(user)}>
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
                    <button className="btn btn-secondary btn-sm" onClick={() => toggleActive(user)}>
                      {user.is_active ? t("adminUsers.disable") : t("adminUsers.enable")}
                    </button>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => openResetModal(user)}
                    >
                      {t("adminUsers.resetPassword")}
                    </button>
                    <button className="btn btn-danger btn-sm" onClick={() => deleteUser(user)}>
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
            onSubmit={(e) => {
              e.preventDefault();
              submitResetPassword();
            }}
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
