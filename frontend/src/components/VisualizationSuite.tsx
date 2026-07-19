/**
 * AcousticSpace — Visualization Suite
 * =====================================
 * Tabbed container hosting all 8 interactive visualizations:
 *
 *   1. Waveform          — enhanced WaveformViewer (handled in ResultsPanel)
 *   2. Mel Spectrogram   — canvas heatmap (64 mel bands × time)
 *   3. MFCC Heatmap      — canvas heatmap (20 coefficients × time)
 *   4. RT60 Graph        — Schroeder decay curve (recharts AreaChart)
 *   5. RIR Graph         — percussive energy curve (recharts AreaChart)
 *   6. Frequency Spectrum — magnitude FFT (recharts AreaChart)
 *   7. Confidence Gauge  — SVG arc gauge
 *   8. Suspicious Timeline — SVG timeline bar
 *
 * All visualizations are purely client-side from data already in the
 * AnalyzeResponse. No additional API calls.
 */

import {
  useEffect,
  useRef,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { AnalyzeResponse, SuspiciousSegment, VisualizationData } from "../types";

// ---------------------------------------------------------------------------
// Palette
// ---------------------------------------------------------------------------
const C_CYAN  = "#4fd6e0";
const C_BLUE  = "#7c9dfc";
const C_RED   = "#ff6b6b";
const C_GREEN = "#4fd68a";
const C_MUTED = "#93a0c4";
const C_GRID  = "#2a3457";

// ---------------------------------------------------------------------------
// Dark recharts tooltip
// ---------------------------------------------------------------------------
function DarkTip({
  active, payload, label,
}: {
  active?: boolean;
  payload?: { value: number; color: string; name?: string }[];
  label?: string | number;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="viz-tooltip">
      {label !== undefined && <p className="viz-tooltip-label">{label}</p>}
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color, margin: "1px 0" }}>
          {p.name ? `${p.name}: ` : ""}<strong>{typeof p.value === "number" ? p.value.toFixed(3) : p.value}</strong>
        </p>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Canvas heatmap helper
// ---------------------------------------------------------------------------
function useHeatmap(
  matrix: number[][] | undefined,
  colorFn: (v: number, min: number, max: number) => [number, number, number],
) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!matrix || matrix.length === 0 || !canvasRef.current) return;
    const rows = matrix.length;
    const cols = matrix[0].length;
    const canvas = canvasRef.current;
    canvas.width  = cols;
    canvas.height = rows;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const flat = matrix.flat();
    const min = Math.min(...flat);
    const max = Math.max(...flat);

    const imgData = ctx.createImageData(cols, rows);
    for (let r = rows - 1; r >= 0; r--) {   // flip vertically (low freq at bottom)
      for (let c = 0; c < cols; c++) {
        const v = matrix[rows - 1 - r]?.[c] ?? 0;
        const [R, G, B] = colorFn(v, min, max);
        const idx = (r * cols + c) * 4;
        imgData.data[idx]     = R;
        imgData.data[idx + 1] = G;
        imgData.data[idx + 2] = B;
        imgData.data[idx + 3] = 255;
      }
    }
    ctx.putImageData(imgData, 0, 0);
  }, [matrix, colorFn]);

  return canvasRef;
}

// colour maps
function melColor(v: number, min: number, max: number): [number, number, number] {
  const t = (v - min) / (max - min);          // 0..1
  // viridis-ish: deep blue → cyan → yellow
  const r = Math.round(t < 0.5 ? 30 + t * 2 * 160 : 190 + (t - 0.5) * 2 * 65);
  const g = Math.round(t < 0.5 ? 10 + t * 2 * 150 : 160 + (t - 0.5) * 2 * 95);
  const b = Math.round(t < 0.5 ? 120 + t * 2 * 90 : 210 - (t - 0.5) * 2 * 185);
  return [r, g, b];
}

