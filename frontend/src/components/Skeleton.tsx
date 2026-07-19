/**
 * AcousticSpace — Skeleton Loading Components
 * =============================================
 * Reusable shimmer skeleton shapes for use while data is loading.
 *
 * Exported components
 * -------------------
 * SkeletonLine    — single line of text placeholder
 * SkeletonCard    — card-shaped block
 * SkeletonStatGrid — 6-card stats grid (Dashboard)
 * SkeletonChartCard — chart placeholder with header + body
 * SkeletonTableRows — n rows of a table
 * SkeletonResultsPanel — full results panel placeholder (Home page)
 * SkeletonUploadDone  — post-upload loading state
 *
 * All are purely presentational; they apply the `.skeleton` base class
 * plus the `.skeleton-shimmer` animation defined in global.css.
 */

import type { CSSProperties } from "react";

// ---------------------------------------------------------------------------
// Primitive
// ---------------------------------------------------------------------------
interface LineProps {
  width?: string;
  height?: string;
  style?: CSSProperties;
  className?: string;
  rounded?: boolean;
}

export function SkeletonLine({
  width = "100%",
  height = "1em",
  style,
  className = "",
  rounded = false,
}: LineProps) {
  return (
    <div
      className={`skeleton skeleton-shimmer ${rounded ? "skeleton--pill" : ""} ${className}`}
      style={{ width, height, borderRadius: rounded ? 99 : 6, ...style }}
      aria-hidden="true"
    />
  );
}

// ---------------------------------------------------------------------------
// Stat card skeleton (Dashboard)
// ---------------------------------------------------------------------------
function SkeletonStatCard() {
  return (
    <div className="dash-stat-card" aria-hidden="true">
      <SkeletonLine width="1.4rem" height="1.4rem" style={{ marginBottom: "0.4rem" }} />
      <SkeletonLine width="55%" height="2rem" style={{ marginBottom: "0.3rem" }} />
      <SkeletonLine width="70%" height="0.7rem" />
    </div>
  );
}

export function SkeletonStatGrid() {
  return (
    <div className="dash-stats-grid" aria-label="Loading statistics…">
      {Array.from({ length: 6 }).map((_, i) => (
        <SkeletonStatCard key={i} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Chart card skeleton
// ---------------------------------------------------------------------------
export function SkeletonChartCard({ wide = false }: { wide?: boolean }) {
  return (
    <div
      className={`dash-chart-card${wide ? " dash-chart-card--wide" : ""}`}
      aria-hidden="true"
    >
      <SkeletonLine width="45%" height="0.95rem" style={{ marginBottom: "1rem" }} />
      <SkeletonLine width="100%" height="200px" style={{ borderRadius: 8 }} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Table row skeletons
// ---------------------------------------------------------------------------
export function SkeletonTableRows({
  rows = 8,
  cols = 6,
}: {
  rows?: number;
  cols?: number;
}) {
  return (
    <>
      {Array.from({ length: rows }).map((_, r) => (
        <tr key={r} aria-hidden="true">
          {Array.from({ length: cols }).map((__, c) => (
            <td key={c} style={{ padding: "0.6rem 0.75rem" }}>
              <SkeletonLine
                width={c === 0 ? "80%" : c === cols - 1 ? "60%" : "70%"}
                height="0.85rem"
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

// ---------------------------------------------------------------------------
// Results panel skeleton (Home page — shown while analysing)
// ---------------------------------------------------------------------------
export function SkeletonResultsPanel() {
  return (
    <div
      className="results-panel skeleton-results"
      aria-label="Analysing audio…"
      aria-busy="true"
    >
      {/* Header */}
      <div className="results-panel-header" aria-hidden="true">
        <SkeletonLine width="55%" height="1.15rem" />
        <SkeletonLine width="120px" height="2rem" style={{ borderRadius: 8 }} />
      </div>

      {/* Confidence card */}
      <div
        className="confidence-card"
        style={{ marginTop: "1rem" }}
        aria-hidden="true"
      >
        <SkeletonLine width="40%" height="1rem" style={{ marginBottom: "0.5rem" }} />
        <SkeletonLine width="100%" height="8px" style={{ borderRadius: 4 }} />
        <SkeletonLine
          width="30%"
          height="0.8rem"
          style={{ marginTop: "0.4rem" }}
        />
      </div>

      {/* Waveform placeholder */}
      <SkeletonLine
        width="100%"
        height="88px"
        style={{ borderRadius: 8, marginTop: "1.25rem" }}
        aria-hidden={true}
      />

      {/* Stats grid */}
      <div className="results-grid" style={{ marginTop: "1.25rem" }} aria-hidden="true">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="result-stat">
            <SkeletonLine width="60%" height="0.7rem" />
            <SkeletonLine width="45%" height="0.95rem" style={{ marginTop: "0.25rem" }} />
          </div>
        ))}
      </div>
    </div>
  );
}
