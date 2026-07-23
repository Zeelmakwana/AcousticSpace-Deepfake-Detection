/**
 * AcousticSpace — Explainable AI Panel
 * ======================================
 * Renders the structured XAI explanation returned by POST /analyze.
 * Displays all 8 explanation fields:
 *   1. Reason (verdict summary)
 *   2. Confidence explanation
 *   3. Risk level badge
 *   4. Recommendation
 *   5. Room mismatch explanation
 *   6. Breathing explanation
 *   7. RT60 explanation
 *   8. RIR explanation
 *
 * Purely presentational — receives a XaiExplanation prop and renders it.
 * No API calls, no state, no side effects.
 */

import type { RiskLevel, XaiExplanation } from "../types";

interface Props {
  explanation: XaiExplanation;
}

// ---------------------------------------------------------------------------
// Risk badge
// ---------------------------------------------------------------------------

const RISK_CONFIG: Record<
  RiskLevel,
  { label: string; className: string; icon: string }
> = {
  Low:      { label: "Low Risk",      className: "xai-risk xai-risk--low",      icon: "✔" },
  Medium:   { label: "Medium Risk",   className: "xai-risk xai-risk--medium",   icon: "⚠" },
  High:     { label: "High Risk",     className: "xai-risk xai-risk--high",     icon: "⚠" },
  Critical: { label: "Critical Risk", className: "xai-risk xai-risk--critical", icon: "🚨" },
};

function RiskBadge({ level }: { level: RiskLevel }) {
  const cfg = RISK_CONFIG[level] ?? RISK_CONFIG.Medium;
  return (
    <span className={cfg.className} aria-label={`Risk level: ${cfg.label}`}>
      <span aria-hidden="true">{cfg.icon}</span> {cfg.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Individual explanation card
// ---------------------------------------------------------------------------

interface CardProps {
  icon: string;
  title: string;
  body: string;
  accent?: "cyan" | "green" | "red" | "blue" | "muted";
}

function XaiCard({ icon, title, body, accent = "muted" }: CardProps) {
  return (
    <div className={`xai-card xai-card--${accent}`}>
      <div className="xai-card-header">
        <span className="xai-card-icon" aria-hidden="true">{icon}</span>
        <h4 className="xai-card-title">{title}</h4>
      </div>
      <p className="xai-card-body">{body}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ExplanationPanel({ explanation }: Props) {
  const {
    reason,
    confidence_explanation,
    room_mismatch_explanation,
    breathing_explanation,
    rt60_explanation,
    rir_explanation,
    risk_level,
    recommendation,
  } = explanation;

  return (
    <section className="xai-panel" aria-label="AI explanation">
      {/* ---- Section heading ---------------------------------------------- */}
      <div className="xai-panel-header">
        <h3 className="xai-panel-title">
          <span aria-hidden="true">🔍</span> Why this result?
        </h3>
        <RiskBadge level={risk_level} />
      </div>

      {/* ---- Reason (verdict summary) ------------------------------------- */}
      <div className="xai-reason">
        <p className="xai-reason-text">{reason}</p>
      </div>

      {/* ---- Recommendation ----------------------------------------------- */}
      <div className="xai-recommendation">
        <span className="xai-rec-label" aria-hidden="true">💡 Recommendation</span>
        <p className="xai-rec-text">{recommendation}</p>
      </div>

      {/* ---- Detail cards grid -------------------------------------------- */}
      <div className="xai-cards-grid">
        <XaiCard
          icon="📊"
          title="Confidence"
          body={confidence_explanation}
          accent="cyan"
        />
        <XaiCard
          icon="🏠"
          title="Room Acoustics"
          body={room_mismatch_explanation}
          accent="blue"
        />
        <XaiCard
          icon="🫁"
          title="Breathing Cadence"
          body={breathing_explanation}
          accent="blue"
        />
        <XaiCard
          icon="🔊"
          title="Reverberation Time (RT60)"
          body={rt60_explanation}
          accent="muted"
        />
        <XaiCard
          icon="〰️"
          title="Room Impulse Response (RIR)"
          body={rir_explanation}
          accent="muted"
        />
      </div>
    </section>
  );
}
