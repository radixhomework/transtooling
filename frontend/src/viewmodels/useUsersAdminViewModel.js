import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import * as usersApi from "../models/users";

function emptyNewUser() {
  return { login: "", password: "", role: "user" };
}

/**
 * ViewModel for the admin users screen: user list plus create / toggle
 * active / toggle role / reset password / delete actions.
 */
export function useUsersAdminViewModel() {
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

  const fetchUsers = useCallback(async () => {
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
  }, [t]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const submitCreate = useCallback(async () => {
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
  }, [fetchUsers, newUser, t]);

  const toggleActive = useCallback(
    async (user) => {
      try {
        await usersApi.updateUser(user.id, { is_active: !user.is_active });
        await fetchUsers();
      } catch {
        setError(t("adminUsers.errorUpdate"));
      }
    },
    [fetchUsers, t]
  );

  const toggleRole = useCallback(
    async (user) => {
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
    },
    [fetchUsers, t]
  );

  const deleteUser = useCallback(
    async (user) => {
      if (!window.confirm(t("adminUsers.deleteConfirm", { login: user.login }))) return;
      try {
        await usersApi.deleteUser(user.id);
        await fetchUsers();
      } catch {
        setError(t("adminUsers.errorDelete"));
      }
    },
    [fetchUsers, t]
  );

  const submitResetPassword = useCallback(async () => {
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
  }, [resetPassword, resetTargetId, t]);

  const openResetModal = useCallback((user) => {
    setResetTargetId(user.id);
    setResetPassword("");
    setResetError(null);
  }, []);

  return {
    // state
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
    // actions / setters
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
  };
}
