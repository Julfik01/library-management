// frontend/src/context/AuthContext.tsx
// D-08: in-memory access token (not localStorage — XSS risk)
// T-03-01 mitigation: token lives in React Context / module-level memory only

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
} from "react";
import { api, setAccessToken as syncAxiosToken } from "@/lib/axios";

interface AuthUser {
  id: number;
  role: string;
  email: string;
  full_name: string;
}

interface AuthState {
  accessToken: string | null;
  user: AuthUser | null;
  initialized: boolean;
}

interface AuthContextType extends AuthState {
  setAuth: (token: string, user: AuthUser) => void;
  clearAuth: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuthState] = useState<AuthState>({
    accessToken: null,
    user: null,
    initialized: false,
  });

  const setAuth = useCallback((token: string, user: AuthUser) => {
    syncAxiosToken(token);
    setAuthState({ accessToken: token, user, initialized: true });
  }, []);

  const clearAuth = useCallback(() => {
    syncAxiosToken(null);
    setAuthState((prev) => ({ ...prev, accessToken: null, user: null }));
  }, []);

  // Ref guard ensures bootstrap fires once — prevents StrictMode double-invoke
  // from consuming a rotation-based refresh token on the second call
  const bootstrapped = useRef(false);

  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;

    api
      .post("/auth/refresh")
      .then(({ data }) => {
        syncAxiosToken(data.access_token);
        // /auth/refresh now returns {access_token, token_type, user}
        setAuthState({
          accessToken: data.access_token,
          user: data.user ?? null,
          initialized: true,
        });
      })
      .catch(() => {
        // 401 = no cookie or expired — treat as logged out, not an error
        setAuthState((prev) => ({ ...prev, initialized: true }));
      });
  }, []);

  // Axios interceptor fires this when a mid-session refresh fails (T-03-05)
  // Using an event keeps the interceptor decoupled from React state
  useEffect(() => {
    const onSessionExpired = () => clearAuth();
    window.addEventListener("auth:session-expired", onSessionExpired);
    return () =>
      window.removeEventListener("auth:session-expired", onSessionExpired);
  }, [clearAuth]);

  return (
    <AuthContext.Provider value={{ ...auth, setAuth, clearAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};