function mfccColor(v: number, min: number, max: number): [number, number, number] {
  const t = (v - min) / (max - min);
  // diverging: cool-blue for negative, neutral for zero, warm-red for positive
  if (t < 0.5) {
    const s = (0.5 - t) * 2;
    return [Math.round(11 + s * 30), Math.round(16 + s * 60), Math.round(50 + s * 150)];
  }
  const s = (t - 0.5) * 2;
  return [Math.round(11 + s * 244), Math.round(16 + s * 91), Math.round(50 + s * 61)];
}

// ---------------------------------------------------------------------------
// 1. Mel Spectrogram
// ---------------------------------------------------------------------------
function MelSpectrogram({ viz }: { viz: VisualizationData }) {
  const colorFn = useCallback(melColor, []);
  const ref = useHeatmap(viz.mel_matrix, colorFn);
  const cols = viz.mel_matrix[0]?.length ?? 1;

  return (
    <div className="viz-heatmap-wrap">
      <div className="viz-heatmap-y-label">Mel Band</div>
      <div className="viz-heatmap-canvas-wrap">
        <canvas
          ref={ref}
          className="viz-canvas"
          aria-label="Mel spectrogram heatmap"
          style={{ width: "100%", height: 180 }}
        />
        <div className="viz-heatmap-scale viz-heatmap-scale--mel" aria-hidden="true" />
      </div>
      <div className="viz-heatmap-x-label">Time Frame (0 → {cols})</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2. MFCC Heatmap
// ---------------------------------------------------------------------------
function MfccHeatmap({ viz }: { viz: VisualizationData }) {
  const colorFn = useCallback(mfccColor, []);
  const ref = useHeatmap(viz.mfcc_matrix, colorFn);
  const cols = viz.mfcc_matrix[0]?.length ?? 1;

  return (
    <div className="viz-heatmap-wrap">
      <div className="viz-heatmap-y-label">MFCC #</div>
      <div className="viz-heatmap-canvas-wrap">
        <canvas
          ref={ref}
          className="viz-canvas"
          aria-label="MFCC coefficient heatmap"
          style={{ width: "100%", height: 160 }}
        />
        <div className="viz-heatmap-scale viz-heatmap-scale--mfcc" aria-hidden="true" />
      </div>
      <div className="viz-heatmap-x-label">Time Frame (0 → {cols})</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 3. RT60 / Schroeder Decay Graph
// ---------------------------------------------------------------------------
function RT60Graph({ viz, rt60 }: { viz: VisualizationData; rt60: number | null }) {
  const data = viz.schroeder_curve.map((v, i) => ({
    t: (i / Math.max(viz.schroeder_curve.length - 1, 1)).toFixed(2),
    dB: parseFloat(v.toFixed(2)),
  }));

  return (
    <div className="viz-chart-wrap">
      {rt60 !== null && (
        <p className="viz-chart-caption">
          Estimated RT60: <strong style={{ color: C_CYAN }}>{rt60.toFixed(3)} s</strong>
          <span className="viz-chart-hint"> — time for decay to reach –60 dB</span>
        </p>
      )}
      {data.length === 0 ? (
        <p className="viz-empty">Schroeder curve unavailable for this signal.</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="schroederGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={C_BLUE} stopOpacity={0.4} />
                <stop offset="95%" stopColor={C_BLUE} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={C_GRID} />
            <XAxis dataKey="t" tick={{ fill: C_MUTED, fontSize: 10 }} label={{ value: "Norm. Time", position: "insideBottomRight", fill: C_MUTED, fontSize: 10, offset: -4 }} />
            <YAxis domain={[-80, 0]} tick={{ fill: C_MUTED, fontSize: 10 }} tickFormatter={(v: number) => `${v}dB`} />
            <Tooltip content={<DarkTip />} />
            <ReferenceLine y={-60} stroke={C_RED} strokeDasharray="4 3" label={{ value: "–60 dB (RT60)", fill: C_RED, fontSize: 9 }} />
            <ReferenceLine y={-5}  stroke={C_MUTED} strokeDasharray="2 3" />
            <Area type="monotone" dataKey="dB" stroke={C_BLUE} fill="url(#schroederGrad)" strokeWidth={1.5} dot={false} name="Level (dB)" />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 4. RIR Energy Graph
// ---------------------------------------------------------------------------
function RIRGraph({ viz }: { viz: VisualizationData }) {
  const data = viz.rir_curve.map((v, i) => ({
    frame: i,
    energy: parseFloat(v.toFixed(5)),
  }));

  return (
    <div className="viz-chart-wrap">
      <p className="viz-chart-caption">
        Percussive (room reflection) energy over time
        <span className="viz-chart-hint"> — higher variance = more natural room</span>
      </p>
      {data.length === 0 ? (
        <p className="viz-empty">RIR curve unavailable.</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="rirGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={C_CYAN} stopOpacity={0.4} />
                <stop offset="95%" stopColor={C_CYAN} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={C_GRID} />
            <XAxis dataKey="frame" tick={{ fill: C_MUTED, fontSize: 10 }} label={{ value: "Frame", position: "insideBottomRight", fill: C_MUTED, fontSize: 10, offset: -4 }} />
            <YAxis tick={{ fill: C_MUTED, fontSize: 10 }} tickFormatter={(v: number) => v.toFixed(3)} />
            <Tooltip content={<DarkTip />} />
            <Area type="monotone" dataKey="energy" stroke={C_CYAN} fill="url(#rirGrad)" strokeWidth={1.5} dot={false} name="RIR Energy" />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 5. Frequency Spectrum
// ---------------------------------------------------------------------------
function FrequencySpectrum({ viz }: { viz: VisualizationData }) {
  const data = viz.freq_hz.map((hz, i) => ({
    hz: Math.round(hz),
    mag: parseFloat((viz.freq_bins[i] ?? 0).toFixed(4)),
  }));

  return (
    <div className="viz-chart-wrap">
      <p className="viz-chart-caption">
        Magnitude spectrum (averaged over time)
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="freqGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={C_GREEN} stopOpacity={0.45} />
              <stop offset="95%" stopColor={C_GREEN} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={C_GRID} />
          <XAxis dataKey="hz" tick={{ fill: C_MUTED, fontSize: 10 }} tickFormatter={(v: number) => `${v >= 1000 ? (v / 1000).toFixed(1) + "k" : v}Hz`} interval="preserveStartEnd" />
          <YAxis tick={{ fill: C_MUTED, fontSize: 10 }} />
          <Tooltip content={<DarkTip />} />
          <Area type="monotone" dataKey="mag" stroke={C_GREEN} fill="url(#freqGrad)" strokeWidth={1.5} dot={false} name="Magnitude" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 6. Confidence Gauge (SVG arc)
// ---------------------------------------------------------------------------
function ConfidenceGauge({
  confidence,
  prediction,
}: {
  confidence: number;
  prediction: "Real" | "Deepfake";
}) {
  const isFake = prediction === "Deepfake";
  const color = isFake ? C_RED : C_GREEN;
  const pct = Math.min(100, Math.max(0, confidence));

  // Arc geometry: semicircle from -180° to 0° (left to right across top)
  const R = 70;       // radius
  const CX = 100;     // centre x in a 200×120 viewBox
  const CY = 100;     // centre y
  const startAngle = -180;
  const sweepAngle = 180 * (pct / 100);

  function polar(deg: number) {
    const rad = (deg * Math.PI) / 180;
    return { x: CX + R * Math.cos(rad), y: CY + R * Math.sin(rad) };
  }

  const s = polar(startAngle);
  const e = polar(startAngle + sweepAngle);
  const large = sweepAngle > 180 ? 1 : 0;
  const arcPath = `M ${s.x} ${s.y} A ${R} ${R} 0 ${large} 1 ${e.x} ${e.y}`;
  const trackPath = `M ${polar(startAngle).x} ${polar(startAngle).y} A ${R} ${R} 0 1 1 ${polar(startAngle + 180).x} ${polar(startAngle + 180).y}`;

  // Needle
  const needleAngle = startAngle + (180 * pct / 100);
  const needleTip = polar(needleAngle);

  return (
    <div className="viz-gauge-wrap" aria-label={`Confidence gauge: ${pct.toFixed(1)}%`}>
      <svg viewBox="0 0 200 120" className="viz-gauge-svg" role="img">
        {/* Track */}
        <path d={trackPath} fill="none" stroke={C_GRID} strokeWidth={14} strokeLinecap="round" />
        {/* Fill */}
        {pct > 0 && (
          <path d={arcPath} fill="none" stroke={color} strokeWidth={14} strokeLinecap="round" />
        )}
        {/* Gradient glow */}
        <path d={arcPath} fill="none" stroke={color} strokeWidth={4} strokeLinecap="round" opacity={0.35} />
        {/* Needle */}
        <line x1={CX} y1={CY} x2={needleTip.x} y2={needleTip.y} stroke={color} strokeWidth={2} strokeLinecap="round" />
        <circle cx={CX} cy={CY} r={5} fill={color} />
        {/* Labels */}
        <text x={CX - R - 6} y={CY + 16} textAnchor="middle" fontSize={9} fill={C_MUTED}>0%</text>
        <text x={CX + R + 6} y={CY + 16} textAnchor="middle" fontSize={9} fill={C_MUTED}>100%</text>
        {/* Value */}
        <text x={CX} y={CY - 16} textAnchor="middle" fontSize={22} fontWeight="bold" fill={color} fontFamily="Space Grotesk, sans-serif">
          {pct.toFixed(1)}%
        </text>
        <text x={CX} y={CY + 2} textAnchor="middle" fontSize={10} fill={C_MUTED}>
          {isFake ? "Deepfake" : "Authentic"}
        </text>
      </svg>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 7. Suspicious Segment Timeline
// ---------------------------------------------------------------------------
function SuspiciousTimeline({
  segments,
  inferenceSec,
}: {
  segments: SuspiciousSegment[];
  inferenceSec: number;
}) {
  // Estimate total duration from segment end times; fallback to inference_time_sec
  const maxEnd = segments.length > 0
    ? Math.max(...segments.map((s) => s.end_sec))
    : 0;
  const totalSec = Math.max(maxEnd * 1.15, inferenceSec, 1);

  const BAR_H = 28;
  const RULER_H = 18;
  const W = 100;   // percentage-based via viewBox

  // Tick marks every ~10% of total
  const ticks = Array.from({ length: 11 }, (_, i) => i * (totalSec / 10));

  return (
    <div className="viz-timeline-wrap" aria-label="Suspicious segment timeline">
      {segments.length === 0 ? (
        <div className="viz-timeline-clean">
          <span className="viz-timeline-clean-icon" aria-hidden="true">✅</span>
          <p>No suspicious segments detected — entire audio is within normal bounds.</p>
        </div>
      ) : (
        <>
          <p className="viz-chart-caption">
            {segments.length} suspicious region{segments.length !== 1 ? "s" : ""} flagged
          </p>
          <svg
            viewBox={`0 0 ${W} ${BAR_H + RULER_H + 4}`}
            className="viz-timeline-svg"
            preserveAspectRatio="none"
            role="img"
          >
            {/* Background track */}
            <rect x={0} y={0} width={W} height={BAR_H} rx={3} ry={3} fill={C_GRID} />

            {/* Segment fills */}
            {segments.map((seg, i) => {
              const x = (seg.start_sec / totalSec) * W;
              const w = Math.max(((seg.end_sec - seg.start_sec) / totalSec) * W, 1);
              return (
                <g key={i}>
                  <rect x={x} y={0} width={w} height={BAR_H} rx={2} ry={2} fill={C_RED} opacity={0.75} />
                  <title>{`Suspicious: ${seg.start_sec.toFixed(2)}s – ${seg.end_sec.toFixed(2)}s`}</title>
                </g>
              );
            })}

            {/* Ruler ticks */}
            {ticks.map((t, i) => {
              const x = (t / totalSec) * W;
              return (
                <g key={i}>
                  <line x1={x} y1={BAR_H} x2={x} y2={BAR_H + 4} stroke={C_MUTED} strokeWidth={0.5} />
                  <text x={x} y={BAR_H + RULER_H} textAnchor="middle" fontSize={4} fill={C_MUTED}>
                    {t.toFixed(1)}s
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Legend */}
          <div className="viz-timeline-legend">
            {segments.map((seg, i) => (
              <span key={i} className="viz-timeline-badge">
                {seg.start_sec.toFixed(2)}s – {seg.end_sec.toFixed(2)}s
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab definitions
// ---------------------------------------------------------------------------
type TabId =
  | "mel"
  | "mfcc"
  | "rt60"
  | "rir"
  | "spectrum"
  | "gauge"
  | "timeline";

interface TabDef {
  id: TabId;
  label: string;
  icon: string;
}

const TABS: TabDef[] = [
  { id: "mel",      label: "Mel Spectrogram",   icon: "🎨" },
  { id: "mfcc",     label: "MFCC Heatmap",      icon: "📐" },
  { id: "rt60",     label: "RT60 Decay",        icon: "🔊" },
  { id: "rir",      label: "RIR Energy",        icon: "〰️" },
  { id: "spectrum", label: "Frequency Spectrum",icon: "📡" },
  { id: "gauge",    label: "Confidence Gauge",  icon: "🎯" },
  { id: "timeline", label: "Suspicious Regions",icon: "⚠️" },
];

// ---------------------------------------------------------------------------
// Main exported component
// ---------------------------------------------------------------------------
interface Props {
  result: AnalyzeResponse;
}

export default function VisualizationSuite({ result }: Props) {
  const [activeTab, setActiveTab] = useState<TabId>("mel");
  const viz = result.viz;

  // Pull RT60 from the viz-independent route: it's on the explanation or directly
  // available as a plain number — we read it from the mfcc_matrix presence check
  const rt60Value: number | null = (() => {
    // Try to parse from explanation's rt60_explanation text — not reliable.
    // The value is available from the backend in viz but not directly exposed;
    // use a regex parse of the explanation text as fallback.
    const txt = result.explanation?.rt60_explanation ?? "";
    const m = txt.match(/RT60\s*=\s*([\d.]+)/);
    return m ? parseFloat(m[1]) : null;
  })();

  if (!viz) {
    return (
      <div className="viz-unavailable">
        <p>Visualization data is not available for this analysis (legacy record).</p>
      </div>
    );
  }

  function renderTab(): ReactNode {
    if (!viz) return null;
    switch (activeTab) {
      case "mel":
        return <MelSpectrogram viz={viz} />;
      case "mfcc":
        return <MfccHeatmap viz={viz} />;
      case "rt60":
        return <RT60Graph viz={viz} rt60={rt60Value} />;
      case "rir":
        return <RIRGraph viz={viz} />;
      case "spectrum":
        return <FrequencySpectrum viz={viz} />;
      case "gauge":
        return (
          <ConfidenceGauge
            confidence={result.confidence}
            prediction={result.prediction}
          />
        );
      case "timeline":
        return (
          <SuspiciousTimeline
            segments={result.suspicious_segments}
            inferenceSec={result.inference_time_sec}
          />
        );
    }
  }

  return (
    <section className="viz-suite" aria-label="Audio visualizations">
      <div className="viz-suite-header">
        <h3 className="viz-suite-title">
          <span aria-hidden="true">📈</span> Acoustic Visualizations
        </h3>
      </div>

      {/* Tab bar */}
      <div className="viz-tabs" role="tablist" aria-label="Visualization tabs">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`viz-panel-${tab.id}`}
            className={`viz-tab ${activeTab === tab.id ? "viz-tab--active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span aria-hidden="true">{tab.icon}</span>
            <span className="viz-tab-label">{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Panel */}
      <div
        id={`viz-panel-${activeTab}`}
        role="tabpanel"
        className="viz-panel"
        aria-label={TABS.find((t) => t.id === activeTab)?.label}
      >
        {renderTab()}
      </div>
    </section>
  );
}
