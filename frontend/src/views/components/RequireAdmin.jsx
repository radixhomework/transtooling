import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../viewmodels/AuthContext/AuthContext.jsx";

export default function RequireAdmin() {
  const { user } = useAuth();
  if (user?.role !== "admin") {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
