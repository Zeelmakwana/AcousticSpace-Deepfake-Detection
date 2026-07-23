/**
 * ProfilePage
 * ===========
 * Displays the authenticated user's profile information and provides
 * a logout button.  This route is protected — unauthenticated users are
 * redirected to /login by ProtectedRoute before this component renders.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [signingOut, setSigningOut] = useState(false);

  async function handleLogout() {
    setSigningOut(true);
    try {
      await logout();
      navigate("/login", { replace: true });
    } finally {
      setSigningOut(false);
    }
  }

  if (!user) return null; // ProtectedRoute guards this; null is unreachable in practice.

  const joined = new Date(user.created_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <div className="profile-page">
      <h2>Profile</h2>

      <div className="profile-card">
        <div className="profile-avatar" aria-hidden="true">
          {user.username.charAt(0).toUpperCase()}
        </div>

        <dl className="profile-details">
          <div className="profile-row">
            <dt>Username</dt>
            <dd>{user.username}</dd>
          </div>
          <div className="profile-row">
            <dt>Email</dt>
            <dd>{user.email}</dd>
          </div>
          <div className="profile-row">
            <dt>Role</dt>
            <dd>
              <span className={`profile-role profile-role--${user.role}`}>
                {user.role === "admin" ? "Administrator" : "User"}
              </span>
            </dd>
          </div>
          <div className="profile-row">
            <dt>Member since</dt>
            <dd>{joined}</dd>
          </div>
          <div className="profile-row">
            <dt>Account status</dt>
            <dd>
              <span className={user.is_active ? "profile-status--active" : "profile-status--inactive"}>
                {user.is_active ? "Active" : "Deactivated"}
              </span>
            </dd>
          </div>
        </dl>

        <button
          className="auth-submit profile-logout-btn"
          onClick={handleLogout}
          disabled={signingOut}
          aria-busy={signingOut}
        >
          {signingOut ? "Signing out…" : "Sign out"}
        </button>
      </div>
    </div>
  );
}
