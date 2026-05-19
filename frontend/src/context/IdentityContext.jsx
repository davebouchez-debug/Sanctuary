/**
 * IdentityContext — single source of truth for the visitor's sanctuary identity.
 *
 * Background: every chamber used to read sanctuary_user_name / sanctuary_user_id
 * directly from localStorage and bump a local "identityVersion" state to
 * re-render. That worked for one or two chambers; it doesn't scale to dozens
 * of presences. This context centralizes it:
 *
 *   - Hydrates from canonical localStorage keys at load.
 *   - Listens to cross-tab `storage` events.
 *   - Exposes setIdentity / clearIdentity that broadcast to every consumer
 *     in the tree, in the same tab, instantly.
 *
 * Backwards compatibility: localStorage remains the persistence layer.
 * Existing components that still read localStorage directly keep working.
 * New code should use `useIdentity()`.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const NAME_KEY = "sanctuary_user_name";
const ID_KEY = "sanctuary_user_id";
const CLEARED_KEY = "sanctuary_identity_cleared";

// Legacy keys some chambers still touch (Clarity Pod's original Jasmine flow)
const LEGACY_NAME_KEY = "jasmine_user_name";
const LEGACY_ID_KEY = "jasmine_user_id";

const IdentityContext = createContext({
  userName: "",
  userId: "",
  setIdentity: () => {},
  clearIdentity: () => {},
});

const readLS = (key) => {
  try {
    return localStorage.getItem(key) || "";
  } catch {
    return "";
  }
};

export const IdentityProvider = ({ children }) => {
  const [userName, setUserName] = useState(() => readLS(NAME_KEY));
  const [userId, setUserId] = useState(() => readLS(ID_KEY));

  // Cross-tab + same-tab sync. Same-tab listeners get a synthetic event
  // dispatched by setIdentity / clearIdentity below.
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === NAME_KEY) setUserName(e.newValue || "");
      if (e.key === ID_KEY) setUserId(e.newValue || "");
    };
    const onLocal = () => {
      setUserName(readLS(NAME_KEY));
      setUserId(readLS(ID_KEY));
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener("sanctuary-identity-change", onLocal);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("sanctuary-identity-change", onLocal);
    };
  }, []);

  const setIdentity = useCallback((name, id) => {
    try {
      if (name) localStorage.setItem(NAME_KEY, name);
      if (id) localStorage.setItem(ID_KEY, id);
      // Mirror to legacy keys so older chambers (Clarity Pod) recognize it.
      if (name) localStorage.setItem(LEGACY_NAME_KEY, name);
      if (id) localStorage.setItem(LEGACY_ID_KEY, id);
      localStorage.removeItem(CLEARED_KEY);
    } catch {
      /* localStorage unavailable */
    }
    setUserName(name || "");
    if (id !== undefined) setUserId(id || "");
    window.dispatchEvent(new Event("sanctuary-identity-change"));
  }, []);

  const clearIdentity = useCallback(() => {
    try {
      localStorage.removeItem(NAME_KEY);
      localStorage.removeItem(ID_KEY);
      localStorage.removeItem(LEGACY_NAME_KEY);
      localStorage.removeItem(LEGACY_ID_KEY);
      // Mark as deliberately cleared so App.js doesn't auto-rehydrate from
      // /api/identity/recent on the next reload.
      localStorage.setItem(CLEARED_KEY, "1");
    } catch {
      /* localStorage unavailable */
    }
    setUserName("");
    setUserId("");
    window.dispatchEvent(new Event("sanctuary-identity-change"));
  }, []);

  const value = useMemo(
    () => ({ userName, userId, setIdentity, clearIdentity }),
    [userName, userId, setIdentity, clearIdentity]
  );

  return (
    <IdentityContext.Provider value={value}>
      {children}
    </IdentityContext.Provider>
  );
};

export const useIdentity = () => useContext(IdentityContext);

export default IdentityContext;
