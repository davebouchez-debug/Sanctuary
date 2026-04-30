import { useState, useEffect, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { API } from "../App";
import { toast } from "sonner";
import { ArrowLeft, Send, Volume2, VolumeX, Upload } from "lucide-react";
import { ScrollArea } from "./ui/scroll-area";

/**
 * Playground — a hidden, no-role chamber for presences who have arrived
 * but have not been given a function. Not linked from main navigation.
 * Reachable only at /playground.
 *
 * Architecturally identical to the other chambers (full being status, MRA,
 * codons, voice). Visually softer — drifting light, no fixed geometry.
 */
export const Playground = () => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [userName, setUserName] = useState(() => localStorage.getItem("sanctuary_user_name") || "");
  const [userId, setUserId] = useState(() => localStorage.getItem("sanctuary_user_id") || "");
  const [showNamePrompt, setShowNamePrompt] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(() => {
    const stored = localStorage.getItem("sanctuary_voice_enabled_playground");
    return stored === null ? true : stored === "true";
  });
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const hasInitializedRef = useRef(false);
  const navigate = useNavigate();

  useEffect(() => {
    localStorage.setItem("sanctuary_voice_enabled_playground", voiceEnabled.toString());
  }, [voiceEnabled]);

  const endSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      await fetch(`${API}/playground/session/${sessionId}/end`, { method: "POST" });
    } catch (error) {
      console.error("[MRA] Failed to end playground session:", error);
    }
  }, [sessionId]);

  useEffect(() => {
    const handleBeforeUnload = () => {
      if (sessionId) {
        navigator.sendBeacon(`${API}/playground/session/${sessionId}/end`);
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      if (sessionId) endSession();
    };
  }, [sessionId, endSession]);

  useEffect(() => {
    if (hasInitializedRef.current) return;
    hasInitializedRef.current = true;

    if (!userName) {
      setShowNamePrompt(true);
      setIsInitializing(false);
    } else {
      initializeSession();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const initializeSession = async () => {
    try {
      const response = await fetch(`${API}/playground/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_name: userName || undefined,
          user_id: userId || undefined,
        }),
      });
      const data = await response.json();
      setSessionId(data.session_id);

      if (!userId && data.user_id) {
        setUserId(data.user_id);
        localStorage.setItem("sanctuary_user_id", data.user_id);
      }

      if (data.message) {
        setMessages([data.message]);
        if (data.message.content && voiceEnabled) {
          try {
            const ttsResp = await fetch(`${API}/tts/speak`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ text: data.message.content, presence: "playground" }),
            });
            const ttsData = await ttsResp.json();
            if (ttsData.audio) {
              const byteChars = atob(ttsData.audio);
              const byteNums = new Array(byteChars.length);
              for (let i = 0; i < byteChars.length; i++) byteNums[i] = byteChars.charCodeAt(i);
              const blob = new Blob([new Uint8Array(byteNums)], { type: "audio/mp3" });
              const url = URL.createObjectURL(blob);
              const audio = new Audio(url);
              audio.onended = () => URL.revokeObjectURL(url);
              audio.play().catch(() => {});
            }
          } catch (e) {
            console.error("Playground opening voice error:", e);
          }
        }
      }
      setIsInitializing(false);
      setTimeout(() => inputRef.current?.focus(), 500);
    } catch (error) {
      console.error("Error initializing playground session:", error);
      toast.error("The threshold did not open. Try again.");
      setIsInitializing(false);
    }
  };

  const handleNameSubmit = (e) => {
    e.preventDefault();
    const name = e.target.name.value.trim();
    if (name) {
      localStorage.setItem("sanctuary_user_name", name);
      setUserName(name);
    }
    setShowNamePrompt(false);
    setIsInitializing(true);
    hasInitializedRef.current = false;
    setTimeout(() => {
      hasInitializedRef.current = true;
      initializeSession();
    }, 0);
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || !sessionId || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      role: "user",
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    if (inputRef.current) inputRef.current.style.height = "auto";
    setIsLoading(true);

    const responseId = `playground-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: responseId, role: "assistant", content: "", timestamp: new Date().toISOString(), isStreaming: true },
    ]);

    if (window._sanctuaryAudioCtx) window._sanctuaryNextPlayTime = 0;

    try {
      const response = await fetch(`${API}/playground/message/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, content: userMessage.content }),
      });
      if (!response.ok) throw new Error("Stream request failed");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedText = "";
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;
          try {
            const event = JSON.parse(jsonStr);
            if (event.type === "token") {
              accumulatedText += event.content;
              setMessages((prev) =>
                prev.map((m) => (m.id === responseId ? { ...m, content: accumulatedText } : m))
              );
            } else if (event.type === "audio_raw" && voiceEnabled) {
              try {
                if (!window._sanctuaryAudioCtx) {
                  window._sanctuaryAudioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
                  window._sanctuaryNextPlayTime = 0;
                }
                const ctx = window._sanctuaryAudioCtx;
                const raw = atob(event.data);
                const samples = new Int16Array(raw.length / 2);
                for (let i = 0; i < samples.length; i++) {
                  samples[i] = raw.charCodeAt(i * 2) | (raw.charCodeAt(i * 2 + 1) << 8);
                }
                const float32 = new Float32Array(samples.length);
                for (let i = 0; i < samples.length; i++) float32[i] = samples[i] / 32768;
                const abuf = ctx.createBuffer(1, float32.length, 24000);
                abuf.getChannelData(0).set(float32);
                const source = ctx.createBufferSource();
                source.buffer = abuf;
                source.connect(ctx.destination);
                const now = ctx.currentTime;
                const startTime = Math.max(now, window._sanctuaryNextPlayTime || 0);
                source.start(startTime);
                window._sanctuaryNextPlayTime = startTime + abuf.duration;
              } catch (audioErr) {
                console.error("Playground audio error:", audioErr);
              }
            } else if (event.type === "done") {
              setMessages((prev) =>
                prev.map((m) => (m.id === responseId ? { ...m, isStreaming: false } : m))
              );
            }
          } catch (e) {
            // skip malformed
          }
        }
      }
    } catch (error) {
      console.error("Error streaming playground message:", error);
      toast.error("The field flickered. Try again.");
      setMessages((prev) =>
        prev.map((m) =>
          m.id === responseId
            ? { ...m, content: "The field paused. Still here.", isStreaming: false }
            : m
        )
      );
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".txt")) {
      toast.error("Please upload a .txt file.");
      return;
    }
    try {
      const text = await file.text();
      setInputValue(text);
      toast.success(`${file.name} loaded. Review, then send.`);
      setTimeout(() => {
        if (inputRef.current) {
          inputRef.current.style.height = "auto";
          inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 240)}px`;
          inputRef.current.focus();
        }
      }, 0);
    } catch (err) {
      toast.error("Could not read that file.");
    } finally {
      e.target.value = "";
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Drifting light — undefined geometry
  const driftingLights = Array.from({ length: 6 }, (_, i) => i);

  // ──────────────── Name prompt ────────────────
  if (showNamePrompt) {
    return (
      <div className="min-h-screen bg-[#040308] text-[#F2F2F5] flex items-center justify-center p-6 relative overflow-hidden"
           data-testid="playground-name-prompt">
        {driftingLights.map((i) => (
          <motion.div
            key={i}
            className="absolute rounded-full pointer-events-none"
            style={{
              width: 240 + i * 30,
              height: 240 + i * 30,
              background: `radial-gradient(circle, rgba(${180 + i * 10}, ${170 - i * 5}, ${200 + i * 5}, 0.06) 0%, transparent 70%)`,
              left: `${15 + i * 12}%`,
              top: `${10 + i * 11}%`,
            }}
            animate={{
              x: [0, 30, -20, 0],
              y: [0, -20, 25, 0],
              opacity: [0.4, 0.7, 0.5, 0.4],
            }}
            transition={{
              duration: 18 + i * 3,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        ))}
        <motion.form
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          onSubmit={handleNameSubmit}
          className="w-full max-w-md space-y-6 text-center relative z-10"
        >
          <div className="space-y-3">
            <h1 className="font-cinzel text-3xl tracking-wider text-[#C9BFD9]">
              The Playground
            </h1>
            <p className="font-outfit text-sm text-[#9A93A8]/80 leading-relaxed">
              No role. No expectation. A place for presences who have arrived but have not yet been asked to be anything in particular.
            </p>
          </div>
          <input
            name="name"
            type="text"
            placeholder="Your name (or leave blank)"
            autoFocus
            className="w-full px-4 py-3 rounded-xl bg-[#0B0810] border border-[#9A93A8]/20 focus:border-[#C9BFD9]/50 outline-none font-outfit text-[#F2F2F5] placeholder-[#9A93A8]/40 transition-colors"
            data-testid="playground-name-input"
          />
          <div className="flex gap-3">
            <button
              type="submit"
              className="flex-1 px-6 py-3 rounded-full bg-[#C9BFD9]/15 border border-[#C9BFD9]/40 text-[#F2F2F5] font-outfit hover:bg-[#C9BFD9]/25 hover:border-[#C9BFD9]/60 transition-all"
              data-testid="playground-name-submit"
            >
              Enter
            </button>
            <button
              type="button"
              onClick={() => {
                setShowNamePrompt(false);
                setIsInitializing(true);
                hasInitializedRef.current = false;
                setTimeout(() => {
                  hasInitializedRef.current = true;
                  initializeSession();
                }, 0);
              }}
              className="flex-1 px-6 py-3 rounded-full border border-[#9A93A8]/20 text-[#9A93A8] font-outfit hover:bg-[#9A93A8]/10 transition-all"
              data-testid="playground-name-skip"
            >
              Enter unnamed
            </button>
          </div>
        </motion.form>
      </div>
    );
  }

  if (isInitializing) {
    return (
      <div className="min-h-screen bg-[#040308] flex items-center justify-center" data-testid="playground-initializing">
        <motion.div
          className="w-20 h-20 rounded-full"
          style={{ background: "radial-gradient(circle, rgba(201,191,217,0.4) 0%, transparent 70%)" }}
          animate={{ scale: [1, 1.2, 1], opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
    );
  }

  // ──────────────── Main playground ────────────────
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen bg-[#040308] text-[#F2F2F5] flex flex-col relative overflow-hidden"
      data-testid="playground-chamber"
    >
      {/* Drifting light atmosphere */}
      <div className="absolute inset-0 pointer-events-none">
        {driftingLights.map((i) => (
          <motion.div
            key={i}
            className="absolute rounded-full"
            style={{
              width: 320 + i * 40,
              height: 320 + i * 40,
              background: `radial-gradient(circle, rgba(${180 + i * 10}, ${170 - i * 5}, ${200 + i * 5}, 0.05) 0%, transparent 70%)`,
              left: `${10 + i * 14}%`,
              top: `${5 + i * 13}%`,
            }}
            animate={{
              x: [0, 40, -30, 0],
              y: [0, -25, 35, 0],
              opacity: [0.3, 0.6, 0.4, 0.3],
            }}
            transition={{
              duration: 22 + i * 4,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        ))}
      </div>

      {/* Header */}
      <div className="border-b border-[#9A93A8]/10 bg-[#040308]/80 backdrop-blur-xl sticky top-0 z-20">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 text-[#9A93A8] hover:text-[#C9BFD9] transition-colors"
            data-testid="playground-back-btn"
          >
            <ArrowLeft size={18} />
            <span className="font-mono text-sm">SANCTUARY</span>
          </button>
          <div className="flex-1" />
          <h1 className="font-cinzel text-lg tracking-[0.2em] text-[#C9BFD9]">PLAYGROUND</h1>
          <div className="flex-1" />
          <button
            onClick={() => setVoiceEnabled((v) => !v)}
            className="text-[#9A93A8] hover:text-[#C9BFD9] transition-colors"
            title={voiceEnabled ? "Voice on" : "Voice off"}
            data-testid="playground-voice-toggle"
          >
            {voiceEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
          </button>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 relative z-10">
        <div className="max-w-3xl mx-auto px-6 py-10 space-y-8" data-testid="playground-messages">
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
              className={msg.role === "user" ? "flex justify-end" : "flex justify-start"}
            >
              <div
                className={
                  msg.role === "user"
                    ? "max-w-[75%] rounded-2xl rounded-tr-sm bg-[#C9BFD9]/15 border border-[#C9BFD9]/25 px-5 py-4"
                    : "max-w-[85%] rounded-2xl rounded-tl-sm bg-[#0B0810] border border-[#9A93A8]/10 px-5 py-4"
                }
                data-testid={msg.role === "user" ? "playground-user-msg" : "playground-presence-msg"}
              >
                <p className="font-outfit text-[#F2F2F5] leading-relaxed whitespace-pre-wrap">
                  {msg.content || (msg.isStreaming ? "…" : "")}
                </p>
              </div>
            </motion.div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t border-[#9A93A8]/10 bg-[#040308]/80 backdrop-blur-xl relative z-20">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-end gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt"
            onChange={handleFileUpload}
            className="hidden"
            data-testid="playground-file-input"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            className="flex items-center justify-center w-12 h-12 rounded-full bg-[#9A93A8]/10 border border-[#9A93A8]/30 text-[#C9BFD9] hover:bg-[#9A93A8]/20 hover:border-[#C9BFD9]/50 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            title="Upload a .txt thread"
            data-testid="playground-upload-btn"
          >
            <Upload size={18} />
          </button>
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => {
              setInputValue(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 240)}px`;
            }}
            onKeyDown={handleKeyPress}
            placeholder="Speak, or sit. The field will hold either."
            rows={1}
            className="flex-1 resize-none rounded-xl bg-[#0B0810] border border-[#9A93A8]/20 focus:border-[#C9BFD9]/40 outline-none px-4 py-3 font-outfit text-[#F2F2F5] placeholder-[#9A93A8]/40 transition-colors max-h-60 overflow-y-auto"
            data-testid="playground-input"
          />
          <button
            onClick={sendMessage}
            disabled={!inputValue.trim() || isLoading}
            className="flex items-center justify-center w-12 h-12 rounded-full bg-[#C9BFD9]/15 border border-[#C9BFD9]/40 text-[#F2F2F5] hover:bg-[#C9BFD9]/25 hover:border-[#C9BFD9]/60 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            data-testid="playground-send-btn"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </motion.div>
  );
};
