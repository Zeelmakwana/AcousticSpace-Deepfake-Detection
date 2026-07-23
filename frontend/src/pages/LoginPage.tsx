/**
 * LoginPage
 * =========
 * Combined Login / Sign-up page with tab switching.
 *
 * - Login tab: email + password + "remember me" checkbox
 * - Sign-up tab: email + username + password
 *
 * On success the user is redirected to the page they originally tried to
 * access (state.from from ProtectedRoute) or to "/" as a fallback.
 */

import { FormEvent, useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

type Tab = "login" | "signup";

export default function LoginPage() {
  const { isAuthenticated, isLoading, login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: Location })?.from?.pathname ?? "/";

  const [tab, setTab] = useState<Tab>("login");

  // Navigate only after React has committed the new auth state.
  // Using useEffect ensures isAuthenticated is already true in the same
  // render cycle that triggers navigation, so ProtectedRoute lets the
  // user through instead of bouncing back to /login.
  useEffect(() => {
    if (isAuthenticated && !isLoading) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate, from]);

  // Login form state
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);

  // Signup form state
  const [signupEmail, setSignupEmail] = useState("");
  const [signupUsername, setSignupUsername] = useState("");
  const [signupPassword, setSignupPassword] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Already authenticated — send them home immediately.
  // (Also covered by the useEffect above, but keep as a fast-path render guard.)
  if (!isLoading && isAuthenticated) {
    return <Navigate to={from} replace />;
  }

  async function handleLogin(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login({ email: loginEmail, password: loginPassword, remember_me: rememberMe });
      // Navigation is handled by the useEffect above once isAuthenticated becomes true.
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Login failed. Check your credentials and try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSignup(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register({
        email: signupEmail,
        username: signupUsername,
        password: signupPassword,
      });
      // Navigation is handled by the useEffect above once isAuthenticated becomes true.
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Registration failed. Please try again.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">🎧 AcousticSpace</div>

        {/* Tab switcher */}
        <div className="auth-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={tab === "login"}
            className={tab === "login" ? "auth-tab active" : "auth-tab"}
            onClick={() => { setTab("login"); setError(null); }}
          >
            Log in
          </button>
          <button
            role="tab"
            aria-selected={tab === "signup"}
            className={tab === "signup" ? "auth-tab active" : "auth-tab"}
            onClick={() => { setTab("signup"); setError(null); }}
          >
            Sign up
          </button>
        </div>

        {/* Error banner */}
        {error && (
          <p className="auth-error" role="alert">
            {error}
          </p>
        )}

        {/* Login form */}
        {tab === "login" && (
          <form className="auth-form" onSubmit={handleLogin} noValidate>
            <label className="auth-label" htmlFor="login-email">Email</label>
            <input
              id="login-email"
              className="auth-input"
              type="email"
              autoComplete="email"
              required
              value={loginEmail}
              onChange={(e) => setLoginEmail(e.target.value)}
            />

            <label className="auth-label" htmlFor="login-password">Password</label>
            <input
              id="login-password"
              className="auth-input"
              type="password"
              autoComplete="current-password"
              required
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
            />

            <label className="auth-checkbox-label">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
              />
              <span>Remember me for 30 days</span>
            </label>

            <button
              className="auth-submit"
              type="submit"
              disabled={submitting}
              aria-busy={submitting}
            >
              {submitting ? "Logging in…" : "Log in"}
            </button>
          </form>
        )}

        {/* Sign-up form */}
        {tab === "signup" && (
          <form className="auth-form" onSubmit={handleSignup} noValidate>
            <label className="auth-label" htmlFor="signup-email">Email</label>
            <input
              id="signup-email"
              className="auth-input"
              type="email"
              autoComplete="email"
              required
              value={signupEmail}
              onChange={(e) => setSignupEmail(e.target.value)}
            />

            <label className="auth-label" htmlFor="signup-username">Username</label>
            <input
              id="signup-username"
              className="auth-input"
              type="text"
              autoComplete="username"
              required
              minLength={3}
              maxLength={64}
              value={signupUsername}
              onChange={(e) => setSignupUsername(e.target.value)}
            />

            <label className="auth-label" htmlFor="signup-password">
              Password <span className="auth-hint">(min. 8 characters)</span>
            </label>
            <input
              id="signup-password"
              className="auth-input"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={signupPassword}
              onChange={(e) => setSignupPassword(e.target.value)}
            />

            <button
              className="auth-submit"
              type="submit"
              disabled={submitting}
              aria-busy={submitting}
            >
              {submitting ? "Creating account…" : "Create account"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
