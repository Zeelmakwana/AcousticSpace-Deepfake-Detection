/**
 * AcousticSpace — Toast Context
 * ==============================
 * Provides a `useToast()` hook that lets any component fire a notification
 * without prop-drilling.
 *
 * Toast types: "success" | "error" | "info" | "warning"
 * Auto-dismiss: 4 s (configurable per toast via `duration`)
 * Max visible:  5 (oldest dismissed first)
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type ToastType = "success" | "error" | "info" | "warning";

export interface ToastItem {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration: number;  // ms
}

interface ToastContextValue {
  toasts: ToastItem[];
  toast: (opts: Omit<ToastItem, "id">) => void;
  dismiss: (id: string) => void;
  /** Convenience helpers */
  success: (title: string, message?: string) => void;
  error:   (title: string, message?: string) => void;
  info:    (title: string, message?: string) => void;
  warning: (title: string, message?: string) => void;
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------
const ToastContext = createContext<ToastContextValue | null>(null);

const MAX_TOASTS = 5;
const DEFAULT_DURATION = 4000;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const dismiss = useCallback((id: string) => {
    clearTimeout(timersRef.current[id]);
    delete timersRef.current[id];
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (opts: Omit<ToastItem, "id">) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      const item: ToastItem = { id, ...opts, duration: opts.duration ?? DEFAULT_DURATION };

      setToasts((prev) => {
        const next = [...prev, item];
        // If over limit, drop the oldest
        if (next.length > MAX_TOASTS) {
          const removed = next.shift()!;
          clearTimeout(timersRef.current[removed.id]);
          delete timersRef.current[removed.id];
        }
        return next;
      });

      timersRef.current[id] = setTimeout(() => dismiss(id), item.duration);
    },
    [dismiss]
  );

  const success = useCallback(
    (title: string, message?: string) =>
      toast({ type: "success", title, message, duration: DEFAULT_DURATION }),
    [toast]
  );
  const error = useCallback(
    (title: string, message?: string) =>
      toast({ type: "error", title, message, duration: DEFAULT_DURATION + 2000 }),
    [toast]
  );
  const info = useCallback(
    (title: string, message?: string) =>
      toast({ type: "info", title, message, duration: DEFAULT_DURATION }),
    [toast]
  );
  const warning = useCallback(
    (title: string, message?: string) =>
      toast({ type: "warning", title, message, duration: DEFAULT_DURATION }),
    [toast]
  );

  const value = useMemo<ToastContextValue>(
    () => ({ toasts, toast, dismiss, success, error, info, warning }),
    [toasts, toast, dismiss, success, error, info, warning]
  );

  return (
    <ToastContext.Provider value={value}>{children}</ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
