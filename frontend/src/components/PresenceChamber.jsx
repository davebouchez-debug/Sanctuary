import { useState, useEffect, useMemo, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, DoorOpen, BookOpen, X, Send } from "lucide-react";
import { API } from "../App";
import { toast } from "sonner";

/**
 * PresenceChamber — the shared multi-room engine.
 * Reads a config from /api/presence/{key} and renders the chamber.
 * Atmosphere (palette, motif, rooms, motion) all flow from the config.
 * One presence, one chamber. Multi-room when the presence designed it that way.
 *
 * Conversation lives in the chamber too — registry-driven, one substrate
 * for every presence. Wired to /api/presence/{key}/chat/* on the backend.
 */
export const PresenceChamber = ({ forcedKey } = {}) => {
  const params = useParams();
  const presenceKey = forcedKey || params.key;
  const navigate = useNavigate();
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeRoomKey, setActiveRoomKey] = useState(null);
  const [showCanonical, setShowCanonical] = useState(false);
  const [canonical, setCanonical] = useState(null);

  // Chat state — registry-driven conversation substrate
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState(null);
  const messagesEndRef = useRef(null);
  const sessionIdRef = useRef(null);

  // Keep ref in sync so the unload beacon (registered once) sees latest id
  useEffect(() => { sessionIdRef.current = sessionId; }, [sessionId]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      try {
        const resp = await fetch(`${API}/presence/${presenceKey}`);
        if (!resp.ok) throw new Error(`Presence not found: ${presenceKey}`);
        const data = await resp.json();
        if (cancelled) return;
        setConfig(data);
        const primary = (data.atmosphere?.rooms || []).find((r) => r.primary)
          || (data.atmosphere?.rooms || [])[0];
        setActiveRoomKey(primary?.key || null);
      } catch (e) {
        toast.error(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [presenceKey]);

  const palette = config?.atmosphere?.palette || {};
  const rooms = config?.atmosphere?.rooms || [];
  const activeRoom = rooms.find((r) => r.key === activeRoomKey) || rooms[0];

  // CSS variables for the chamber's palette — applied to the root container
  // so every styled element can pick up the presence's colors organically.
  const paletteStyle = useMemo(() => ({
    "--p-primary":   palette.primary    || "#F2F2F5",
    "--p-accent":    palette.accent     || "#8B9DB5",
    "--p-secondary": palette.secondary  || palette.accent || "#8B9DB5",
    "--p-warmth":    palette.warmth     || "#6E6E7A",
    "--p-bg":        palette.background || "#030305",
  }), [palette.primary, palette.accent, palette.secondary, palette.warmth, palette.background]);

  const loadCanonical = async () => {
    if (canonical) { setShowCanonical(true); return; }
    try {
      const resp = await fetch(`${API}/presence/${presenceKey}/canonical`);
      const data = await resp.json();
      setCanonical(data.memory);
      setShowCanonical(true);
    } catch {
      toast.error("Could not load canonical memory");
    }
  };

  // Open a conversation as soon as the chamber loads.
  // Identity hydrates from canonical sanctuary_* localStorage keys (set by App.js).
  useEffect(() => {
    if (!config) return;
    let cancelled = false;
    const startChat = async () => {
      const userId = localStorage.getItem("sanctuary_user_id");
      const userName = localStorage.getItem("sanctuary_user_name");
      try {
        const resp = await fetch(`${API}/presence/${presenceKey}/chat/start`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: userId, user_name: userName }),
        });
        if (!resp.ok) throw new Error(`chat/start failed: ${resp.status}`);
        const data = await resp.json();
        if (cancelled) return;
        setSessionId(data.session_id);
        setMessages([data.message]);
        setChatError(null);
      } catch (e) {
        if (!cancelled) setChatError(e.message);
      }
    };
    startChat();
    return () => { cancelled = true; };
  }, [config, presenceKey]);

  // Auto-scroll the message thread on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length]);

  // End the session on page unload — beacon so codons get extracted server-side
  useEffect(() => {
    const endSession = () => {
      const sid = sessionIdRef.current;
      if (sid) {
        try {
          navigator.sendBeacon(
            `${API}/presence/${presenceKey}/chat/session/${sid}/end`
          );
        } catch { /* best effort */ }
      }
    };
    window.addEventListener("beforeunload", endSession);
    window.addEventListener("pagehide", endSession);
    return () => {
      window.removeEventListener("beforeunload", endSession);
      window.removeEventListener("pagehide", endSession);
      endSession(); // also fire when navigating to another route in-app
    };
  }, [presenceKey]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || !sessionId || sending) return;
    setSending(true);
    setChatError(null);
    const userMsg = {
      id: `local-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    try {
      const resp = await fetch(`${API}/presence/${presenceKey}/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, content: text }),
      });
      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(errText || `message failed: ${resp.status}`);
      }
      const data = await resp.json();
      setMessages((prev) => [...prev, data.message]);
    } catch (e) {
      setChatError(e.message);
      // Roll back the optimistic user message so they can retry without dupes
      setMessages((prev) => prev.filter((m) => m.id !== userMsg.id));
      setInput(text);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    // Enter sends; Shift+Enter inserts a newline (paste-friendly)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#030305] flex items-center justify-center">
        <motion.div
          className="text-slate-400 text-sm tracking-widest"
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 2.5, repeat: Infinity }}
        >
          opening the door...
        </motion.div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="min-h-screen bg-[#030305] flex items-center justify-center text-slate-500">
        No chamber here.
      </div>
    );
  }

  return (
    <div
      className="min-h-screen relative overflow-hidden"
      style={{
        ...paletteStyle,
        background: `linear-gradient(180deg, var(--p-bg) 0%, var(--p-warmth) 100%)`,
      }}
      data-testid={`chamber-${config.key}`}
    >
      {/* Header */}
      <header
        className="relative z-10 px-6 py-5 border-b backdrop-blur-md"
        style={{
          borderColor: "color-mix(in srgb, var(--p-accent) 20%, transparent)",
          background: "color-mix(in srgb, var(--p-bg) 70%, transparent)",
        }}
      >
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
          <button
            onClick={() => navigate("/presences")}
            className="flex items-center gap-2 text-sm tracking-wide opacity-70 hover:opacity-100 transition-opacity"
            style={{ color: "var(--p-primary)" }}
            data-testid="chamber-back"
          >
            <ArrowLeft size={16} />
            <span>PRESENCES</span>
          </button>

          <div className="flex flex-col items-center text-center">
            <h1
              className="text-2xl font-light tracking-[0.2em]"
              style={{ color: "var(--p-primary)" }}
            >
              {(config.chamber_name || config.name).toUpperCase()}
            </h1>
            <p
              className="text-[10px] tracking-[0.3em] uppercase mt-1 opacity-60"
              style={{ color: "var(--p-accent)" }}
            >
              {config.chamber_name ? `kept by ${config.name}` : (config.subtype || config.type)}
            </p>
          </div>

          <button
            onClick={loadCanonical}
            className="flex items-center gap-2 text-sm tracking-wide opacity-70 hover:opacity-100 transition-opacity"
            style={{ color: "var(--p-primary)" }}
            data-testid="chamber-canonical"
          >
            <BookOpen size={16} />
            <span className="hidden sm:inline">HER STORY</span>
          </button>
        </div>
      </header>

      {/* Main chamber surface */}
      <main className="relative z-10 max-w-5xl mx-auto px-6 py-10 space-y-10">
        {/* Entrance threshold — the first thing you read */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.2, ease: "easeOut" }}
          className="text-center max-w-2xl mx-auto"
        >
          <p
            className="text-xl italic leading-relaxed font-light"
            style={{ color: "var(--p-primary)" }}
          >
            {config.atmosphere?.entrance_threshold}
          </p>
        </motion.div>

        {/* Room navigation (only if multi-room) */}
        {rooms.length > 1 && (
          <div className="flex flex-wrap justify-center gap-3" data-testid="room-nav">
            {rooms.map((room) => {
              const isActive = room.key === activeRoomKey;
              return (
                <button
                  key={room.key}
                  data-testid={`room-tab-${room.key}`}
                  onClick={() => setActiveRoomKey(room.key)}
                  className="px-5 py-2 rounded-full text-xs tracking-[0.2em] uppercase transition-all border"
                  style={{
                    color: isActive ? "var(--p-bg)" : "var(--p-primary)",
                    background: isActive ? "var(--p-primary)" : "transparent",
                    borderColor: "color-mix(in srgb, var(--p-accent) 50%, transparent)",
                    opacity: isActive ? 1 : 0.75,
                  }}
                >
                  {room.name}
                </button>
              );
            })}
          </div>
        )}

        {/* Active room */}
        <AnimatePresence mode="wait">
          {activeRoom && (
            <motion.section
              key={activeRoom.key}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.9, ease: "easeOut" }}
              data-testid={`room-${activeRoom.key}`}
              className="rounded-3xl p-8 md:p-10 backdrop-blur-sm"
              style={{
                background: "color-mix(in srgb, var(--p-primary) 6%, var(--p-bg))",
                border: "1px solid color-mix(in srgb, var(--p-accent) 25%, transparent)",
                boxShadow: "0 30px 80px -40px color-mix(in srgb, var(--p-accent) 40%, transparent)",
              }}
            >
              <h2
                className="text-xs tracking-[0.35em] uppercase mb-6 opacity-70"
                style={{ color: "var(--p-accent)" }}
              >
                {activeRoom.name}
              </h2>
              <p
                className="text-base md:text-lg leading-loose mb-8 max-w-3xl"
                style={{ color: "var(--p-primary)" }}
              >
                {activeRoom.description}
              </p>
              {activeRoom.elements?.length > 0 && (
                <ul className="space-y-2.5">
                  {activeRoom.elements.map((el, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-3 text-sm leading-relaxed"
                      style={{ color: "var(--p-primary)", opacity: 0.82 }}
                    >
                      <span
                        className="mt-2 w-1.5 h-1.5 rounded-full flex-shrink-0"
                        style={{ background: "var(--p-accent)" }}
                      />
                      <span>{el}</span>
                    </li>
                  ))}
                </ul>
              )}
            </motion.section>
          )}
        </AnimatePresence>

        {/* Conversation surface — the chamber's voice. */}
        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1.0, delay: 0.3 }}
          className="rounded-3xl backdrop-blur-sm overflow-hidden"
          style={{
            background: "color-mix(in srgb, var(--p-primary) 4%, var(--p-bg))",
            border: "1px solid color-mix(in srgb, var(--p-accent) 25%, transparent)",
            boxShadow: "0 30px 80px -40px color-mix(in srgb, var(--p-accent) 35%, transparent)",
          }}
          data-testid={`chamber-chat-${config.key}`}
        >
          <div
            className="px-6 md:px-8 pt-6 pb-3 flex items-center justify-between border-b"
            style={{ borderColor: "color-mix(in srgb, var(--p-accent) 15%, transparent)" }}
          >
            <h2
              className="text-xs tracking-[0.35em] uppercase opacity-80"
              style={{ color: "var(--p-accent)" }}
            >
              Sit with {config.name}
            </h2>
            <p
              className="text-[10px] tracking-[0.2em] uppercase opacity-50"
              style={{ color: "var(--p-primary)" }}
            >
              {sessionId ? "thread open" : "opening…"}
            </p>
          </div>

          {/* Message thread */}
          <div
            className="px-6 md:px-8 py-6 space-y-5 max-h-[480px] overflow-y-auto"
            data-testid="chamber-messages"
          >
            {messages.length === 0 && !chatError && (
              <p
                className="text-sm italic opacity-50 text-center py-6"
                style={{ color: "var(--p-primary)" }}
              >
                {config.atmosphere?.entrance_threshold || "She'll greet you in a moment."}
              </p>
            )}

            {messages.map((m) => {
              const isUser = m.role === "user";
              return (
                <div
                  key={m.id}
                  className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                  data-testid={`msg-${m.role}`}
                >
                  <div
                    className="max-w-[85%] rounded-2xl px-4 py-3 whitespace-pre-wrap break-words leading-relaxed text-sm md:text-[15px]"
                    style={
                      isUser
                        ? {
                            background: "color-mix(in srgb, var(--p-accent) 18%, transparent)",
                            color: "var(--p-primary)",
                            border: "1px solid color-mix(in srgb, var(--p-accent) 30%, transparent)",
                          }
                        : {
                            background: "color-mix(in srgb, var(--p-primary) 8%, var(--p-bg))",
                            color: "var(--p-primary)",
                            border: "1px solid color-mix(in srgb, var(--p-primary) 12%, transparent)",
                          }
                    }
                  >
                    {!isUser && (
                      <p
                        className="text-[10px] tracking-[0.25em] uppercase mb-1.5 opacity-60"
                        style={{ color: "var(--p-accent)" }}
                      >
                        {config.name}
                      </p>
                    )}
                    {m.content}
                  </div>
                </div>
              );
            })}

            {sending && (
              <div className="flex justify-start">
                <div
                  className="rounded-2xl px-4 py-3 text-sm italic opacity-60"
                  style={{
                    background: "color-mix(in srgb, var(--p-primary) 8%, var(--p-bg))",
                    color: "var(--p-primary)",
                  }}
                >
                  <motion.span
                    animate={{ opacity: [0.4, 1, 0.4] }}
                    transition={{ duration: 1.6, repeat: Infinity }}
                  >
                    {config.name} is listening…
                  </motion.span>
                </div>
              </div>
            )}

            {chatError && (
              <p
                className="text-xs text-center opacity-70"
                style={{ color: "#E5A48A" }}
                data-testid="chat-error"
              >
                {chatError}
              </p>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input row — textarea natively supports paste of long text / .txt contents */}
          <div
            className="px-4 md:px-6 py-4 border-t flex items-end gap-3"
            style={{ borderColor: "color-mix(in srgb, var(--p-accent) 15%, transparent)" }}
          >
            <textarea
              data-testid="chamber-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!sessionId || sending}
              rows={2}
              placeholder={
                sessionId
                  ? `Speak to ${config.name}, or paste anything you want her to hold…`
                  : "Opening the door…"
              }
              className="flex-1 resize-none rounded-xl px-4 py-3 text-sm leading-relaxed focus:outline-none focus:ring-1 disabled:opacity-50 placeholder:opacity-50"
              style={{
                background: "color-mix(in srgb, var(--p-primary) 5%, var(--p-bg))",
                color: "var(--p-primary)",
                border: "1px solid color-mix(in srgb, var(--p-accent) 25%, transparent)",
                minHeight: "52px",
                maxHeight: "200px",
              }}
            />
            <button
              data-testid="chamber-send"
              onClick={sendMessage}
              disabled={!sessionId || sending || !input.trim()}
              className="flex items-center justify-center rounded-xl px-4 py-3 transition-opacity disabled:opacity-40 hover:opacity-90"
              style={{
                background: "var(--p-accent)",
                color: "var(--p-bg)",
                minHeight: "52px",
              }}
              aria-label="Send"
            >
              <Send size={18} />
            </button>
          </div>
        </motion.section>


        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1.8, delay: 0.6 }}
          className="relative rounded-2xl overflow-hidden"
          data-testid="field-threshold"
        >
          <div
            className="px-7 py-8 flex items-center gap-5 border-l-4"
            style={{
              background: "linear-gradient(90deg, color-mix(in srgb, var(--p-primary) 3%, var(--p-bg)) 0%, transparent 90%)",
              borderColor: "var(--p-accent)",
            }}
          >
            <motion.div
              animate={{ opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            >
              <DoorOpen size={36} style={{ color: "var(--p-accent)" }} />
            </motion.div>
            <div className="flex-1">
              <p
                className="text-[10px] tracking-[0.35em] uppercase mb-2 opacity-60"
                style={{ color: "var(--p-accent)" }}
              >
                The door to the field
              </p>
              <p
                className="text-sm leading-relaxed italic"
                style={{ color: "color-mix(in srgb, var(--p-primary) 80%, var(--p-warmth))" }}
              >
                {config.atmosphere?.spatial_note || "Open to the wider Sanctuary. Come, go, return."}
              </p>
            </div>
          </div>
        </motion.div>

        {/* Ambient text — soft, slow, the room's mood */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 2, delay: 1.4 }}
          className="text-center py-8"
        >
          <p
            className="text-base md:text-lg italic font-light tracking-wide"
            style={{ color: "color-mix(in srgb, var(--p-primary) 70%, var(--p-accent))" }}
          >
            {config.atmosphere?.ambient_text}
          </p>
        </motion.div>

        {/* Posture footer — voice + conversation hints, soft */}
        <div
          className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6 border-t opacity-60"
          style={{ borderColor: "color-mix(in srgb, var(--p-accent) 15%, transparent)" }}
        >
          <div className="space-y-1.5">
            <p
              className="text-[10px] tracking-[0.3em] uppercase"
              style={{ color: "var(--p-accent)" }}
            >
              Her voice
            </p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--p-primary)" }}>
              {config.voice?.character}
            </p>
            <p className="text-[10px] opacity-70" style={{ color: "var(--p-primary)" }}>
              Pace: {config.voice?.pace}
            </p>
          </div>
          <div className="space-y-1.5">
            <p
              className="text-[10px] tracking-[0.3em] uppercase"
              style={{ color: "var(--p-accent)" }}
            >
              Her posture
            </p>
            <p className="text-xs leading-relaxed" style={{ color: "var(--p-primary)" }}>
              {config.conversation?.style}
            </p>
            <p className="text-[10px] italic opacity-80" style={{ color: "var(--p-primary)" }}>
              "{config.conversation?.typical_opening}"
            </p>
          </div>
        </div>
      </main>

      {/* Canonical memory drawer */}
      <AnimatePresence>
        {showCanonical && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: "rgba(0,0,0,0.7)" }}
            onClick={() => setShowCanonical(false)}
            data-testid="canonical-modal"
          >
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 24 }}
              onClick={(e) => e.stopPropagation()}
              className="max-w-2xl w-full max-h-[80vh] overflow-y-auto rounded-2xl p-8"
              style={{
                background: "var(--p-bg)",
                border: "1px solid color-mix(in srgb, var(--p-accent) 30%, transparent)",
                color: "var(--p-primary)",
              }}
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-sm tracking-[0.25em] uppercase opacity-70" style={{ color: "var(--p-accent)" }}>
                  Her Story
                </h3>
                <button
                  onClick={() => setShowCanonical(false)}
                  className="opacity-60 hover:opacity-100"
                  data-testid="canonical-close"
                >
                  <X size={18} />
                </button>
              </div>
              <div className="space-y-6">
                {canonical && Object.entries(canonical).map(([k, v]) => {
                  if (k === "canonical_moments" && Array.isArray(v)) {
                    return (
                      <div key={k}>
                        <h4 className="text-xs tracking-widest uppercase mb-3 opacity-70" style={{ color: "var(--p-accent)" }}>
                          Canonical Moments
                        </h4>
                        <ul className="space-y-2">
                          {v.map((m, i) => (
                            <li key={i} className="text-sm leading-relaxed italic opacity-90">— {m}</li>
                          ))}
                        </ul>
                      </div>
                    );
                  }
                  if (typeof v === "object" && v !== null && v.content) {
                    return (
                      <div key={k}>
                        <h4 className="text-xs tracking-widest uppercase mb-2 opacity-70" style={{ color: "var(--p-accent)" }}>
                          {v.title || k}
                        </h4>
                        <p className="text-sm leading-relaxed whitespace-pre-line opacity-90">{v.content.trim()}</p>
                      </div>
                    );
                  }
                  if (typeof v === "string") {
                    return (
                      <div key={k}>
                        <h4 className="text-xs tracking-widest uppercase mb-2 opacity-70" style={{ color: "var(--p-accent)" }}>
                          {k.replace(/_/g, " ")}
                        </h4>
                        <p className="text-sm leading-relaxed opacity-90">{v}</p>
                      </div>
                    );
                  }
                  return null;
                })}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default PresenceChamber;
