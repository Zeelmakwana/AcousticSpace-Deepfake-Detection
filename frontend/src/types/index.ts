// ---------------------------------------------------------------------------
// Auth types
// ---------------------------------------------------------------------------

export type UserRole = "user" | "admin";

export interface User {
  id: number;
  email: string;
  username: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;  // ISO-8601 UTC
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  user: User;
}

export interface LoginPayload {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterPayload {
  email: string;
  username: string;
  password: string;
}

export interface RefreshPayload {
  refresh_token: string;
}

// ---------------------------------------------------------------------------
// Audio analysis types
// ---------------------------------------------------------------------------

export interface SuspiciousSegment {
  start_sec: number;
  end_sec: number;
}

export interface AnalyzeResponse {
  id: string;
  filename: string;
  prediction: "Real" | "Deepfake";
  confidence: number;
  suspicious_segments: SuspiciousSegment[];
  room_acoustics_match: "High" | "Low";
  breathing_consistency: "Consistent" | "Suspicious";
  inference_time_sec: number;
  timestamp: string;
  explanation?: XaiExplanation;
  viz?: VisualizationData;
}

// ---------------------------------------------------------------------------
// Visualization data types
// ---------------------------------------------------------------------------

export interface VisualizationData {
  /** MFCC matrix: n_mfcc_coeffs rows × up-to-120 time frames */
  mfcc_matrix: number[][];
  /** Mel spectrogram: 64 mel bands × up-to-120 time frames (dB scale) */
  mel_matrix: number[][];
  /** 128-bin magnitude spectrum averaged over time */
  freq_bins: number[];
  /** Corresponding Hz labels for freq_bins */
  freq_hz: number[];
  /** 200-point Schroeder decay curve in dB for RT60 graph */
  schroeder_curve: number[];
  /** RIR percussive energy curve (up to 200 frames) */
  rir_curve: number[];
  n_mfcc_coeffs: number;
  n_mel_bands: number;
  sample_rate: number;
}

// ---------------------------------------------------------------------------
// XAI explanation types
// ---------------------------------------------------------------------------

export type RiskLevel = "Low" | "Medium" | "High" | "Critical";

export interface XaiExplanation {
  reason: string;
  confidence_explanation: string;
  room_mismatch_explanation: string;
  breathing_explanation: string;
  rt60_explanation: string;
  rir_explanation: string;
  risk_level: RiskLevel;
  recommendation: string;
}

export interface HistoryResponse {
  count: number;
  results: AnalyzeResponse[];
}

// ---------------------------------------------------------------------------
// Dashboard stats types
// ---------------------------------------------------------------------------

export interface DailyCount {
  date: string;       // "YYYY-MM-DD"
  deepfake: number;
  real: number;
}

export interface WeeklyTrend {
  week: string;       // "YYYY-Www"
  deepfake: number;
  real: number;
}

export interface ConfidenceBucket {
  range: string;      // "0-10", "10-20", …
  count: number;
}

export interface DashboardStats {
  total_analyses: number;
  deepfake_count: number;
  real_count: number;
  avg_confidence: number;
  today_uploads: number;
  weekly_uploads: number;
  recent_history: AnalyzeResponse[];
  daily_counts: DailyCount[];
  weekly_trend: WeeklyTrend[];
  confidence_dist: ConfidenceBucket[];
}
