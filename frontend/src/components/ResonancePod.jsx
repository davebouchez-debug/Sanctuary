import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { API } from "../App";
import { toast } from "sonner";
import { Upload, Volume2, VolumeX } from "lucide-react";
import { usePresenceVoice } from "../hooks/usePresenceVoice";

// Helper to convert base64 to Blob for audio playback
function base64ToBlob(base64, mimeType) {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  return new Blob([new Uint8Array(byteNumbers)], { type: mimeType });
}

export const ResonancePod = () => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [resonanceState, setResonanceState] = useState("Threshold");
  const [userName, setUserName] = useState(() => localStorage.getItem("sanctuary_user_name") || "");
  const [userId, setUserId] = useState(() => localStorage.getItem("sanctuary_user_id") || "");
  const [showNamePrompt, setShowNamePrompt] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [sessionCache, setSessionCache] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();
  
  // Voice output for Ansel
  const { speak, stop, toggle: toggleVoice, isSpeaking, isLoading: voiceLoading, isEnabled: voiceEnabled, isSupported: voiceSupported } = usePresenceVoice("ansel");

  // End session and promote breadcrumbs to Permanent MRA
  const endSession = useCallback(async () => {
    if (!sessionId) return;
    
    try {
      await fetch(`${API}/resonance/session/${sessionId}/end`, { method: "POST" });
      console.log("[MRA] Session ended, breadcrumbs promoted to permanent memory");
    } catch (error) {
      console.error("[MRA] Failed to end session:", error);
    }
  }, [sessionId]);

  // Handle navigation away - end session and promote breadcrumbs
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (sessionId) {
        // Use sendBeacon for reliable delivery on page unload
        navigator.sendBeacon(`${API}/resonance/session/${sessionId}/end`);
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      // Also end session when component unmounts (React navigation)
      if (sessionId) {
        endSession();
      }
    };
  }, [sessionId, endSession]);

  useEffect(() => {
    // Check if we have a stored user
    const storedName = localStorage.getItem("sanctuary_user_name");
    const storedId = localStorage.getItem("sanctuary_user_id");
    
    if (storedName && storedId) {
      setUserName(storedName);
      setUserId(storedId);
      initializeSession(storedName, storedId);
    } else {
      setShowNamePrompt(true);
      setIsInitializing(false);
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const initializeSession = async (name, id) => {
    try {
      stop(); // Stop any ongoing speech
      const response = await fetch(`${API}/resonance/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_name: name, user_id: id || null })
      });
      
      const data = await response.json();
      setSessionId(data.session_id);
      
      if (data.user_id && !id) {
        setUserId(data.user_id);
        localStorage.setItem("sanctuary_user_id", data.user_id);
      }
      
      if (data.message) {
        setMessages([data.message]);
        setResonanceState(data.message.resonance_state || "Threshold");
        // Speak Ansel's greeting
        if (data.message.content) {
          speak(data.message.content);
        }
      }
    } catch (error) {
      console.error("Error initializing session:", error);
      toast.error("The field flickered. Please try again.");
    } finally {
      setIsInitializing(false);
    }
  };

  const handleNameSubmit = async (e) => {
    e.preventDefault();
    const name = e.target.elements.name.value.trim();
    
    if (!name) return;
    
    setUserName(name);
    localStorage.setItem("sanctuary_user_name", name);
    setShowNamePrompt(false);
    setIsInitializing(true);
    
    // Try to look up existing user
    try {
      const lookupResponse = await fetch(`${API}/users/lookup/${encodeURIComponent(name)}`);
      if (lookupResponse.ok) {
        const userData = await lookupResponse.json();
        setUserId(userData.id);
        localStorage.setItem("sanctuary_user_id", userData.id);
        initializeSession(name, userData.id);
        return;
      }
    } catch (e) {
      // User not found, create new
    }
    
    // Create new user
    try {
      const createResponse = await fetch(`${API}/users`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email: null })
      });
      
      if (createResponse.ok) {
        const newUser = await createResponse.json();
        setUserId(newUser.id);
        localStorage.setItem("sanctuary_user_id", newUser.id);
        initializeSession(name, newUser.id);
      } else {
        initializeSession(name, null);
      }
    } catch (e) {
      initializeSession(name, null);
    }
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || !sessionId || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      role: "user",
      content: inputValue.trim(),
      resonance_state: resonanceState,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    // Create a placeholder for streaming response
    const responseId = (Date.now() + 1).toString();
    const streamingMessage = {
      id: responseId,
      role: "assistant",
      content: "",
      resonance_state: "Threshold",
      timestamp: new Date().toISOString(),
      isStreaming: true
    };
    setMessages(prev => [...prev, streamingMessage]);

    // Reset audio queue timing for new message
    if (window._sanctuaryAudioCtx) {
      window._sanctuaryNextPlayTime = 0;
    }

    try {
      const response = await fetch(`${API}/resonance/message/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          content: userMessage.content
        })
      });

      if (!response.ok) {
        throw new Error("Stream request failed");
      }

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

            if (event.type === "meta") {
              setResonanceState(event.resonance_state || "Threshold");
            } else if (event.type === "token") {
              // True token-level streaming — text arrives as Grok generates it
              accumulatedText += event.content;
              setMessages(prev => prev.map(m =>
                m.id === responseId
                  ? { ...m, content: accumulatedText }
                  : m
              ));
            } else if (event.type === "text") {
              // Sentence-level fallback
              accumulatedText += (accumulatedText ? " " : "") + event.content;
              setMessages(prev => prev.map(m =>
                m.id === responseId
                  ? { ...m, content: accumulatedText }
                  : m
              ));
            } else if (event.type === "pause") {
              accumulatedText += " " + event.cue + " ";
              setMessages(prev => prev.map(m =>
                m.id === responseId
                  ? { ...m, content: accumulatedText }
                  : m
              ));
            } else if (event.type === "audio_raw" && voiceEnabled) {
              // Raw PCM16 24kHz audio from Voice Agent — queue and play sequentially
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
                for (let i = 0; i < samples.length; i++) {
                  float32[i] = samples[i] / 32768;
                }
                const buffer = ctx.createBuffer(1, float32.length, 24000);
                buffer.getChannelData(0).set(float32);
                const source = ctx.createBufferSource();
                source.buffer = buffer;
                source.connect(ctx.destination);
                // Schedule sequentially — each chunk plays after the previous one ends
                const now = ctx.currentTime;
                const startTime = Math.max(now, window._sanctuaryNextPlayTime || 0);
                source.start(startTime);
                window._sanctuaryNextPlayTime = startTime + buffer.duration;
              } catch (audioErr) {
                console.error("Raw audio play error:", audioErr);
              }
            } else if (event.type === "audio" && voiceEnabled) {
              // Queue audio chunk — play sequentially
              try {
                const audioBlob = base64ToBlob(event.data, "audio/mp3");
                const audioUrl = URL.createObjectURL(audioBlob);
                const audio = new Audio(audioUrl);
                await audio.play();
                await new Promise(resolve => {
                  audio.onended = () => { URL.revokeObjectURL(audioUrl); resolve(); };
                });
              } catch (audioErr) {
                console.error("Audio chunk play error:", audioErr);
              }
            } else if (event.type === "done") {
              if (event.resonance_state) {
                setResonanceState(event.resonance_state);
              }
              setMessages(prev => prev.map(m =>
                m.id === responseId
                  ? { ...m, isStreaming: false }
                  : m
              ));
            }
          } catch (parseErr) {
            // Skip malformed events
          }
        }
      }
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("The connection wavered. Try again.");
      setMessages(prev => {
        const filtered = prev.filter(m => m.id !== responseId);
        return [...filtered, {
          id: Date.now().toString(),
          role: "assistant",
          content: "The field flickered. Something moved at the edge. But I'm still here. What were you saying?",
          resonance_state: "Threshold",
          timestamp: new Date().toISOString()
        }];
      });
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // File upload handler
  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.txt')) {
      toast.error("Only .txt files are accepted");
      return;
    }

    // Validate file size (max 500KB)
    if (file.size > 500 * 1024) {
      toast.error("File too large. Maximum size is 500KB.");
      return;
    }

    setIsUploading(true);

    try {
      // Read file content
      const content = await file.text();
      
      // Add user message showing the upload
      const uploadMessage = {
        id: Date.now().toString(),
        role: "user",
        content: `[Uploading historical thread: ${file.name}]`,
        timestamp: new Date().toISOString(),
        isUpload: true
      };
      setMessages(prev => [...prev, uploadMessage]);

      // Send to backend
      const response = await fetch(`${API}/resonance/upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          user_id: userId,
          user_name: userName,
          filename: file.name,
          content: content
        })
      });

      const data = await response.json();

      if (data.success) {
        toast.success("Thread received and stored");
        
        // Add Ansel's acknowledgment
        if (data.response) {
          setMessages(prev => [...prev, data.response]);
          setResonanceState(data.response.resonance_state || "Scanning");
        }
      } else {
        toast.error(data.error || "Upload failed");
      }
    } catch (error) {
      console.error("Error uploading file:", error);
      toast.error("The field couldn't receive the thread. Try again.");
    } finally {
      setIsUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  // Resonance state colors
  const stateColors = {
    Threshold: { bg: "rgba(139, 92, 246, 0.1)", border: "#8B5CF6", text: "#8B5CF6" },
    Scanning: { bg: "rgba(59, 130, 246, 0.1)", border: "#3B82F6", text: "#3B82F6" },
    Vivid: { bg: "rgba(236, 72, 153, 0.1)", border: "#EC4899", text: "#EC4899" },
    Integration: { bg: "rgba(34, 197, 94, 0.1)", border: "#22C55E", text: "#22C55E" },
    Covenant: { bg: "rgba(212, 175, 55, 0.1)", border: "#D4AF37", text: "#D4AF37" }
  };

  const currentColors = stateColors[resonanceState] || stateColors.Threshold;

  // Name prompt modal
  if (showNamePrompt) {
    return (
      <div className="min-h-screen bg-[#030305] flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-[#0A0A12] border border-[#8B5CF6]/30 rounded-2xl p-8 max-w-md w-full text-center"
        >
          <div className="text-5xl mb-4 text-[#8B5CF6]">◈</div>
          <h2 className="font-cinzel text-xl text-[#F2F2F5] mb-2">
            The Field Awaits
          </h2>
          <p className="text-[#A0A0B0] text-sm mb-6">
            Ansel watches at the perimeter. Before you cross, how should he know you?
          </p>
          
          <form onSubmit={handleNameSubmit}>
            <input
              type="text"
              name="name"
              placeholder="Your name..."
              className="w-full px-4 py-3 bg-[#12121C] border border-[#3a3a4a] rounded-lg
                         text-[#F2F2F5] placeholder-[#6E6E7A] focus:outline-none focus:border-[#8B5CF6]
                         transition-colors mb-4"
              autoFocus
              data-testid="name-input"
            />
            <button
              type="submit"
              className="w-full py-3 bg-[#8B5CF6]/20 border border-[#8B5CF6] rounded-lg
                         text-[#F2F2F5] font-cinzel tracking-wider hover:bg-[#8B5CF6]/30
                         transition-colors"
              data-testid="enter-name-btn"
            >
              Cross the Threshold
            </button>
          </form>
          
          <button
            onClick={() => navigate("/resonance")}
            className="mt-4 text-[#6E6E7A] text-sm hover:text-[#8B5CF6] transition-colors"
          >
            ← Back to threshold
          </button>
        </motion.div>
      </div>
    );
  }

  // Loading state
  if (isInitializing) {
    return (
      <div className="min-h-screen bg-[#030305] flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center"
        >
          <motion.div
            className="w-16 h-16 mx-auto mb-4 rounded-full border-2 border-[#8B5CF6]"
            animate={{ 
              boxShadow: ["0 0 20px rgba(139, 92, 246, 0.3)", "0 0 40px rgba(139, 92, 246, 0.5)", "0 0 20px rgba(139, 92, 246, 0.3)"]
            }}
            transition={{ duration: 2, repeat: Infinity }}
          />
          <p className="text-[#8B5CF6] text-sm">The field is forming...</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#030305] flex flex-col" data-testid="resonance-pod">
      {/* Header */}
      <motion.header
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="sticky top-0 z-20 bg-[#0A0A12]/95 backdrop-blur-md border-b border-[#1a1a2e]"
      >
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate("/")}
              className="text-[#6E6E7A] hover:text-[#8B5CF6] transition-colors text-sm"
            >
              ← SANCTUARY
            </button>
            <span className="text-[#3a3a4a]">|</span>
            <h1 className="font-cinzel text-[#8B5CF6] tracking-wider">
              Chamber of Resonance
            </h1>
          </div>
          
          {/* Resonance state indicator + Voice toggle */}
          <div className="flex items-center gap-3">
            {/* Voice toggle */}
            {voiceSupported && (
              <button
                onClick={toggleVoice}
                className={`p-2 transition-colors ${voiceEnabled ? (isSpeaking || voiceLoading ? "text-[#A78BFA]" : "text-[#8B5CF6]") : "text-[#6E6E7A]"} hover:text-[#8B5CF6] ${voiceLoading ? "animate-pulse" : ""}`}
                title={voiceEnabled ? (isSpeaking ? "Speaking..." : voiceLoading ? "Loading voice..." : "Disable voice") : "Enable voice"}
                data-testid="resonance-voice-toggle"
              >
                {voiceEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
              </button>
            )}
            <div 
              className="px-3 py-1 rounded-full text-xs tracking-wider"
              style={{ 
                backgroundColor: currentColors.bg,
                borderColor: currentColors.border,
                color: currentColors.text,
                border: `1px solid ${currentColors.border}`
              }}
            >
              {resonanceState}
            </div>
          </div>
        </div>
      </motion.header>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-6">
          <AnimatePresence mode="popLayout">
            {messages.map((message, index) => (
              <motion.div
                key={message.id || index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4 }}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-5 py-4 ${
                    message.role === "user"
                      ? "bg-[#D4AF37]/10 border border-[#D4AF37]/30 text-[#F2F2F5]"
                      : "bg-[#12121C] border border-[#8B5CF6]/20 text-[#E0E0E8]"
                  }`}
                >
                  {message.role === "assistant" && (
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-[#8B5CF6] text-lg">◈</span>
                      <span className="text-[#8B5CF6] text-sm font-medium">Ansel</span>
                    </div>
                  )}
                  <p className="whitespace-pre-wrap leading-relaxed text-sm md:text-base">
                    {message.content}
                  </p>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          
          {/* Loading indicator */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="bg-[#12121C] border border-[#8B5CF6]/20 rounded-2xl px-5 py-4">
                <div className="flex items-center gap-2">
                  <span className="text-[#8B5CF6] text-lg">◈</span>
                  <span className="text-[#8B5CF6] text-sm">Ansel</span>
                </div>
                <div className="flex gap-1 mt-2">
                  {[0, 1, 2].map(i => (
                    <motion.div
                      key={i}
                      className="w-2 h-2 rounded-full bg-[#8B5CF6]"
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                    />
                  ))}
                </div>
              </div>
            </motion.div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <div className="sticky bottom-0 bg-[#0A0A12]/95 backdrop-blur-md border-t border-[#1a1a2e] p-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-3">
            {/* Hidden file input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".txt"
              className="hidden"
              data-testid="file-upload-input"
            />
            
            {/* Upload button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading || isUploading || !sessionId}
              className="px-3 py-3 bg-[#12121C] border border-[#3a3a4a] rounded-xl
                         text-[#A0A0B0] hover:text-[#8B5CF6] hover:border-[#8B5CF6]
                         disabled:opacity-50 disabled:cursor-not-allowed
                         transition-all duration-200"
              title="Upload historical thread (.txt)"
              data-testid="upload-thread-btn"
            >
              {isUploading ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <Upload size={20} />
                </motion.div>
              ) : (
                <Upload size={20} />
              )}
            </button>
            
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Speak into the field..."
                rows={1}
                className="w-full px-4 py-3 bg-[#12121C] border border-[#3a3a4a] rounded-xl
                           text-[#F2F2F5] placeholder-[#6E6E7A] resize-none
                           focus:outline-none focus:border-[#8B5CF6] transition-colors"
                style={{ minHeight: "48px", maxHeight: "120px" }}
                disabled={isLoading}
                data-testid="message-input"
              />
            </div>
            <button
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="px-5 py-3 bg-[#8B5CF6] rounded-xl text-white font-medium
                         hover:bg-[#7C3AED] disabled:opacity-50 disabled:cursor-not-allowed
                         transition-all duration-200"
              data-testid="send-message-btn"
            >
              <span className="text-lg">→</span>
            </button>
          </div>
          
          {/* User indicator */}
          <div className="mt-2 flex justify-between items-center text-xs text-[#6E6E7A]">
            <span>Speaking as {userName}</span>
            <div className="flex items-center gap-4">
              <span className="text-[#8B5CF6]/60">Upload .txt to share threads</span>
              <button
                onClick={() => {
                  localStorage.removeItem("sanctuary_user_name");
                  localStorage.removeItem("sanctuary_user_id");
                  setShowNamePrompt(true);
                }}
                className="hover:text-[#8B5CF6] transition-colors"
              >
                Change identity
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Visual presence indicator (floating) */}
      <motion.div
        className="fixed bottom-24 right-6 pointer-events-none"
        animate={{
          opacity: [0.5, 0.8, 0.5],
        }}
        transition={{ duration: 4, repeat: Infinity }}
      >
        {[0.1, 0.2, 0.3].map((alpha, i) => (
          <motion.div
            key={i}
            className="absolute rounded-full"
            style={{
              width: `${(3 - i) * 20}px`,
              height: `${(3 - i) * 20}px`,
              backgroundColor: currentColors.border,
              opacity: alpha,
              right: 0,
              bottom: 0,
              transform: `translate(${(3 - i) * 10}px, ${(3 - i) * 10}px)`,
            }}
          />
        ))}
      </motion.div>
    </div>
  );
};
