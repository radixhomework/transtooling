import { useEffect, useState } from "react";
import * as usersApi from "../api/users";
import "./AdminUsersPage.css";

function emptyNewUser() {
  return { login: "", password: "", role: "user" };
}

export default function AdminUsersPage() {
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
      setError("Impossible de charger les utilisateurs.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    fetchUsers();
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
        setCreateError("Cet identifiant est déjà utilisé.");
      } else if (status === 422) {
        setCreateError("Le mot de passe doit contenir au moins 8 caractères, une lettre et un chiffre.");
      } else {
        setCreateError("Impossible de créer l'utilisateur.");
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
      setError("Impossible de mettre à jour cet utilisateur.");
    }
  }

  async function handleToggleRole(user) {
    const newRole = user.role === "admin" ? "user" : "admin";
    if (!window.confirm(`Changer le rôle de ${user.login} en « ${newRole} » ?`)) return;
    try {
      await usersApi.updateUser(user.id, { role: newRole });
      await fetchUsers();
    } catch {
      setError("Impossible de mettre à jour le rôle.");
    }
  }

  async function handleDelete(user) {
    if (!window.confirm(`Supprimer définitivement le compte de ${user.login} ?`)) return;
    try {
      await usersApi.deleteUser(user.id);
      await fetchUsers();
    } catch {
      setError("Impossible de supprimer cet utilisateur (peut-être votre propre compte).");
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
        status === 422
          ? "Le mot de passe doit contenir au moins 8 caractères, une lettre et un chiffre."
          : "Impossible de réinitialiser ce mot de passe."
      );
    }
  }

  return (
    <div className="admin-users-page">
      <div className="admin-page-header">
        <div>
          <h1>Utilisateurs</h1>
          <p>Gérez les comptes utilisateurs et administrateurs de l'application.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreateForm((v) => !v)}>
          {showCreateForm ? "Annuler" : "Ajouter un utilisateur"}
        </button>
      </div>

      {showCreateForm && (
        <form onSubmit={handleCreate} className="card create-user-form">
          <div className="field">
            <label htmlFor="new-login">Identifiant</label>
            <input
              id="new-login"
              type="text"
              required
              value={newUser.login}
              onChange={(e) => setNewUser({ ...newUser, login: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="new-password">Mot de passe initial</label>
            <input
              id="new-password"
              type="password"
              required
              value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="new-role">Rôle</label>
            <select
              id="new-role"
              value={newUser.role}
              onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
            >
              <option value="user">Utilisateur</option>
              <option value="admin">Administrateur</option>
            </select>
          </div>
          {createError && <p className="error-text">{createError}</p>}
          <button type="submit" className="btn btn-primary" disabled={isCreating}>
            {isCreating ? "Création..." : "Créer le compte"}
          </button>
        </form>
      )}

      {error && <p className="error-text">{error}</p>}

      {isLoading ? (
        <p>Chargement…</p>
      ) : (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>Identifiant</th>
                <th>Rôle</th>
                <th>Statut</th>
                <th>Dernière connexion</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.login}</td>
                  <td>
                    <button className="role-toggle" onClick={() => handleToggleRole(user)}>
                      {user.role === "admin" ? "Administrateur" : "Utilisateur"}
                    </button>
                  </td>
                  <td>
                    <span className={`badge ${user.is_active ? "badge-done" : "badge-error"}`}>
                      {user.is_active ? "Actif" : "Désactivé"}
                    </span>
                  </td>
                  <td className="mono">
                    {user.last_login_at
                      ? new Date(user.last_login_at).toLocaleString("fr-FR")
                      : "Jamais"}
                  </td>
                  <td className="admin-user-actions">
                    <button className="btn btn-secondary btn-sm" onClick={() => handleToggleActive(user)}>
                      {user.is_active ? "Désactiver" : "Activer"}
                    </button>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        setResetTargetId(user.id);
                        setResetPassword("");
                        setResetError(null);
                      }}
                    >
                      Réinitialiser mdp
                    </button>
                    <button className="btn btn-danger btn-sm" onClick={() => handleDelete(user)}>
                      Supprimer
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
            <h2>Réinitialiser le mot de passe</h2>
            <div className="field">
              <label htmlFor="reset-password">Nouveau mot de passe</label>
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
                Annuler
              </button>
              <button type="submit" className="btn btn-primary">
                Réinitialiser
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
