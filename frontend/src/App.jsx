import { Routes, Route, Navigate } from "react-router-dom";
import RequireAuth from "./components/RequireAuth.jsx";
import RequireAdmin from "./components/RequireAdmin.jsx";
import Layout from "./components/Layout.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import TranslationPage from "./pages/TranslationPage.jsx";
import AccountPage from "./pages/AccountPage.jsx";
import AdminUsersPage from "./pages/AdminUsersPage.jsx";
import AdminModelsPage from "./pages/AdminModelsPage.jsx";
import AdminSettingsPage from "./pages/AdminSettingsPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/translation" element={<TranslationPage />} />
          <Route path="/account" element={<AccountPage />} />

          <Route element={<RequireAdmin />}>
            <Route path="/admin/users" element={<AdminUsersPage />} />
            <Route path="/admin/models" element={<AdminModelsPage />} />
            <Route path="/admin/settings" element={<AdminSettingsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
