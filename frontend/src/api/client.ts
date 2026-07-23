import axios from "axios";
import type {
  AnalyzeResponse,
  DashboardStats,
  HistoryResponse,
  LoginPayload,
  RefreshPayload,
  RegisterPayload,
  TokenResponse,
  User,
} from "../types";

// ---------------------------------------------------------------------------
// Axios instance
// ---------------------------------------------------------------------------
const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  timeout: 60_000,
});

// ---------------------------------------------------------------------------
// Storage helpers — read access token for outgoing requests.
// These mirror the keys used in AuthContext without importing it (avoids a
// circular dependency: client ← AuthContext ← client).
// ---------------------------------------------------------------------------
const ACCESS_KEY = "as_access_token";
const REFRESH_KEY = "as_refresh_token";

function getAccessToken(): string | null {
  return sessionStorage.getItem(ACCESS_KEY);
}

function getRefreshToken(): string | null {
  return (
    localStorage.getItem(REFRESH_KEY) ?? sessionStorage.getItem(REFRESH_KEY)
  );
}

function storeAccessToken(token: string): void {
  sessionStorage.setItem(ACCESS_KEY, token);
}

// ---------------------------------------------------------------------------
// Request interceptor — attach Bearer token to every outgoing request
// ---------------------------------------------------------------------------
client.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  console.debug(
    `[axios] ${config.method?.toUpperCase()} ${config.baseURL ?? ""}${config.url}`,
    "Content-Type:", config.headers?.["Content-Type"] ?? "(auto)",
    "body:", typeof config.data === "string" ? config.data.slice(0, 200) : config.data,
  );
  return config;
});

// ---------------------------------------------------------------------------
// Response interceptor — silent token refresh on 401
// ---------------------------------------------------------------------------
let _isRefreshing = false;
let _refreshQueue: Array<(token: string | null) => void> = [];

function processQueue(token: string | null): void {
  _refreshQueue.forEach((cb) => cb(token));
  _refreshQueue = [];
}

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    // Log every error response for DevTools visibility
    console.error(
      `[axios] ERROR ${error.response?.status ?? "network"} on ${original?.method?.toUpperCase()} ${original?.url}`,
      "\nResponse body:", error.response?.data,
    );

    // Only attempt refresh once per request and only for 401 responses.
    // Skip the refresh endpoint itself to avoid infinite loops.
    if (
      error.response?.status !== 401 ||
      original._retry ||
      original.url?.includes("/auth/refresh") ||
      original.url?.includes("/auth/login")
    ) {
      return Promise.reject(error);
    }

    original._retry = true;

    if (_isRefreshing) {
      return new Promise((resolve, reject) => {
        _refreshQueue.push((token) => {
          if (token) {
            original.headers["Authorization"] = `Bearer ${token}`;
            resolve(client(original));
          } else {
            reject(error);
          }
        });
      });
    }

    _isRefreshing = true;
    const refresh = getRefreshToken();

    if (!refresh) {
      _isRefreshing = false;
      processQueue(null);
      return Promise.reject(error);
    }

    try {
      const { data } = await axios.post<TokenResponse>(
        `${client.defaults.baseURL}/auth/refresh`,
        { refresh_token: refresh }
      );
      storeAccessToken(data.access_token);
      processQueue(data.access_token);
      original.headers["Authorization"] = `Bearer ${data.access_token}`;
      return client(original);
    } catch (refreshError) {
      processQueue(null);
      return Promise.reject(refreshError);
    } finally {
      _isRefreshing = false;
    }
  }
);

// ---------------------------------------------------------------------------
// Auth API calls
// ---------------------------------------------------------------------------
export async function apiRegister(payload: RegisterPayload): Promise<User> {
  console.debug("[auth] apiRegister →", { email: payload.email, username: payload.username });
  const { data } = await client.post<User>("/auth/register", payload);
  console.debug("[auth] apiRegister ← HTTP 201", { user: data });
  return data;
}

export async function apiLogin(payload: LoginPayload): Promise<TokenResponse> {
  console.debug("[auth] apiLogin →", { url: `${client.defaults.baseURL}/auth/login`, payload: { ...payload, password: "***" } });
  const { data } = await client.post<TokenResponse>("/auth/login", payload);
  console.debug("[auth] apiLogin ← HTTP 200", { keys: Object.keys(data), user: data.user });
  return data;
}

export async function apiRefresh(payload: RefreshPayload): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>("/auth/refresh", payload);
  return data;
}

export async function apiLogout(): Promise<void> {
  await client.post("/auth/logout");
}

export async function apiGetMe(): Promise<User> {
  const { data } = await client.get<User>("/auth/me");
  return data;
}

// ---------------------------------------------------------------------------
// Existing audio analysis API calls (unchanged)
// ---------------------------------------------------------------------------
export async function analyzeAudio(file: File): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const { data } = await client.post<AnalyzeResponse>("/analyze", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getHistory(): Promise<HistoryResponse> {
  const { data } = await client.get<HistoryResponse>("/history");
  return data;
}

export async function deleteAnalysis(id: string): Promise<{ deleted: string }> {
  const { data } = await client.delete<{ deleted: string }>(`/history/${id}`);
  return data;
}

export async function deleteAllAnalyses(): Promise<{ deleted: number }> {
  const { data } = await client.delete<{ deleted: number }>("/history");
  return data;
}

export async function getHealth() {
  const { data } = await client.get("/health");
  return data;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await client.get<DashboardStats>("/dashboard-stats");
  return data;
}

/**
 * Download a PDF report for the given analysis ID.
 * Uses a raw axios call with responseType "blob" so the binary PDF
 * is not decoded as text, then triggers a browser file download.
 */
export async function downloadReport(id: string): Promise<void> {
  const response = await client.get(`/report/${id}`, {
    responseType: "blob",
  });

  const blob = new Blob([response.data as BlobPart], {
    type: "application/pdf",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `acousticspace-report-${id}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default client;
