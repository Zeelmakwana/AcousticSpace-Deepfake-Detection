/**
 * AcousticSpace — History Page
 * ==============================
 * Full-featured analysis history table with:
 *   - Live search (filename)
 *   - Column sorting (all columns, asc/desc toggle)
 *   - Prediction + room-match + breathing filters
 *   - Client-side pagination (10 rows/page)
 *   - Delete one row (with inline confirmation)
 *   - Delete all rows (with modal confirmation)
 *   - CSV export of the current filtered/sorted view
 *
 * All data manipulation is client-side; GET /history fetches everything once.
 * DELETE /history/{id} and DELETE /history are the only mutating API calls.
 * No prediction / ML logic is touched.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { deleteAllAnalyses, deleteAnalysis, getHistory } from "../api/client";
import type { AnalyzeResponse } from "../types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SortKey = keyof Pick<
  AnalyzeResponse,
  | "filename"
  | "prediction"
  | "confidence"
  | "room_acoustics_match"
  | "breathing_consistency"
  | "timestamp"
>;

type SortDir = "asc" | "desc";

interface SortState {
  key: SortKey;
  dir: SortDir;
}

const PAGE_SIZE = 10;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function exportToCsv(rows: AnalyzeResponse[]): void {
  const headers = [
    "id",
    "filename",
    "prediction",
    "confidence",
    "room_acoustics_match",
    "breathing_consistency",
    "inference_time_sec",
    "timestamp",
  ];

  const escape = (v: string | number) => {
    const s = String(v);
    return s.includes(",") || s.includes('"') || s.includes("\n")
      ? `"${s.replace(/"/g, '""')}"`
      : s;
  };

  const lines = [
    headers.join(","),
    ...rows.map((r) =>
      [
        r.id,
        r.filename,
        r.prediction,
        r.confidence.toFixed(2),
        r.room_acoustics_match,
        r.breathing_consistency,
        r.inference_time_sec.toFixed(3),
        r.timestamp,
      ]
        .map(escape)
        .join(",")
    ),
  ];

  const blob = new Blob([lines.join("\r\n")], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `acousticspace-history-${new Date()
    .toISOString()
    .slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function SortIcon({
  col,
  sort,
}: {
  col: SortKey;
  sort: SortState;
}) {
  if (sort.key !== col)
    return <span className="hist-sort-icon hist-sort-icon--idle">⇅</span>;
  return (
    <span className="hist-sort-icon hist-sort-icon--active">
      {sort.dir === "asc" ? "↑" : "↓"}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Confirm-delete modal
// ---------------------------------------------------------------------------
interface ConfirmModalProps {
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
}

function ConfirmModal({
  message,
  onConfirm,
  onCancel,
  danger = false,
}: ConfirmModalProps) {
  // Trap focus inside modal
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  return (
    <div
      className="hist-modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Confirm action"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="hist-modal">
        <p className="hist-modal-msg">{message}</p>
        <div className="hist-modal-actions">
          <button
            ref={cancelRef}
            className="hist-btn hist-btn--ghost"
            onClick={onCancel}
          >
            Cancel
          </button>
          <button
            className={`hist-btn ${danger ? "hist-btn--danger" : "hist-btn--primary"}`}
            onClick={onConfirm}
          >
            {danger ? "Delete" : "Confirm"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function History() {
  // ---- data ----------------------------------------------------------------
  const [allRows, setAllRows] = useState<AnalyzeResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // ---- search / filter / sort ---------------------------------------------
  const [search, setSearch] = useState("");
  const [filterPrediction, setFilterPrediction] = useState<
    "All" | "Real" | "Deepfake"
  >("All");
  const [filterRoom, setFilterRoom] = useState<"All" | "High" | "Low">("All");
  const [filterBreathing, setFilterBreathing] = useState<
    "All" | "Consistent" | "Suspicious"
  >("All");
  const [sort, setSort] = useState<SortState>({
    key: "timestamp",
    dir: "desc",
  });

  // ---- pagination ---------------------------------------------------------
  const [page, setPage] = useState(1);

  // ---- delete state -------------------------------------------------------
  // pendingDeleteId: row id waiting inline confirm; null = none pending
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  // showDeleteAll: whether the "delete all" modal is open
  const [showDeleteAll, setShowDeleteAll] = useState(false);
  // deletingId: id currently being deleted (shows spinner on that row)
  const [deletingId, setDeletingId] = useState<string | null>(null);
  // deletingAll: bulk delete in flight
  const [deletingAll, setDeletingAll] = useState(false);
  // actionError: last delete error message
  const [actionError, setActionError] = useState<string | null>(null);

  // ---- load ---------------------------------------------------------------
  const load = useCallback(() => {
    setLoading(true);
    setFetchError(null);
    getHistory()
      .then((data) => setAllRows(data.results))
      .catch(() => setFetchError("Failed to load history. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // ---- derived: filtered + sorted rows ------------------------------------
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return allRows
      .filter((r) => (q ? r.filename.toLowerCase().includes(q) : true))
      .filter((r) =>
        filterPrediction === "All" ? true : r.prediction === filterPrediction
      )
      .filter((r) =>
        filterRoom === "All" ? true : r.room_acoustics_match === filterRoom
      )
      .filter((r) =>
        filterBreathing === "All"
          ? true
          : r.breathing_consistency === filterBreathing
      )
      .sort((a, b) => {
        const av = a[sort.key];
        const bv = b[sort.key];
        const cmp =
          typeof av === "number" && typeof bv === "number"
            ? av - bv
            : String(av).localeCompare(String(bv));
        return sort.dir === "asc" ? cmp : -cmp;
      });
  }, [allRows, search, filterPrediction, filterRoom, filterBreathing, sort]);

  // ---- pagination ---------------------------------------------------------
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageRows = filtered.slice(
    (safePage - 1) * PAGE_SIZE,
    safePage * PAGE_SIZE
  );

  // Reset to page 1 whenever filters change
  useEffect(() => {
    setPage(1);
  }, [search, filterPrediction, filterRoom, filterBreathing, sort]);

  // ---- sort toggle --------------------------------------------------------
  function toggleSort(key: SortKey) {
    setSort((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key, dir: "asc" }
    );
  }

  // ---- delete one ---------------------------------------------------------
  async function confirmDeleteOne(id: string) {
    setDeletingId(id);
    setActionError(null);
    try {
      await deleteAnalysis(id);
      setAllRows((prev) => prev.filter((r) => r.id !== id));
    } catch {
      setActionError("Failed to delete the record. Please try again.");
    } finally {
      setDeletingId(null);
      setPendingDeleteId(null);
    }
  }

  // ---- delete all ---------------------------------------------------------
  async function confirmDeleteAll() {
    setShowDeleteAll(false);
    setDeletingAll(true);
    setActionError(null);
    try {
      await deleteAllAnalyses();
      setAllRows([]);
    } catch {
      setActionError("Failed to delete all records. Please try again.");
    } finally {
      setDeletingAll(false);
    }
  }

  // ---- render helpers -----------------------------------------------------
  function th(label: string, key: SortKey) {
    return (
      <th
        className="hist-th-sortable"
        onClick={() => toggleSort(key)}
        aria-sort={
          sort.key === key
            ? sort.dir === "asc"
              ? "ascending"
              : "descending"
            : "none"
        }
      >
        {label} <SortIcon col={key} sort={sort} />
      </th>
    );
  }

  // ---- loading / error states ---------------------------------------------
  if (loading) {
    return (
      <div className="history-page">
        <div className="auth-loading">
          <span
            className="auth-spinner"
            role="status"
            aria-label="Loading history"
          />
        </div>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="history-page">
        <p className="error-message">{fetchError}</p>
      </div>
    );
  }

  // ---- main render --------------------------------------------------------
  return (
    <div className="history-page">
      {/* Modals */}
      {pendingDeleteId && (
        <ConfirmModal
          message="Permanently delete this analysis? This cannot be undone."
          onConfirm={() => confirmDeleteOne(pendingDeleteId)}
          onCancel={() => setPendingDeleteId(null)}
          danger
        />
      )}
      {showDeleteAll && (
        <ConfirmModal
          message={`Permanently delete all ${allRows.length} analysis records? This cannot be undone.`}
          onConfirm={confirmDeleteAll}
          onCancel={() => setShowDeleteAll(false)}
          danger
        />
      )}

      {/* ---- Header -------------------------------------------------------- */}
      <div className="hist-header">
        <h2 className="hist-title">Analysis History</h2>
        <div className="hist-header-actions">
          <button
            className="hist-btn hist-btn--secondary"
            onClick={() => exportToCsv(filtered)}
            disabled={filtered.length === 0}
            title="Export current view as CSV"
          >
            ⬇ Export CSV
          </button>
          <button
            className="hist-btn hist-btn--danger"
            onClick={() => setShowDeleteAll(true)}
            disabled={allRows.length === 0 || deletingAll}
            title="Delete all analysis records"
          >
            {deletingAll ? "Deleting…" : "🗑 Delete All"}
          </button>
        </div>
      </div>

      {/* Action error */}
      {actionError && (
        <p className="error-message hist-action-error" role="alert">
          {actionError}
        </p>
      )}

      {/* ---- Controls ----------------------------------------------------- */}
      <div className="hist-controls">
        {/* Search */}
        <div className="hist-search-wrap">
          <span className="hist-search-icon" aria-hidden="true">🔍</span>
          <input
            type="search"
            className="hist-search"
            placeholder="Search by filename…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search by filename"
          />
        </div>

        {/* Prediction filter */}
        <label className="hist-filter-label" htmlFor="filter-prediction">
          Prediction
          <select
            id="filter-prediction"
            className="hist-select"
            value={filterPrediction}
            onChange={(e) =>
              setFilterPrediction(e.target.value as typeof filterPrediction)
            }
          >
            <option value="All">All</option>
            <option value="Real">Real</option>
            <option value="Deepfake">Deepfake</option>
          </select>
        </label>

        {/* Room match filter */}
        <label className="hist-filter-label" htmlFor="filter-room">
          Room Match
          <select
            id="filter-room"
            className="hist-select"
            value={filterRoom}
            onChange={(e) =>
              setFilterRoom(e.target.value as typeof filterRoom)
            }
          >
            <option value="All">All</option>
            <option value="High">High</option>
            <option value="Low">Low</option>
          </select>
        </label>

        {/* Breathing filter */}
        <label className="hist-filter-label" htmlFor="filter-breathing">
          Breathing
          <select
            id="filter-breathing"
            className="hist-select"
            value={filterBreathing}
            onChange={(e) =>
              setFilterBreathing(e.target.value as typeof filterBreathing)
            }
          >
            <option value="All">All</option>
            <option value="Consistent">Consistent</option>
            <option value="Suspicious">Suspicious</option>
          </select>
        </label>

        {/* Result count */}
        <p className="hist-count" aria-live="polite">
          {filtered.length === allRows.length
            ? `${allRows.length} record${allRows.length !== 1 ? "s" : ""}`
            : `${filtered.length} of ${allRows.length}`}
        </p>
      </div>

      {/* ---- Empty state -------------------------------------------------- */}
      {allRows.length === 0 && (
        <p className="hist-empty">
          No analyses yet. Upload an audio file on the Upload tab to get
          started.
        </p>
      )}

      {allRows.length > 0 && filtered.length === 0 && (
        <p className="hist-empty">No records match your filters.</p>
      )}

      {/* ---- Table --------------------------------------------------------- */}
      {filtered.length > 0 && (
        <>
          <div className="hist-table-wrapper">
            <table className="history-table hist-table" aria-label="Analysis history">
              <thead>
                <tr>
                  {th("Filename", "filename")}
                  {th("Prediction", "prediction")}
                  {th("Confidence", "confidence")}
                  {th("Room Match", "room_acoustics_match")}
                  {th("Breathing", "breathing_consistency")}
                  {th("Timestamp", "timestamp")}
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {pageRows.map((r) => (
                  <tr
                    key={r.id}
                    className={
                      r.prediction === "Deepfake" ? "row-fake" : "row-real"
                    }
                  >
                    <td
                      className="hist-filename"
                      title={r.filename}
                    >
                      {r.filename.length > 26
                        ? `…${r.filename.slice(-24)}`
                        : r.filename}
                    </td>
                    <td>
                      <span
                        className={
                          r.prediction === "Deepfake"
                            ? "dash-badge dash-badge--fake"
                            : "dash-badge dash-badge--real"
                        }
                      >
                        {r.prediction}
                      </span>
                    </td>
                    <td className="hist-mono">{r.confidence.toFixed(2)}%</td>
                    <td>{r.room_acoustics_match}</td>
                    <td>{r.breathing_consistency}</td>
                    <td className="hist-mono">
                      {new Date(r.timestamp).toLocaleString()}
                    </td>
                    <td className="hist-actions-cell">
                      <button
                        className="hist-btn hist-btn--icon hist-btn--danger-ghost"
                        title="Delete this record"
                        aria-label={`Delete analysis ${r.filename}`}
                        disabled={deletingId === r.id}
                        onClick={() => setPendingDeleteId(r.id)}
                      >
                        {deletingId === r.id ? "…" : "🗑"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ---- Pagination ------------------------------------------------ */}
          {totalPages > 1 && (
            <div className="hist-pagination" role="navigation" aria-label="Pagination">
              <button
                className="hist-btn hist-btn--ghost hist-page-btn"
                onClick={() => setPage(1)}
                disabled={safePage === 1}
                aria-label="First page"
              >
                «
              </button>
              <button
                className="hist-btn hist-btn--ghost hist-page-btn"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={safePage === 1}
                aria-label="Previous page"
              >
                ‹
              </button>

              {/* Page number buttons — show at most 5 around current page */}
              {Array.from({ length: totalPages }, (_, i) => i + 1)
                .filter(
                  (p) =>
                    p === 1 ||
                    p === totalPages ||
                    Math.abs(p - safePage) <= 2
                )
                .reduce<(number | "…")[]>((acc, p, idx, arr) => {
                  if (idx > 0 && (p as number) - (arr[idx - 1] as number) > 1)
                    acc.push("…");
                  acc.push(p);
                  return acc;
                }, [])
                .map((item, i) =>
                  item === "…" ? (
                    <span key={`ellipsis-${i}`} className="hist-page-ellipsis">
                      …
                    </span>
                  ) : (
                    <button
                      key={item}
                      className={`hist-btn hist-page-btn ${
                        item === safePage ? "hist-page-btn--active" : "hist-btn--ghost"
                      }`}
                      onClick={() => setPage(item as number)}
                      aria-current={item === safePage ? "page" : undefined}
                    >
                      {item}
                    </button>
                  )
                )}

              <button
                className="hist-btn hist-btn--ghost hist-page-btn"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={safePage === totalPages}
                aria-label="Next page"
              >
                ›
              </button>
              <button
                className="hist-btn hist-btn--ghost hist-page-btn"
                onClick={() => setPage(totalPages)}
                disabled={safePage === totalPages}
                aria-label="Last page"
              >
                »
              </button>

              <span className="hist-page-info">
                Page {safePage} of {totalPages}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
