/**
 * AcousticSpace — Toast Renderer
 * ================================
 * Renders the active toast queue from ToastContext in a fixed portal at the
 * top-right of the viewport.  Each toast auto-dismisses after its duration
 * and can be manually closed with the × button.
 *
 * Accessibility
 * -------------
 * - The container has role="region" aria-label="Notifications" and
 *   aria-live="polite" so screen readers announce new toasts.
 * - Error toasts use aria-live="assertive" for immediate announcement.
 * - Each toast has role="status" (success/info/warning) or role="alert" (error).
 * - Close button has an aria-label.
 */

import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { useToast } from "../contexts/ToastContext";
import type { ToastItem, ToastType } from "../contexts/ToastContext";

// ---------------------------------------------------------------------------
// Icon + metadata per type
// ---------------------------------------------------------------------------
const TYPE_META: Record<
  ToastType,
  { icon: string; className: string; role: "status" | "alert"; live: "polite" | "assertive" }
> = {
  success: { icon: "✓",  className: "toast--success", role: "status", live: "polite"     },
  error:   { icon: "✕",  className: "toast--error",   role: "alert",  live: "assertive"  },
  info:    { icon: "ℹ",  className: "toast--info",    role: "status", live: "polite"     },
  warning: { icon: "⚠",  className: "toast--warning", role: "status", live: "polite"     },
};

// ---------------------------------------------------------------------------
// Single toast item
// ---------------------------------------------------------------------------
function ToastCard({ item }: { item: ToastItem }) {
  const { dismiss } = useToast();
  const meta = TYPE_META[item.type];
  const progressRef = useRef<HTMLDivElement>(null);

  // Animate the progress bar shrinking over `item.duration` ms
  useEffect(() => {
    const el = progressRef.current;
    if (!el) return;
    el.style.transition = "none";
    el.style.width = "100%";
    // Force reflow before starting animation
    void el.offsetWidth;
    el.style.transition = `width ${item.duration}ms linear`;
    el.style.width = "0%";
  }, [item.duration]);

  return (
    <div
      className={`toast ${meta.className}`}
      role={meta.role}
      aria-live={meta.live}
      aria-atomic="true"
    >
      {/* Left accent icon */}
      <span className="toast-icon" aria-hidden="true">
        {meta.icon}
      </span>

      {/* Text content */}
      <div className="toast-content">
        <p className="toast-title">{item.title}</p>
        {item.message && <p className="toast-message">{item.message}</p>}
      </div>

      {/* Close button */}
      <button
        className="toast-close"
        onClick={() => dismiss(item.id)}
        aria-label="Dismiss notification"
      >
        ×
      </button>

      {/* Progress bar */}
      <div className="toast-progress-track" aria-hidden="true">
        <div ref={progressRef} className="toast-progress-fill" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Portal container — mounts outside the main React tree
// ---------------------------------------------------------------------------
export default function ToastContainer() {
  const { toasts } = useToast();

  return createPortal(
    <div
      className="toast-region"
      aria-label="Notifications"
      aria-live="polite"
    >
      {toasts.map((item) => (
        <ToastCard key={item.id} item={item} />
      ))}
    </div>,
    document.body
  );
}
