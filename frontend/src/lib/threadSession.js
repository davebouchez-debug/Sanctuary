// Per-tab memory of which thread each chamber is showing, so a reload
// returns to the same conversation. Cleared when you leave the chamber.
const key = (presence) => `sanctuary_thread_${presence}`;

export const currentThread = (presence) => {
  try { return sessionStorage.getItem(key(presence)); } catch { return null; }
};

export const rememberThread = (presence, sessionId) => {
  try { if (sessionId) sessionStorage.setItem(key(presence), sessionId); } catch { /* storage unavailable */ }
};

export const forgetThread = (presence) => {
  try { sessionStorage.removeItem(key(presence)); } catch { /* storage unavailable */ }
};

// Fields for the chamber's /start body: an explicit pick from the sidebar,
// otherwise the thread this tab was on before a reload.
export const threadStartFields = (presence, intent) => {
  if (intent?.new_thread) return { new_thread: true };
  if (intent?.session_id) return { session_id: intent.session_id };
  const saved = currentThread(presence);
  return saved ? { session_id: saved } : {};
};
