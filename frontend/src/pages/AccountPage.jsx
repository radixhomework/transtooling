import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import * as authApi from "../api/auth";
import "./AccountPage.css";

export default function AccountPage() {
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
      setError("La confirmation ne correspond pas au nouveau mot de passe.");
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
        setError("Mot de passe actuel incorrect.");
      } else if (status === 422) {
        setError("Le nouveau mot de passe doit contenir au moins 8 caractères, une lettre et un chiffre.");
      } else {
        setError("Une erreur est survenue. Réessayez.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="account-page">
      <h1>Mon compte</h1>

      <div className="card account-info">
        <div>
          <span className="account-info-label">Email</span>
          <span className="mono">{user?.login}</span>
        </div>
        <div>
          <span className="account-info-label">Rôle</span>
          <span className="mono">{user?.role === "admin" ? "Administrateur" : "Utilisateur"}</span>
        </div>
      </div>

      <div className="card account-form-card">
        <h2>Changer de mot de passe</h2>
        <form onSubmit={handleSubmit} className="account-form">
          <div className="field">
            <label htmlFor="current-password">Mot de passe actuel</label>
            <input
              id="current-password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="new-password">Nouveau mot de passe</label>
            <input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="confirm-password">Confirmer le nouveau mot de passe</label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          {error && <p className="error-text">{error}</p>}
          {success && <p className="success-text">Mot de passe mis à jour.</p>}

          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? "Mise à jour..." : "Mettre à jour le mot de passe"}
          </button>
        </form>
      </div>
    </div>
  );
}
