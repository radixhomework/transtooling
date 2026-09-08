import { useState } from "react";
import { useTranslation } from "react-i18next";
import AdminUsersPage from "./AdminUsersPage.jsx";
import AdminModelsPage from "./AdminModelsPage.jsx";
import AdminSettingsPage from "./AdminSettingsPage.jsx";
import "./AdminPage.css";

const TABS = [
  { id: "users", label: "nav.users" },
  { id: "models", label: "nav.models" },
  { id: "settings", label: "nav.settings" },
];

export default function AdminPage() {
  const { t } = useTranslation();
  const [tab, setTab] = useState("users");

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1>{t("admin.title")}</h1>
          <p>{t("admin.subtitle")}</p>
        </div>
      </div>

      <div className="admin-tabs" role="tablist">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className={`admin-tab ${tab === id ? "is-active" : ""}`}
            onClick={() => setTab(id)}
          >
            {t(label)}
          </button>
        ))}
      </div>

      {tab === "users" && <AdminUsersPage />}
      {tab === "models" && <AdminModelsPage />}
      {tab === "settings" && <AdminSettingsPage />}
    </div>
  );
}
