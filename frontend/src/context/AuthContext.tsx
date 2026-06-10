// frontend/src/context/AuthContext.tsx
// D-08: in-memory access token (not localStorage — XSS risk)
// T-03-01 mitigation: token lives in React Context / module-level memory only

import React, { createContext, useContext, useState, useCallback } from "react";
import { setAccessToken as syncAxiosToken } from "@/lib/axios";

interface AuthUser {
  id: number;
  role: string;
  email: string;
  full_name: string;
}

interface AuthState {
  accessToken: string | null;
  user: AuthUser | null;
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
  });

  const setAuth = useCallback((token: string, user: AuthUser) => {
    // Keep module-level axios token in sync with context (PATTERNS.md Pattern 5)
    syncAxiosToken(token);
    setAuthState({ accessToken: token, user });
  }, []);

  const clearAuth = useCallback(() => {
    // Clear module-level axios token
    syncAxiosToken(null);
    setAuthState({ accessToken: null, user: null });
  }, []);

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
