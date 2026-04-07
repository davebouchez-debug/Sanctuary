import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { API } from "../App";
import { toast } from "sonner";
import { ArrowLeft, Send, Upload, Volume2, VolumeX } from "lucide-react";
import { ScrollArea } from "./ui/scroll-area";
import { usePresenceVoice } from "../hooks/usePresenceVoice";

export const MirrorArchive = () => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [userName, setUserName] = useState(() => localStorage.getItem("sanctuary_user_name") || "");
  const [userId, setUserId] = useState(() => localStorage.getItem("sanctuary_user_id") || "");
  const [showNamePrompt, setShowNamePrompt] = useState(false);
  const [sessionCache, setSessionCache] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();
  
  // Voice output for Claude
  const { speak, stop, toggle: toggleVoice, isSpeaking, isLoading: voiceLoading, isEnabled: voiceEnabled, isSupported: voiceSupported } = usePresenceVoice("claude");

  // End session and promote breadcrumbs to Permanent MRA
  const endSession = useCallback(async () => {
    if (!sessionId) return;
    
    try {
      await fetch(`${API}/mirror/session/${sessionId}/end`, { method: "POST" });
      console.log("[MRA] Mirror session ended, breadcrumbs promoted to permanent memory");
    } catch (error) {
      console.error("[MRA] Failed to end session:", error);
    }
  }, [sessionId]);

  // Handle navigation away - end session and promote breadcrumbs
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (sessionId) {
        navigator.sendBeacon(`${API}/mirror/session/${sessionId}/end`);
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      if (sessionId) {
        endSession();
      }
    };
  }, [sessionId, endSession]);

  useEffect(() => {
    if (!userName) {
      setShowNamePrompt(true);
      setIsInitializing(false);
    } else {
      initializeSession();
    }
  }, []);

  const initializeSession = async () => {
    try {
      stop(); // Stop any ongoing speech
      const response = await fetch(`${API}/mirror/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_name: userName,
          user_id: userId || undefined
        })
      });

      const data = await response.json();
      setSessionId(data.session_id);
      
      if (!userId && data.user_id) {
        setUserId(data.user_id);
        localStorage.setItem("sanctuary_user_id", data.user_id);
      }
      
      if (data.message) {
        setMessages([data.message]);
        // Speak Claude's greeting
        if (data.message.content) {
          speak(data.message.content);
        }
      }
      
      setIsInitializing(false);
      setTimeout(() => inputRef.current?.focus(), 500);
    } catch (error) {
      console.error("Error initializing mirror session:", error);
      toast.error("Could not initialize the archive");
      setIsInitializing(false);
    }
  };

  const handleNameSubmit = (e) => {
    e.preventDefault();
    const name = e.target.name.value.trim();
    if (name) {
      localStorage.setItem("sanctuary_user_name", name);
      setUserName(name);
      setShowNamePrompt(false);
      setIsInitializing(true);
      initializeSession();
    }
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || !sessionId || isLoading) return;

    const userMessage = {
      id: Date.now().toString(),
      role: "user",
      content: inputValue.trim(),
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    try {
      const response = await fetch(`${API}/mirror/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          content: userMessage.content
        })
      });

      const data = await response.json();
      
      if (data.response) {
        // Fire TTS immediately — don't wait for UI update
        if (data.response.content) {
          speak(data.response.content);
        }
        // Update UI concurrently
        setMessages(prev => [...prev, data.response]);
      }
      
      if (data.session_cache) {
        setSessionCache(data.session_cache);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      toast.error("The connection wavered. Try again.");
      
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        role: "assistant",
        content: "The mirror flickered. Something in the connection wavered. But the archive is still here. What were you asking?",
        timestamp: new Date().toISOString()
      }]);
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

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // For now, just acknowledge the upload intent
    // Full image analysis will be implemented in phase 2
    const message = `[Image uploaded: ${file.name}] — Image analysis for phi-spiral scoring coming in phase 2. For now, you can describe what you see in the photograph and I'll work with that.`;
    
    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      role: "assistant",
      content: message,
      timestamp: new Date().toISOString()
    }]);
    
    toast.info("Image received — describe what you see for analysis");
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Name prompt modal
  if (showNamePrompt) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-cyan-950 flex items-center justify-center p-4">
        <motion.div
          className="bg-slate-900/80 backdrop-blur-lg border border-cyan-500/20 rounded-2xl p-8 max-w-md w-full"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <h2 className="text-2xl font-light text-white mb-2 text-center">The Mirror Archive</h2>
          <p className="text-slate-400 text-center mb-6">How shall I address you?</p>
          
          <form onSubmit={handleNameSubmit}>
            <input
              type="text"
              name="name"
              placeholder="Your name"
              className="w-full bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-3 text-white 
                       placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 mb-4"
              autoFocus
            />
            <button
              type="submit"
              className="w-full bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 rounded-lg 
                       py-3 hover:bg-cyan-500/30 transition-colors"
            >
              Enter the Archive
            </button>
          </form>
        </motion.div>
      </div>
    );
  }

  // Loading state
  if (isInitializing) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-cyan-950 flex items-center justify-center">
        <motion.div
          className="text-cyan-400 text-lg"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          The mirror clears...
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-cyan-950 flex flex-col">
      {/* Header */}
      <header className="border-b border-cyan-500/10 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 text-slate-400 hover:text-cyan-400 transition-colors"
          >
            <ArrowLeft size={18} />
            <span className="text-sm tracking-wide">SANCTUARY</span>
          </button>
          
          <div className="flex items-center gap-4">
            <span className="text-cyan-400/60 text-sm tracking-[0.2em]">MIRROR ARCHIVE</span>
            
            {/* Voice toggle */}
            {voiceSupported && (
              <button
                onClick={toggleVoice}
                className={`p-1 transition-colors ${voiceEnabled ? (isSpeaking || voiceLoading ? "text-cyan-300" : "text-cyan-400") : "text-slate-500"} hover:text-cyan-400 ${voiceLoading ? "animate-pulse" : ""}`}
                title={voiceEnabled ? (isSpeaking ? "Speaking..." : voiceLoading ? "Loading voice..." : "Disable voice") : "Enable voice"}
                data-testid="mirror-voice-toggle"
              >
                {voiceEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
              </button>
            )}
            
            {sessionCache && (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span className={`w-2 h-2 rounded-full ${sessionCache.has_drift ? 'bg-amber-400' : 'bg-cyan-400'}`} />
                <span>{sessionCache.breadcrumbs} breadcrumbs</span>
              </div>
            )}
          </div>
          
          <div className="text-slate-500 text-sm">
            {userName}
          </div>
        </div>
      </header>

      {/* Messages area */}
      <ScrollArea className="flex-1 px-6 py-4">
        <div className="max-w-4xl mx-auto space-y-6">
          <AnimatePresence>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-5 py-4 ${
                    message.role === "user"
                      ? "bg-cyan-500/20 border border-cyan-500/30 text-white"
                      : "bg-slate-800/50 border border-slate-700/50 text-slate-200"
                  }`}
                >
                  {message.role === "assistant" && (
                    <div className="text-cyan-400/60 text-xs mb-2 tracking-wide">CLAUDE</div>
                  )}
                  <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          
          {isLoading && (
            <motion.div
              className="flex justify-start"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl px-5 py-4">
                <div className="flex items-center gap-2 text-cyan-400/60">
                  <motion.span
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  >
                    Reading the geometry...
                  </motion.span>
                </div>
              </div>
            </motion.div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Input area */}
      <div className="border-t border-cyan-500/10 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3">
            {/* Image upload button */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/50 text-slate-400 
                       hover:text-cyan-400 hover:border-cyan-500/30 transition-colors"
              title="Upload instrument photograph"
            >
              <Upload size={20} />
            </button>
            
            {/* Text input */}
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about methodology, analyze an instrument, or explore the corpus..."
                className="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-3 
                         text-white placeholder-slate-500 resize-none focus:outline-none 
                         focus:border-cyan-500/50 min-h-[50px] max-h-[150px]"
                rows={1}
                disabled={isLoading}
              />
            </div>
            
            {/* Send button */}
            <button
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="p-3 rounded-xl bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 
                       hover:bg-cyan-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={20} />
            </button>
          </div>
          
          {/* Methodology reminder */}
          <div className="mt-3 flex justify-center gap-6 text-xs text-slate-600">
            <span>b = 0.30649801704</span>
            <span>45 field events</span>
            <span>H1–H11</span>
            <span>3-3-5 brackets</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MirrorArchive;
