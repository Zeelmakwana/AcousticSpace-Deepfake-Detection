import { useState } from "react";
import { Routes, Route, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import { useTheme } from "./contexts/ThemeContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import History from "./pages/History";
import LoginPage from "./pages/LoginPage";
import ProfilePage from "./pages/ProfilePage";
import ErrorPage from "./pages/ErrorPage";

export default function App() {
  const { isAuthenticated, user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleLogout() {
    await logout();
    setMenuOpen(false);
    navigate("/login", { replace: true });
  }

  function closeMenu() {
    setMenuOpen(false);
  }

  return (
    <div className="app-shell">
      {/* Skip to main content — first focusable element for keyboard users */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* ------------------------------------------------------------------ */}
      {/* Header                                                               */}
      {/* ------------------------------------------------------------------ */}
      <header className="app-header" role="banner">
        {/* Brand */}
        <NavLink to="/" className="brand" aria-label="AcousticSpace home">
          <span className="brand-icon" aria-hidden="true">
            {/* Waveform SVG icon — cleaner than emoji */}
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
              <rect x="1"  y="8"  width="2.5" height="6"  rx="1.25" fill="currentColor" opacity="0.5"/>
              <rect x="5"  y="5"  width="2.5" height="12" rx="1.25" fill="currentColor" opacity="0.75"/>
              <rect x="9"  y="2"  width="2.5" height="18" rx="1.25" fill="currentColor"/>
              <rect x="13" y="5"  width="2.5" height="12" rx="1.25" fill="currentColor" opacity="0.75"/>
              <rect x="17" y="8"  width="2.5" height="6"  rx="1.25" fill="currentColor" opacity="0.5"/>
            </svg>
          </span>
          AcousticSpace
        </NavLink>

        {/* Desktop nav */}
        <nav className="nav-desktop" aria-label="Primary navigation">
          {isAuthenticated ? (
            <>
              <NavLink to="/" end onClick={closeMenu}>
                <span aria-hidden="true">⬆</span> Upload
              </NavLink>
              <NavLink to="/dashboard" onClick={closeMenu}>
                <span aria-hidden="true">◫</span> Dashboard
              </NavLink>
              <NavLink to="/history" onClick={closeMenu}>
                <span aria-hidden="true">⏱</span> History
              </NavLink>
              <NavLink to="/profile" onClick={closeMenu}>
                <span aria-hidden="true">◉</span>{" "}
                {user?.username ?? "Profile"}
              </NavLink>
              <button
                className="nav-logout-btn"
                onClick={handleLogout}
                aria-label="Sign out"
              >
                <span aria-hidden="true">↩</span> Sign out
              </button>
            </>
          ) : (
            <NavLink to="/login">
              <span aria-hidden="true">→</span> Log in
            </NavLink>
          )}
        </nav>

        {/* Right-side controls: theme toggle + hamburger */}
        <div className="nav-controls">
          {/* Theme toggle */}
          <button
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label={
              theme === "dark"
                ? "Switch to light mode"
                : "Switch to dark mode"
            }
            title={theme === "dark" ? "Light mode" : "Dark mode"}
          >
            {theme === "dark" ? (
              /* Sun icon */
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="5"/>
                <line x1="12" y1="1"  x2="12" y2="3"/>
                <line x1="12" y1="21" x2="12" y2="23"/>
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                <line x1="1"  y1="12" x2="3"  y2="12"/>
                <line x1="21" y1="12" x2="23" y2="12"/>
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
              </svg>
            ) : (
              /* Moon icon */
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
              </svg>
            )}
          </button>

          {/* Hamburger — mobile only */}
          <button
            className="nav-hamburger"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            aria-controls="mobile-nav"
            onClick={() => setMenuOpen((o) => !o)}
          >
            {menuOpen ? (
              /* X icon */
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
                <line x1="18" y1="6"  x2="6"  y2="18"/>
                <line x1="6"  y1="6"  x2="18" y2="18"/>
              </svg>
            ) : (
              /* Menu icon */
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
                <line x1="3"  y1="6"  x2="21" y2="6"/>
                <line x1="3"  y1="12" x2="21" y2="12"/>
                <line x1="3"  y1="18" x2="21" y2="18"/>
              </svg>
            )}
          </button>
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* Mobile nav drawer                                                    */}
      {/* ------------------------------------------------------------------ */}
      {menuOpen && (
        /* Backdrop */
        <div
          className="mobile-nav-backdrop"
          aria-hidden="true"
          onClick={closeMenu}
        />
      )}
      <nav
        id="mobile-nav"
        className={`mobile-nav ${menuOpen ? "mobile-nav--open" : ""}`}
        aria-label="Mobile navigation"
        aria-hidden={!menuOpen}
      >
        {isAuthenticated ? (
          <>
            <NavLink to="/" end className="mobile-nav-link" onClick={closeMenu}>
              <span className="mobile-nav-icon" aria-hidden="true">⬆</span>
              Upload
            </NavLink>
            <NavLink to="/dashboard" className="mobile-nav-link" onClick={closeMenu}>
              <span className="mobile-nav-icon" aria-hidden="true">◫</span>
              Dashboard
            </NavLink>
            <NavLink to="/history" className="mobile-nav-link" onClick={closeMenu}>
              <span className="mobile-nav-icon" aria-hidden="true">⏱</span>
              History
            </NavLink>
            <NavLink to="/profile" className="mobile-nav-link" onClick={closeMenu}>
              <span className="mobile-nav-icon" aria-hidden="true">◉</span>
              {user?.username ?? "Profile"}
            </NavLink>
            <button
              className="mobile-nav-link mobile-nav-logout"
              onClick={handleLogout}
            >
              <span className="mobile-nav-icon" aria-hidden="true">↩</span>
              Sign out
            </button>
          </>
        ) : (
          <NavLink to="/login" className="mobile-nav-link" onClick={closeMenu}>
            <span className="mobile-nav-icon" aria-hidden="true">→</span>
            Log in
          </NavLink>
        )}
      </nav>

      {/* ------------------------------------------------------------------ */}
      {/* Main content                                                         */}
      {/* ------------------------------------------------------------------ */}
      <main id="main-content" className="app-main" tabIndex={-1}>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected */}
          <Route path="/" element={<ProtectedRoute><Home /></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/dashboard/:id" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />

          {/* 404 catch-all */}
          <Route path="*" element={<ErrorPage code={404} />} />
        </Routes>
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* Footer                                                               */}
      {/* ------------------------------------------------------------------ */}
      <footer className="app-footer" role="contentinfo">
        AcousticSpace — Deepfake Detection via Room Impulse Response (RIR)
        <span className="footer-sep" aria-hidden="true"> · </span>
        Infotact Solutions Internship
      </footer>
    </div>
  );
}
