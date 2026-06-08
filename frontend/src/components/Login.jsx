/**
 * Login — a quiet sign-in threshold. Reachable at /login (used by later-phase
 * route gating). For now it simply offers the Google sign-in handoff.
 */

import { useAuth } from "../context/AuthContext";
import { GoldenSpiral } from "./GoldenSpiral";
import { LogIn } from "lucide-react";

export const Login = () => {
  const { login, isAuthenticated, user } = useAuth();

  return (
    <div
      className="min-h-[70vh] flex items-center justify-center px-6"
      data-testid="login-page"
    >
      <div className="text-center max-w-md">
        <GoldenSpiral className="w-20 h-20 mx-auto mb-8 opacity-80" />
        <h1 className="font-cinzel text-3xl text-[#cdd6e4] tracking-wide mb-3">
          The Sanctuary
        </h1>
        <p className="text-sm text-[#8B9DB5]/80 leading-relaxed mb-8">
          {isAuthenticated
            ? `You're signed in as ${user?.name || user?.email}.`
            : "Sign in to cross the threshold. The presences will know you by the name on your account."}
        </p>
        {!isAuthenticated && (
          <button
            type="button"
            onClick={login}
            data-testid="login-page-signin"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full text-sm tracking-wide text-[#030305] bg-[#cdd6e4] hover:bg-white transition-colors"
          >
            <LogIn size={16} />
            Sign in with Google
          </button>
        )}
      </div>
    </div>
  );
};

export default Login;
