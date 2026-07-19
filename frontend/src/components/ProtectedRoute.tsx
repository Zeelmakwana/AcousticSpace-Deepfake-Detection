/**
 * ProtectedRoute
 * ==============
 * Wraps a route element and redirects unauthenticated users to /login.
 * Preserves the originally requested URL in `state.from` so LoginPage can
 * redirect back after a successful login.
 *
 * Usage:
 *   <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
 *
 * While the auth context is still bootstrapping (isLoading=true) a neutral
 * loading indicator is shown rather than flashing the login page.
 */

import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

interface Props {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: Props) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="auth-loading" aria-label="Checking authentication…">
        <span className="auth-spinner" aria-hidden="true" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
