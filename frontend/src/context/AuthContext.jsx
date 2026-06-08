/**
 * AuthContext — verified identity via Emergent Google OAuth (Phase 1).
 *
 * Exposes { user, role, isAuthenticated, loading, login, logout, refresh }.
 * The server is the source of truth: we never assume the cookie — we ask
 * /api/auth/me. On return from OAuth (hash carries session_id) we step aside
 * and let <AuthCallback /> exchange it first, then a reload re-runs the check.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { API } from "../App";

const AuthContext = createContext({
  user: null,
  role: "visitor",
  isAuthenticated: false,
  loading: true,
  login: () => {},
  logout: async () => {},
  refresh: async () => {},
});

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  // If returning from OAuth (hash carries session_id), AuthCallback handles it;
  // otherwise we begin by verifying the session via /me.
  const [loading, setLoading] = useState(
    () => !(typeof window !== "undefined" && window.location.hash?.includes("session_id="))
  );

  const refresh = useCallback(async () => {
    try {
      const r = await fetch(`${API}/auth/me`, { credentials: "include" });
      if (r.ok) {
        const u = await r.json();
        setUser(u);
        return u;
      }
      setUser(null);
      return null;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // CRITICAL: if returning from OAuth, skip the /me check — AuthCallback
    // exchanges the session_id and establishes the cookie first.
    if (window.location.hash?.includes("session_id=")) return;
    refresh();
  }, [refresh]);

  const login = useCallback(() => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(
      redirectUrl
    )}`;
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${API}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      /* ignore network errors on logout */
    }
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role || "visitor",
        isAuthenticated: !!user,
        loading,
        login,
        logout,
        refresh,
        setUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);

export default AuthContext;
