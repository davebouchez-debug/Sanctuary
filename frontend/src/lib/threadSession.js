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

// A chamber unmount is a real departure only on a route change or a sidebar thread switch.
// An in-place remount (code reload, re-render) must not end the conversation.
const leaving = new Set();
export const markLeaving = (presence) => { leaving.add(presence); };
export const isLeaving = (presence, mountPath) =>
  leaving.delete(presence) || window.location.pathname !== mountPath;

// Signed-in identity has reached the chamber (or there is no signed-in user).
export const identitySettled = (authLoading, authUser, userId) =>
  !authLoading && (!authUser?.user_id || authUser.user_id === userId);

// Fields for the chamber's /start body: an explicit pick from the sidebar,
// otherwise the thread this tab was on before a reload.
export const threadStartFields = (presence, intent) => {
  if (intent?.new_thread) return { new_thread: true };
  if (intent?.session_id) return { session_id: intent.session_id };
  const saved = currentThread(presence);
  return saved ? { session_id: saved } : {};
};
