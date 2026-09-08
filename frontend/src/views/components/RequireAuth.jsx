import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../../viewmodels/AuthContext/AuthContext.jsx";
import Waveform from "./Waveform.jsx";

export default function RequireAuth() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: 80 }}>
        <Waveform size="lg" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
