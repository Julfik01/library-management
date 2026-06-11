// frontend/src/lib/axios.ts
// CRITICAL: withCredentials: true — sends httpOnly refresh cookie (T-03-03)
// CRITICAL: Do NOT use allow_origins=["*"] on backend when withCredentials is set (T-03-04)
// D-08: No localStorage — access token in module-level memory only

import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  withCredentials: true, // CRITICAL: sends httpOnly refresh cookie
});

// Module-level ref avoids stale closure in interceptors
// AuthContext setAuth also calls setAccessToken to keep in sync
let accessToken: string | null = null;
export const setAccessToken = (t: string | null) => {
  accessToken = t;
};

// Request interceptor: inject Authorization header
api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers["Authorization"] = `Bearer ${accessToken}`;
  }
  return config;
});

// Response interceptor: on 401, attempt token refresh once, then replay queued requests
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (v: string) => void;
  reject: (e: unknown) => void;
}> = [];

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config;
    // Never retry the refresh endpoint itself — prevents the bootstrap 401-retry loop
    const isRefreshEndpoint = originalRequest?.url?.includes("/auth/refresh") === true;
    if (
      error.response?.status === 401 &&
      !originalRequest?._retry &&
      !isRefreshEndpoint
    ) {
      originalRequest._retry = true;
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers["Authorization"] = `Bearer ${token}`;
          return api(originalRequest);
        });
      }
      isRefreshing = true;
      try {
        // CRITICAL: use same api instance (withCredentials) for refresh (Pitfall 5)
        const { data } = await api.post("/auth/refresh");
        setAccessToken(data.access_token);
        failedQueue.forEach(({ resolve }) => resolve(data.access_token));
        failedQueue = [];
        originalRequest.headers["Authorization"] = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (e) {
        failedQueue.forEach(({ reject }) => reject(e));
        failedQueue = [];
        setAccessToken(null);
        // Dispatch event so AuthContext can clearAuth() and React Router can redirect.
        // Replacing window.location.href = "/login" prevents the hard-reload loop:
        // a hard reload re-runs bootstrap which fires another POST /auth/refresh → 401 → loop.
        window.dispatchEvent(new CustomEvent("auth:session-expired"));
        return Promise.reject(e);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);
