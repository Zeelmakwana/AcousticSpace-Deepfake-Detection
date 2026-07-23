/**
 * AcousticSpace — Error Page
 * ===========================
 * Used for both 404 (not found) and generic error states.
 *
 * Props
 * -----
 * code?    : HTTP status number (defaults to 404)
 * title?   : Override heading text
 * message? : Override body text
 * retry?   : If true, show a "Try again" button that reloads the page
 *
 * Routes
 * ------
 * <Route path="*" element={<ErrorPage />} />
 * Can also be rendered inline for fetch errors with code={500} retry.
 */

import { useNavigate } from "react-router-dom";

interface Props {
  code?: number;
  title?: string;
  message?: string;
  retry?: boolean;
}

const DEFAULTS: Record<number, { title: string; message: string; icon: string }> = {
  404: {
    icon: "🔍",
    title: "Page not found",
    message:
      "The page you're looking for doesn't exist or has been moved. Check the URL or navigate back to the upload page.",
  },
  403: {
    icon: "🔒",
    title: "Access denied",
    message:
      "You don't have permission to view this page. Please log in with an account that has the required access.",
  },
  500: {
    icon: "⚡",
    title: "Something went wrong",
    message:
      "An unexpected error occurred. The issue has been noted. Try refreshing the page, or go back and attempt the action again.",
  },
};

export default function ErrorPage({
  code = 404,
  title,
  message,
  retry = false,
}: Props) {
  const navigate = useNavigate();
  const defaults = DEFAULTS[code] ?? DEFAULTS[500];

  const displayTitle   = title   ?? defaults.title;
  const displayMessage = message ?? defaults.message;
  const displayIcon    = defaults.icon;

  return (
    <div className="error-page" role="main" aria-labelledby="error-heading">
      <div className="error-page-inner">
        {/* Status code */}
        <p className="error-page-code" aria-hidden="true">{code}</p>

        {/* Icon */}
        <span className="error-page-icon" aria-hidden="true">{displayIcon}</span>

        {/* Heading */}
        <h1 className="error-page-title" id="error-heading">
          {displayTitle}
        </h1>

        {/* Body */}
        <p className="error-page-message">{displayMessage}</p>

        {/* Actions */}
        <div className="error-page-actions">
          <button
            className="error-page-btn error-page-btn--primary"
            onClick={() => navigate("/", { replace: true })}
          >
            ← Go to Upload
          </button>

          <button
            className="error-page-btn error-page-btn--ghost"
            onClick={() => navigate(-1)}
          >
            Go back
          </button>

          {retry && (
            <button
              className="error-page-btn error-page-btn--ghost"
              onClick={() => window.location.reload()}
            >
              ↺ Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
