/**
 * AcousticSpace — Dashboard Page
 * ================================
 * Aggregated analytics view with stat cards and three charts:
 *   • Pie Chart    — Real vs Deepfake distribution
 *   • Bar Chart    — Daily upload counts (last 30 days)
 *   • Line Chart   — Weekly upload trend (last 8 ISO weeks)
 *
 * Data is fetched from GET /dashboard-stats once on mount.
 * No ML logic is touched here.
 */

import { useEffect, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import { getDashboardStats } from "../api/client";
import type { DashboardStats } from "../types";

// ---------------------------------------------------------------------------
// Palette — matches AcousticSpace CSS variables
// ---------------------------------------------------------------------------
const COLOR_REAL = "#4fd68a";
const COLOR_FAKE = "#ff6b6b";
const COLOR_CYAN = "#4fd6e0";
const COLOR_BLUE = "#7c9dfc";
const TEXT_MUTED = "#93a0c4";
const GRID_LINE = "#2a3457";

// ---------------------------------------------------------------------------
// Small sub-components
// ---------------------------------------------------------------------------

interface StatCardProps {
  label: string;
  value: string | number;
  accent?: string;
  icon: string;
}

function StatCard({ label, value, accent = COLOR_CYAN, icon }: StatCardProps) {
  return (
    <div className="dash-stat-card">
      <span className="dash-stat-icon" aria-hidden="true">{icon}</span>
      <p className="dash-stat-value" style={{ color: accent }}>
        {value}
      </p>
      <p className="dash-stat-label">{label}</p>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h3 className="dash-section-title">{children}</h3>;
}

// ---------------------------------------------------------------------------
// Custom Recharts tooltip styled for the dark theme
// ---------------------------------------------------------------------------
function DarkTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="dash-tooltip">
      {label && <p className="dash-tooltip-label">{label}</p>}
      {payload.map((entry) => (
        <p key={entry.name} style={{ color: entry.color, margin: "2px 0" }}>
          {entry.name}: <strong>{entry.value}</strong>
        </p>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(() => setError("Failed to load dashboard stats. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  // ---- Loading state -------------------------------------------------------
  if (loading) {
    return (
      <div className="dash-page" aria-busy="true">
        <div className="auth-loading">
          <span className="auth-spinner" role="status" aria-label="Loading dashboard" />
        </div>
      </div>
    );
  }

  // ---- Error state ---------------------------------------------------------
  if (error || !stats) {
    return (
      <div className="dash-page">
        <p className="error-message">{error ?? "No data available."}</p>
      </div>
    );
  }

  // ---- Pie chart data: Real vs Deepfake ------------------------------------
  const pieData = [
    { name: "Real", value: stats.real_count },
    { name: "Deepfake", value: stats.deepfake_count },
  ];
  const PIE_COLORS = [COLOR_REAL, COLOR_FAKE];

  // ---- Bar chart: shorten date labels to "MM/DD" --------------------------
  const barData = stats.daily_counts.map((d) => ({
    ...d,
    dateLabel: d.date.slice(5).replace("-", "/"), // "MM/DD"
  }));

  // ---- Line chart: shorten week label to "Www" ----------------------------
  const lineData = stats.weekly_trend.map((w) => ({
    ...w,
    weekLabel: w.week.split("-")[1], // "W01", "W02", …
  }));

  // ---- Helpers -------------------------------------------------------------
  const noHistory = stats.recent_history.length === 0;

  return (
    <div className="dash-page">
      {/* ------------------------------------------------------------------ */}
      {/* Page header                                                          */}
      {/* ------------------------------------------------------------------ */}
      <div className="dash-header">
        <h2 className="dash-title">Dashboard</h2>
        <p className="dash-subtitle">
          Aggregated analytics across all audio analyses
        </p>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Stat cards row                                                       */}
      {/* ------------------------------------------------------------------ */}
      <section aria-label="Key metrics" className="dash-stats-grid">
        <StatCard
          icon="🎵"
          label="Total Analyses"
          value={stats.total_analyses}
        />
        <StatCard
          icon="⚠️"
          label="Deepfake Count"
          value={stats.deepfake_count}
          accent={COLOR_FAKE}
        />
        <StatCard
          icon="✅"
          label="Real Count"
          value={stats.real_count}
          accent={COLOR_REAL}
        />
        <StatCard
          icon="📊"
          label="Avg Confidence"
          value={`${stats.avg_confidence.toFixed(1)}%`}
          accent={COLOR_BLUE}
        />
        <StatCard
          icon="📅"
          label="Today's Uploads"
          value={stats.today_uploads}
          accent={COLOR_CYAN}
        />
        <StatCard
          icon="📆"
          label="Weekly Uploads"
          value={stats.weekly_uploads}
          accent={COLOR_CYAN}
        />
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Charts row                                                           */}
      {/* ------------------------------------------------------------------ */}
      <section aria-label="Charts" className="dash-charts-grid">

        {/* Pie: Real vs Deepfake */}
        <div className="dash-chart-card">
          <SectionTitle>Prediction Distribution</SectionTitle>
          {stats.total_analyses === 0 ? (
            <p className="dash-empty">No data yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  innerRadius={50}
                  paddingAngle={3}
                  label={({ name, percent }) =>
                    `${name} ${(percent * 100).toFixed(0)}%`
                  }
                  labelLine={false}
                >
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<DarkTooltip />} />
                <Legend
                  wrapperStyle={{ fontSize: "0.8rem", color: TEXT_MUTED }}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Bar: Daily uploads */}
        <div className="dash-chart-card">
          <SectionTitle>Daily Uploads — Last 30 Days</SectionTitle>
          {barData.length === 0 ? (
            <p className="dash-empty">No data in the last 30 days.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={barData}
                margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_LINE} />
                <XAxis
                  dataKey="dateLabel"
                  tick={{ fill: TEXT_MUTED, fontSize: 10 }}
                  interval="preserveStartEnd"
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: TEXT_MUTED, fontSize: 10 }}
                />
                <Tooltip content={<DarkTooltip />} />
                <Legend
                  wrapperStyle={{ fontSize: "0.8rem", color: TEXT_MUTED }}
                />
                <Bar dataKey="real" name="Real" fill={COLOR_REAL} radius={[3, 3, 0, 0]} />
                <Bar dataKey="deepfake" name="Deepfake" fill={COLOR_FAKE} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Line: Weekly trend */}
        <div className="dash-chart-card dash-chart-card--wide">
          <SectionTitle>Weekly Upload Trend — Last 8 Weeks</SectionTitle>
          {lineData.length === 0 ? (
            <p className="dash-empty">No data in the last 8 weeks.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart
                data={lineData}
                margin={{ top: 4, right: 16, left: -16, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_LINE} />
                <XAxis
                  dataKey="weekLabel"
                  tick={{ fill: TEXT_MUTED, fontSize: 11 }}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fill: TEXT_MUTED, fontSize: 11 }}
                />
                <Tooltip content={<DarkTooltip />} />
                <Legend
                  wrapperStyle={{ fontSize: "0.8rem", color: TEXT_MUTED }}
                />
                <Line
                  type="monotone"
                  dataKey="real"
                  name="Real"
                  stroke={COLOR_REAL}
                  strokeWidth={2}
                  dot={{ r: 3, fill: COLOR_REAL }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey="deepfake"
                  name="Deepfake"
                  stroke={COLOR_FAKE}
                  strokeWidth={2}
                  dot={{ r: 3, fill: COLOR_FAKE }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>

      {/* ------------------------------------------------------------------ */}
      {/* Recent history table                                                 */}
      {/* ------------------------------------------------------------------ */}
      <section aria-label="Recent analysis history">
        <SectionTitle>Recent History</SectionTitle>
        {noHistory ? (
          <p className="dash-empty">No analyses yet.</p>
        ) : (
          <div className="dash-table-wrapper">
            <table className="history-table dash-history-table">
              <thead>
                <tr>
                  <th>Filename</th>
                  <th>Prediction</th>
                  <th>Confidence</th>
                  <th>Room Match</th>
                  <th>Breathing</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {stats.recent_history.map((r) => (
                  <tr
                    key={r.id}
                    className={r.prediction === "Deepfake" ? "row-fake" : "row-real"}
                  >
                    <td className="dash-filename" title={r.filename}>
                      {r.filename.length > 28
                        ? `…${r.filename.slice(-26)}`
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
                    <td>{r.confidence.toFixed(1)}%</td>
                    <td>{r.room_acoustics_match}</td>
                    <td>{r.breathing_consistency}</td>
                    <td>{new Date(r.timestamp).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
