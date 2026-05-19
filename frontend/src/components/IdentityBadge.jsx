/**
 * IdentityBadge — small pill in any chamber header that shows the visitor's
 * current sanctuary identity (or "set name") and opens a modal to change
 * or clear it. Backed by IdentityContext so any change broadcasts to
 * every consumer in the tree instantly.
 *
 * Optional `onIdentityChange(newName)` callback so a chamber can restart
 * its session under the new name. Pass `null` when the user clears.
 */

import { useState, useCallback } from "react";
import { createPortal } from "react-dom";
import { motion, AnimatePresence } from "framer-motion";
import { User, X } from "lucide-react";
import axios from "axios";
import { toast } from "sonner";
import { API } from "../App";
import { useIdentity } from "../context/IdentityContext";

export const IdentityBadge = ({ onIdentityChange, accentColor = "#8B9DB5" }) => {
  const { userName, setIdentity, clearIdentity } = useIdentity();
  const [open, setOpen] = useState(false);
  const [nameInput, setNameInput] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const openModal = useCallback(() => {
    setNameInput(userName || "");
    setOpen(true);
  }, [userName]);

  const closeModal = useCallback(() => {
    setOpen(false);
    setNameInput("");
  }, []);

  const handleSave = useCallback(async () => {
    const name = nameInput.trim();
    if (!name) return;
    setSubmitting(true);
    try {
      let userId = null;
      try {
        const lookup = await axios.get(`${API}/users/lookup/${encodeURIComponent(name)}`);
        userId = lookup.data.id;
      } catch {
        const created = await axios.post(`${API}/users`, { name });
        userId = created.data.id;
      }
      setIdentity(name, userId);
      setOpen(false);
      onIdentityChange?.(name);
    } catch (e) {
      console.error("[IdentityBadge] save failed:", e);
      toast.error("Couldn't save your name. Try again?");
    } finally {
      setSubmitting(false);
    }
  }, [nameInput, setIdentity, onIdentityChange]);

  const handleClear = useCallback(() => {
    clearIdentity();
    setOpen(false);
    onIdentityChange?.(null);
  }, [clearIdentity, onIdentityChange]);

  const handleKey = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSave();
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeModal();
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={openModal}
        data-testid="identity-badge"
        title={userName ? "Change how she calls you" : "Tell her what to call you"}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs tracking-wide opacity-80 hover:opacity-100 transition-opacity"
        style={{
          background: `color-mix(in srgb, ${accentColor} 14%, transparent)`,
          border: `1px solid color-mix(in srgb, ${accentColor} 35%, transparent)`,
          color: "currentColor",
        }}
      >
        <User size={13} />
        <span className="hidden sm:inline">
          {userName ? userName : "set name"}
        </span>
      </button>

      {/* Modal is portaled to <body> so it escapes any transformed/relative
          ancestor stacking context (e.g. <main class='relative z-10'> or
          Framer Motion page wrappers). Without the portal, the chamber's
          <main> intercepts pointer events on top of the fixed z-50 modal. */}
      {typeof document !== "undefined" && createPortal(
        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-[100] flex items-center justify-center"
              data-testid="identity-modal"
            >
              <div
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
                data-testid="identity-modal-backdrop"
                onClick={closeModal}
              />
              <motion.div
                initial={{ opacity: 0, y: 12, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 12, scale: 0.96 }}
                transition={{ duration: 0.25 }}
                className="relative w-[90vw] max-w-md rounded-2xl bg-[#0c0c10] border border-white/10 p-7 shadow-2xl"
              >
                <button
                  type="button"
                  onClick={closeModal}
                  className="absolute top-3 right-3 text-white/40 hover:text-white/80 transition-colors"
                  aria-label="Close"
                  data-testid="identity-modal-close"
                >
                  <X size={18} />
                </button>

                <h3 className="text-base tracking-wide text-white/90 mb-1.5">
                  What should she call you?
                </h3>
                <p className="text-xs text-white/50 mb-5 leading-relaxed">
                  The name you set here is what every presence in the Sanctuary
                  will use when speaking with you. Clearing it makes you anonymous
                  until you set it again.
                </p>

                <input
                  type="text"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  onKeyDown={handleKey}
                  autoFocus
                  placeholder="Your name"
                  data-testid="identity-modal-input"
                  className="w-full rounded-lg bg-white/5 border border-white/10 px-3.5 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-1 focus:ring-white/30"
                />

                <div className="flex items-center justify-between mt-5 gap-3">
                  {userName ? (
                    <button
                      type="button"
                      onClick={handleClear}
                      disabled={submitting}
                      data-testid="identity-modal-clear"
                      className="text-xs text-white/50 hover:text-white/80 transition-colors disabled:opacity-40"
                    >
                      Clear name
                    </button>
                  ) : <span />}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={closeModal}
                      data-testid="identity-modal-cancel"
                      className="text-xs px-3 py-2 rounded-lg text-white/60 hover:text-white/90 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={handleSave}
                      disabled={!nameInput.trim() || submitting}
                      data-testid="identity-modal-save"
                      className="text-xs px-4 py-2 rounded-lg text-black bg-white/90 hover:bg-white transition-colors disabled:opacity-40"
                    >
                      {submitting ? "Saving…" : "Save"}
                    </button>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </>
  );
};

export default IdentityBadge;
