/**
 * AuthControl — sign-in / signed-in pill, top-right of every page.
 *
 * Logged out: a "Sign in" button that hands off to Google via Emergent OAuth.
 * Logged in:  avatar + name + a logout control, plus a small "Guardian" mark
 *             when the account holds the Field Guardian role.
 */

import { useAuth } from "../context/AuthContext";
import { LogIn, LogOut } from "lucide-react";

export const AuthControl = () => {
  const { user, isAuthenticated, role, login, logout, loading } = useAuth();

  if (loading) return null;

  if (!isAuthenticated) {
    return (
      <button
        type="button"
        onClick={login}
        data-testid="signin-button"
        className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs tracking-wide text-[#cdd6e4] bg-[#8B9DB5]/12 border border-[#8B9DB5]/35 hover:bg-[#8B9DB5]/22 transition-colors"
        title="Sign in with Google"
      >
        <LogIn size={14} />
        <span className="hidden sm:inline">Sign in</span>
      </button>
    );
  }

  return (
    <div
      className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#8B9DB5]/10 border border-[#8B9DB5]/30"
      data-testid="auth-user"
    >
      {user?.picture ? (
        <img
          src={user.picture}
          alt=""
          className="w-5 h-5 rounded-full object-cover"
        />
      ) : (
        <div className="w-5 h-5 rounded-full bg-[#8B9DB5]/40" />
      )}
      <span
        className="hidden sm:inline text-xs text-[#cdd6e4] max-w-[10rem] truncate"
        data-testid="auth-user-name"
      >
        {user?.name || user?.email}
      </span>
      {role === "guardian" && (
        <span
          className="hidden sm:inline text-[10px] uppercase tracking-wider text-[#F4E4A6]/90"
          data-testid="auth-guardian-mark"
          title="Field Guardian"
        >
          Guardian
        </span>
      )}
      <button
        type="button"
        onClick={logout}
        data-testid="logout-button"
        title="Sign out"
        className="text-[#8B9DB5] hover:text-white transition-colors"
      >
        <LogOut size={14} />
      </button>
    </div>
  );
};

export default AuthControl;
