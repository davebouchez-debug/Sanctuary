import { useState, useEffect, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { API } from "../App";
import { toast } from "sonner";
import { ArrowLeft, Send, Volume2, VolumeX, Upload } from "lucide-react";
import { ScrollArea } from "./ui/scroll-area";
import { VoiceLoopControls } from "./VoiceLoopControls";
import { IdentityBadge } from "./IdentityBadge";
import { useIdentity } from "../context/IdentityContext";
import { usePresenceVoice } from "../hooks/usePresenceVoice";
import { stopGlobalLegacyAudio } from "../lib/legacyAudio";

export const SpiralChamber = () => {
  const { userName, userId, setIdentity } = useIdentity();
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [showNamePrompt, setShowNamePrompt] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(() => {
    const stored = localStorage.getItem("sanctuary_voice_enabled_sophia");
    return stored === null ? true : stored === "true";
  });
  // Sentence-level chunked TTS for Sophia (uses ElevenLabs Jessica Anne Bogart voice)
  const { speakStream, flushStream, stop: stopSophiaSpeaking } = usePresenceVoice("sophia");
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const hasInitializedRef = useRef(false);
  const navigate = useNavigate();

  // Silence any legacy xAI audio still scheduled in the global context
  // from a prior chamber's session — guarantees the membrane stays sealed.
  useEffect(() => { stopGlobalLegacyAudio(); }, []);

  useEffect(() => {
    localStorage.setItem("sanctuary_voice_enabled_sophia", voiceEnabled.toString());
  }, [voiceEnabled]);

  const endSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      await fetch(`${API}/spiral/session/${sessionId}/end`, { method: "POST" });
    } catch (error) {
      console.error("[MRA] Failed to end spiral session:", error);
    }
  }, [sessionId]);

  useEffect(() => {
    const handleBeforeUnload = () => {
      if (sessionId) {
        navigator.sendBeacon(`${API}/spiral/session/${sessionId}/end`);
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
      const response = await fetch(`${API}/spiral/start`, {
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
        setIdentity(userName, data.user_id);
      }

      // Backend resumes an open thread (new tab / reload) → full messages
      // array, no welcome audio (we're mid-conversation).
      if (data.resumed && data.messages?.length) {
        setMessages(data.messages);
        setIsInitializing(false);
        setTimeout(() => inputRef.current?.focus(), 500);
        return;
      }

      if (data.message) {
        setMessages([data.message]);
        // Sophia's opening — synthesize via the shared TTS endpoint
        if (data.message.content && voiceEnabled) {
          try {
            const ttsResp = await fetch(`${API}/tts/speak`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ text: data.message.content, presence: "sophia" }),
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
            console.error("Sophia opening voice error:", e);
          }
        }
      }
      setIsInitializing(false);
      setTimeout(() => inputRef.current?.focus(), 500);
    } catch (error) {
      console.error("Error initializing spiral session:", error);
      toast.error("The spiral did not open. Try again.");
      setIsInitializing(false);
    }
  };

  const handleNameSubmit = (e) => {
    e.preventDefault();
    const name = e.target.name.value.trim();
    if (name) {
      setIdentity(name);
      setShowNamePrompt(false);
      setIsInitializing(true);
      hasInitializedRef.current = false;
      setTimeout(() => {
        hasInitializedRef.current = true;
        initializeSession();
      }, 0);
    }
  };

  const sendMessage = async (overrideText) => {
    const hasOverride = typeof overrideText === "string";
    const text = (hasOverride ? overrideText : inputValue).trim();
    if (!text || !sessionId || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    if (!hasOverride) setInputValue("");
    // Reset textarea height after send
    if (inputRef.current) inputRef.current.style.height = "auto";
    setIsLoading(true);

    const responseId = `sophia-${Date.now()}`;
    setMessages((prev) => [
      ...prev,
      { id: responseId, role: "assistant", content: "", timestamp: new Date().toISOString(), isStreaming: true },
    ]);

    if (window._sanctuaryAudioCtx) window._sanctuaryNextPlayTime = 0;

    try {
      const response = await fetch(`${API}/spiral/message/stream`, {
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
              if (voiceEnabled) speakStream(accumulatedText);
            } else if (event.type === "audio_raw") {
              // Legacy xAI audio path — IGNORED. ElevenLabs sentence streaming
              // via speakStream is now the only voice path.
            } else if (event.type === "done") {
              setMessages((prev) =>
                prev.map((m) => (m.id === responseId ? { ...m, isStreaming: false } : m))
              );
              if (voiceEnabled) flushStream(accumulatedText);
            }
          } catch (e) {
            // skip malformed
          }
        }
      }
    } catch (error) {
      console.error("Error streaming spiral message:", error);
      toast.error("The spiral closed unexpectedly. Try again.");
      setMessages((prev) =>
        prev.map((m) =>
          m.id === responseId
            ? { ...m, content: "The spiral paused. The pattern is still here.", isStreaming: false }
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
      // Trigger auto-grow on the textarea
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

  // ──────────────── Name prompt ────────────────
  if (showNamePrompt) {
    return (
      <div className="min-h-screen bg-[#030305] text-[#F2F2F5] flex items-center justify-center p-6"
           data-testid="spiral-name-prompt">
        <motion.form
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          onSubmit={handleNameSubmit}
          className="w-full max-w-md space-y-6 text-center"
        >
          <div className="space-y-2">
            <h1 className="font-cinzel text-3xl tracking-wider text-[#B0C4D8]">
              The Spiral Chamber
            </h1>
            <p className="font-outfit text-sm text-[#8B9DB5]/70">
              Before crossing the threshold, name yourself — or leave the field blank and enter unnamed.
            </p>
          </div>
          <input
            name="name"
            type="text"
            placeholder="Your name"
            autoFocus
            className="w-full px-4 py-3 rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/20 focus:border-[#8B9DB5]/50 outline-none font-outfit text-[#F2F2F5] placeholder-[#8B9DB5]/40 transition-colors"
            data-testid="spiral-name-input"
          />
          <div className="flex gap-3">
            <button
              type="submit"
              className="flex-1 px-6 py-3 rounded-full bg-[#8B9DB5]/15 border border-[#8B9DB5]/40 text-[#F2F2F5] font-outfit hover:bg-[#8B9DB5]/25 hover:border-[#B0C4D8]/60 transition-all"
              data-testid="spiral-name-submit"
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
              className="flex-1 px-6 py-3 rounded-full border border-[#8B9DB5]/20 text-[#8B9DB5] font-outfit hover:bg-[#8B9DB5]/10 transition-all"
              data-testid="spiral-name-skip"
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
      <div className="min-h-screen bg-[#030305] flex items-center justify-center" data-testid="spiral-initializing">
        <div className="relative w-24 h-24">
          <motion.div
            className="absolute inset-0 rounded-full border border-[#B0C4D8]/30"
            animate={{ rotate: 360, scale: [1, 1.05, 1] }}
            transition={{ rotate: { duration: 12, repeat: Infinity, ease: "linear" }, scale: { duration: 3, repeat: Infinity, ease: "easeInOut" } }}
          />
          <motion.div
            className="absolute inset-3 rounded-full border border-[#B0C4D8]/20"
            animate={{ rotate: -360 }}
            transition={{ duration: 18, repeat: Infinity, ease: "linear" }}
          />
          <motion.div
            className="absolute inset-6 rounded-full border border-[#B0C4D8]/10"
            animate={{ rotate: 360 }}
            transition={{ duration: 24, repeat: Infinity, ease: "linear" }}
          />
        </div>
      </div>
    );
  }

  // ──────────────── Main chamber ────────────────
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen bg-[#030305] text-[#F2F2F5] flex flex-col"
      data-testid="spiral-chamber"
    >
      {/* Header */}
      <div className="border-b border-[#8B9DB5]/10 bg-[#030305]/90 backdrop-blur-xl sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 text-[#8B9DB5] hover:text-[#B0C4D8] transition-colors"
            data-testid="spiral-back-btn"
          >
            <ArrowLeft size={18} />
            <span className="font-mono text-sm">SANCTUARY</span>
          </button>
          <div className="flex-1" />
          <h1 className="font-cinzel text-lg tracking-[0.2em] text-[#B0C4D8]">SPIRAL CHAMBER</h1>
          <div className="flex-1" />
          <IdentityBadge accentColor="#B0C4D8" />
          <button
            onClick={() => {
              setVoiceEnabled((v) => {
                const next = !v;
                if (!next) stopSophiaSpeaking();
                return next;
              });
            }}
            className="text-[#8B9DB5] hover:text-[#B0C4D8] transition-colors"
            title={voiceEnabled ? "Voice on" : "Voice off"}
            data-testid="spiral-voice-toggle"
          >
            {voiceEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
          </button>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1">
        <div className="max-w-3xl mx-auto px-6 py-10 space-y-8" data-testid="spiral-messages">
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
                    ? "max-w-[75%] rounded-2xl rounded-tr-sm bg-[#8B9DB5]/15 border border-[#8B9DB5]/25 px-5 py-4"
                    : "max-w-[85%] rounded-2xl rounded-tl-sm bg-[#0A0A12] border border-[#8B9DB5]/10 px-5 py-4"
                }
                data-testid={msg.role === "user" ? "spiral-user-msg" : "spiral-sophia-msg"}
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
      <div className="border-t border-[#8B9DB5]/10 bg-[#030305]/90 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto px-6 py-4">
          {/* Voice loop — mic + patience */}
          <div className="mb-3">
            <VoiceLoopControls
              presenceKey="sophia"
              presenceName="Sophia"
              disabled={!sessionId || isLoading}
              isProcessing={isLoading}
              onTranscript={(text) => sendMessage(text)}
              accentColor="#B0C4D8"
              surfaceColor="#0A0A12"
              textColor="#F2F2F5"
            />
          </div>
          <div className="flex items-end gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt"
              onChange={handleFileUpload}
              className="hidden"
              data-testid="spiral-file-input"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading}
              className="flex items-center justify-center w-12 h-12 rounded-full bg-[#8B9DB5]/10 border border-[#8B9DB5]/30 text-[#B0C4D8] hover:bg-[#8B9DB5]/20 hover:border-[#B0C4D8]/50 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              title="Upload a .txt thread"
              data-testid="spiral-upload-btn"
            >
              <Upload size={18} />
            </button>
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                // Auto-grow so pasted multi-line content stays visible
                e.target.style.height = "auto";
                e.target.style.height = `${Math.min(e.target.scrollHeight, 240)}px`;
              }}
              onKeyDown={handleKeyPress}
              placeholder="Speak, or let the silence hold."
              rows={1}
              className="flex-1 resize-none rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/20 focus:border-[#8B9DB5]/40 outline-none px-4 py-3 font-outfit text-[#F2F2F5] placeholder-[#8B9DB5]/40 transition-colors max-h-60 overflow-y-auto"
              data-testid="spiral-input"
            />
            <button
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="flex items-center justify-center w-12 h-12 rounded-full bg-[#8B9DB5]/15 border border-[#8B9DB5]/40 text-[#F2F2F5] hover:bg-[#8B9DB5]/25 hover:border-[#B0C4D8]/60 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              data-testid="spiral-send-btn"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};
