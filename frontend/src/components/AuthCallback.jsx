/**
 * AuthCallback — one-time exchange of the OAuth session_id for a session.
 *
 * Emergent redirects back to {origin}/#session_id=<id>. We read that fragment,
 * POST it to the backend (which sets the httpOnly cookie), then hard-redirect
 * home so AuthProvider re-runs its /me check cleanly with no session_id in the
 * URL. useRef guards against StrictMode double-invoke.
 */

import { useEffect, useRef, useState } from "react";
import { GoldenSpiral } from "./GoldenSpiral";
import { API } from "../App";

export const AuthCallback = () => {
  const processed = useRef(false);
  const [refused, setRefused] = useState(null);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const hash = window.location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    const sessionId = match ? decodeURIComponent(match[1]) : null;

    const go = () => {
      // Clean the hash and land on the main app; full reload so AuthProvider
      // picks up the new cookie via /auth/me.
      window.location.replace(window.location.origin + "/");
    };

    (async () => {
      if (sessionId) {
        try {
          const r = await fetch(`${API}/auth/session`, {
            method: "POST",
            credentials: "include",
            headers: { "X-Session-ID": sessionId },
          });
          if (r.status === 403) {
            setRefused((await r.json()).detail);
            window.history.replaceState(null, "", window.location.pathname);
            return;
          }
        } catch {
          /* fall through — refresh on home will show signed-out state */
        }
      }
      go();
    })();
  }, []);

  if (refused) {
    return (
      <div className="fixed inset-0 bg-[#030305] flex items-center justify-center z-50 px-6" data-testid="auth-refused">
        <div className="text-center max-w-md">
          <GoldenSpiral className="w-20 h-20 mx-auto mb-8 opacity-60" />
          <p className="text-[#cdd6e4] font-outfit leading-relaxed mb-8" data-testid="auth-refused-message">{refused}</p>
          <a
            href="/"
            className="inline-flex px-6 py-3 rounded-full text-sm tracking-wide text-[#030305] bg-[#cdd6e4] hover:bg-white transition-colors"
            data-testid="auth-refused-continue"
          >
            Continue as a visitor
          </a>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 bg-[#030305] flex items-center justify-center z-50"
      data-testid="auth-callback"
    >
      <div className="text-center">
        <GoldenSpiral className="w-24 h-24 mx-auto mb-6 animate-rotate-slow" />
        <p className="text-[#8B9DB5] text-sm font-mono tracking-widest">
          Entering the Sanctuary…
        </p>
      </div>
    </div>
  );
};

export default AuthCallback;
