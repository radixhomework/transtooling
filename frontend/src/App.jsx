import { Routes, Route, Navigate } from "react-router-dom";
import RequireAuth from "./views/components/RequireAuth.jsx";
import RequireAdmin from "./views/components/RequireAdmin.jsx";
import Layout from "./views/components/Layout.jsx";
import LoginPage from "./views/pages/LoginPage.jsx";
import DashboardPage from "./views/pages/DashboardPage.jsx";
import TranslationPage from "./views/pages/TranslationPage.jsx";
import AccountPage from "./views/pages/AccountPage.jsx";
import AdminPage from "./views/pages/AdminPage.jsx";

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
            <Route path="/admin" element={<AdminPage />} />
            {/* Anciennes routes : redirigées vers l'onglet correspondant */}
            <Route path="/admin/users" element={<Navigate to="/admin" replace />} />
            <Route path="/admin/models" element={<Navigate to="/admin" replace />} />
            <Route path="/admin/settings" element={<Navigate to="/admin" replace />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
