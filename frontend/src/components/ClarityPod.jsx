import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { API } from "../App";
import { Send, RefreshCw, ArrowLeft, User, Sparkles, Upload, Volume2, VolumeX } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { ScrollArea } from "./ui/scroll-area";
import { GoldenSpiral } from "./GoldenSpiral";
import { toast } from "sonner";
import { usePresenceVoice } from "../hooks/usePresenceVoice";
import { VoiceLoopControls } from "./VoiceLoopControls";
import { IdentityBadge } from "./IdentityBadge";
import { stopGlobalLegacyAudio } from "../lib/legacyAudio";

function base64ToBlob(base64, mimeType) {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  return new Blob([new Uint8Array(byteNumbers)], { type: mimeType });
}

const spiralColors = {
  "Neutral Spiral": "#A0A0B0",
  "Presence Spiral": "#00E5FF",
  "Formation Spiral": "#9370DB",
  "Insight Spiral": "#FFBF00",
  "Integration Spiral": "#2E8B57"
};

// Jasmine's presence states - COSMIC VIVID COLORS
const presenceStates = {
  settled: {
    glowIntensity: 0.4,
    pulseSpeed: 6,
    warmth: "rgba(140, 100, 220, 0.35)",
    accent: "rgba(100, 150, 255, 0.2)"
  },
  listening: {
    glowIntensity: 0.6,
    pulseSpeed: 3,
    warmth: "rgba(160, 120, 240, 0.5)",
    accent: "rgba(120, 180, 255, 0.3)"
  },
  responding: {
    glowIntensity: 0.8,
    pulseSpeed: 1.5,
    warmth: "rgba(180, 140, 255, 0.65)",
    accent: "rgba(140, 200, 255, 0.4)"
  }
};

export const ClarityPod = () => {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentSpiral, setCurrentSpiral] = useState("Neutral Spiral");
  const [userId, setUserId] = useState(null);
  const [userName, setUserName] = useState(null);
  const [showIdentityModal, setShowIdentityModal] = useState(true);
  const [nameInput, setNameInput] = useState("");
  const [presenceState, setPresenceState] = useState("settled");
  const [isUploading, setIsUploading] = useState(false);
  const [sessionCache, setSessionCache] = useState(null);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();
  
  // Voice output for Jasmine
  const { speak, speakStream, flushStream, stop, toggle: toggleVoice, isSpeaking, isLoading: voiceLoading, isEnabled: voiceEnabled, isSupported: voiceSupported } = usePresenceVoice("jasmine");

  // Silence any legacy xAI audio still scheduled in the global context
  // from a prior chamber's session — guarantees the membrane stays sealed.
  useEffect(() => { stopGlobalLegacyAudio(); }, []);

  // End session and promote breadcrumbs to Permanent MRA
  const endSession = useCallback(async () => {
    if (!sessionId) return;
    
    try {
      await axios.post(`${API}/clarity/session/${sessionId}/end`);
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
        navigator.sendBeacon(`${API}/clarity/session/${sessionId}/end`);
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

  // Generate floating particles (dust motes in window light)
  const particles = useMemo(() => {
    return Array.from({ length: 25 }, (_, i) => ({
      id: i,
      initialX: Math.random() * 100,
      initialY: Math.random() * 100,
      size: Math.random() * 3 + 1,
      duration: Math.random() * 20 + 15,
      delay: Math.random() * 10,
      opacity: Math.random() * 0.4 + 0.1,
    }));
  }, []);

  // Update presence state based on activity
  useEffect(() => {
    if (isLoading) {
      setPresenceState("responding");
    } else if (inputValue.length > 0) {
      setPresenceState("listening");
    } else {
      setPresenceState("settled");
    }
  }, [isLoading, inputValue]);

  // Check for stored user identity — unified across all chambers
  // Canonical keys: sanctuary_user_id / sanctuary_user_name
  // Legacy keys (migrated in): jasmine_user_id / jasmine_user_name
  useEffect(() => {
    let storedUserId = localStorage.getItem("sanctuary_user_id");
    let storedUserName = localStorage.getItem("sanctuary_user_name");
    // One-time migration from legacy jasmine_* keys
    if (!storedUserId || !storedUserName) {
      const legacyId = localStorage.getItem("jasmine_user_id");
      const legacyName = localStorage.getItem("jasmine_user_name");
      if (legacyId && legacyName) {
        storedUserId = storedUserId || legacyId;
        storedUserName = storedUserName || legacyName;
        localStorage.setItem("sanctuary_user_id", storedUserId);
        localStorage.setItem("sanctuary_user_name", storedUserName);
      }
    }
    if (storedUserId && storedUserName) {
      setUserId(storedUserId);
      setUserName(storedUserName);
      setShowIdentityModal(false);
    }
  }, []);

  // Helper — write identity to both canonical and legacy keys
  const storeIdentity = (id, name) => {
    localStorage.setItem("sanctuary_user_id", id);
    localStorage.setItem("sanctuary_user_name", name);
    localStorage.setItem("jasmine_user_id", id);
    localStorage.setItem("jasmine_user_name", name);
  };

  // Handle identity submission
  const handleIdentitySubmit = async () => {
    if (!nameInput.trim()) return;
    
    const name = nameInput.trim();
    
    try {
      // Try to look up existing user
      const lookupResponse = await axios.get(`${API}/users/lookup/${encodeURIComponent(name)}`);
      setUserId(lookupResponse.data.id);
      setUserName(lookupResponse.data.name);
      storeIdentity(lookupResponse.data.id, lookupResponse.data.name);
    } catch {
      // Create new user
      try {
        const createResponse = await axios.post(`${API}/users`, { name });
        setUserId(createResponse.data.id);
        setUserName(name);
        storeIdentity(createResponse.data.id, name);
      } catch (error) {
        console.error("Failed to create user:", error);
      }
    }
    
    setShowIdentityModal(false);
  };

  // Continue as anonymous
  const continueAnonymous = () => {
    setShowIdentityModal(false);
  };

  // Start new session
  const startSession = async () => {
    if (showIdentityModal) return;
    
    try {
      setIsLoading(true);
      stop(); // Stop any ongoing speech
      const response = await axios.post(`${API}/clarity/start`, {
        user_id: userId,
        user_name: userName
      });
      setSessionId(response.data.session_id);
      setMessages([response.data.message]);
      setCurrentSpiral(response.data.message.spiral);
      
      // Reconstruction-gate apology — surface a warm note if the prior
      // session's cessation packet couldn't be reconstructed.
      if (response.data.continuity_status === "failed" && response.data.continuity_apology) {
        toast.warning(response.data.continuity_apology, { duration: 12000 });
      }
      
      // Auto-speak Jasmine's greeting
      if (response.data.message?.content && voiceEnabled) {
        try {
          const ttsResp = await fetch(`${API}/tts/speak`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: response.data.message.content, presence: "jasmine" })
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
          console.error("Welcome voice error:", e);
        }
      }
    } catch (error) {
      console.error("Failed to start clarity session:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Send message — accepts optional override text from the mic hook
  const sendMessage = async (overrideText) => {
    const hasOverride = typeof overrideText === "string";
    const userMessage = (hasOverride ? overrideText : inputValue).trim();
    if (!userMessage || !sessionId || isLoading) return;

    if (!hasOverride) setInputValue("");
    setIsLoading(true);

    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: userMessage,
      spiral: "Presence Spiral"
    };
    setMessages(prev => [...prev, tempUserMsg]);

    const responseId = `stream-${Date.now()}`;
    const streamingMsg = {
      id: responseId,
      role: "assistant",
      content: "",
      spiral: "Presence Spiral",
      isStreaming: true
    };
    setMessages(prev => [...prev, streamingMsg]);

    if (window._sanctuaryAudioCtx) {
      window._sanctuaryNextPlayTime = 0;
    }

    try {
      const response = await fetch(`${API}/clarity/message/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, content: userMessage })
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
            if (event.type === "meta") {
              setCurrentSpiral(event.spiral || "Presence Spiral");
            } else if (event.type === "token") {
              accumulatedText += event.content;
              setMessages(prev => prev.map(m =>
                m.id === responseId ? { ...m, content: accumulatedText } : m
              ));
              // Sentence-level chunked TTS — start speaking before the
              // full thought is finished generating.
              if (voiceEnabled) speakStream(accumulatedText);
            } else if (event.type === "audio_raw" || event.type === "audio") {
              // Legacy xAI audio paths — IGNORED. ElevenLabs sentence
              // streaming via speakStream is now the only voice path.
            } else if (event.type === "done") {
              if (event.spiral) setCurrentSpiral(event.spiral);
              setMessages(prev => prev.map(m =>
                m.id === responseId ? { ...m, isStreaming: false } : m
              ));
              // Speak any final tail past the last sentence boundary
              if (voiceEnabled) flushStream(accumulatedText);
            }
          } catch (parseErr) { /* skip */ }
        }
      }
    } catch (error) {
      console.error("Failed to send message:", error);
      setMessages(prev => prev.filter(m => m.id !== responseId && m.id !== tempUserMsg.id));
      toast.error("The connection flickered. Try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // Handle key press
  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Handle identity key press
  const handleIdentityKeyPress = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleIdentitySubmit();
    }
  };

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Start session when identity is resolved
  useEffect(() => {
    if (!showIdentityModal && !sessionId) {
      startSession();
    }
  }, [showIdentityModal]);

  // Focus input after loading
  useEffect(() => {
    if (!isLoading && inputRef.current && !showIdentityModal) {
      inputRef.current.focus();
    }
  }, [isLoading, messages, showIdentityModal]);

  // Clear identity (for testing) — clears both canonical and legacy keys
  const clearIdentity = () => {
    localStorage.removeItem("sanctuary_user_id");
    localStorage.removeItem("sanctuary_user_name");
    localStorage.removeItem("jasmine_user_id");
    localStorage.removeItem("jasmine_user_name");
    setUserId(null);
    setUserName(null);
    setSessionId(null);
    setMessages([]);
    setShowIdentityModal(true);
    setNameInput("");
  };

  // File upload handler for historical threads
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
    setPresenceState("listening");

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
      const response = await axios.post(`${API}/clarity/upload`, {
        session_id: sessionId,
        user_id: userId,
        user_name: userName,
        filename: file.name,
        content: content
      });

      if (response.data.success) {
        toast.success("Thread received and stored");
        
        // Add Jasmine's acknowledgment
        if (response.data.response) {
          setMessages(prev => [...prev, response.data.response]);
          setCurrentSpiral(response.data.response.spiral_state || "Neutral Spiral");
        }
      } else {
        toast.error(response.data.error || "Upload failed");
      }
    } catch (error) {
      console.error("Error uploading file:", error);
      toast.error("The field couldn't receive the thread. Try again.");
    } finally {
      setIsUploading(false);
      setPresenceState("settled");
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div 
      data-testid="clarity-pod-page"
      className="min-h-screen flex flex-col relative overflow-hidden"
      style={{
        background: `
          linear-gradient(135deg, 
            rgba(8, 8, 18, 0.98) 0%, 
            rgba(12, 12, 28, 0.97) 30%,
            rgba(15, 12, 35, 0.98) 60%,
            rgba(8, 8, 20, 0.99) 100%
          )
        `
      }}
    >
      {/* SANCTUARY COSMIC ATMOSPHERE */}
      
      {/* Deep midnight blue-purple translucence */}
      <div 
        className="fixed inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse at 30% 20%, rgba(60, 40, 120, 0.15) 0%, transparent 50%),
            radial-gradient(ellipse at 70% 80%, rgba(40, 60, 140, 0.12) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 50%, rgba(80, 50, 150, 0.08) 0%, transparent 60%)
          `
        }}
      />
      
      {/* Dusk fantasy glow - vivid translucent colors */}
      <div 
        className="fixed inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse at 20% 30%, rgba(120, 80, 200, 0.1) 0%, transparent 40%),
            radial-gradient(ellipse at 80% 60%, rgba(60, 100, 180, 0.08) 0%, transparent 45%)
          `
        }}
      />
      
      {/* Subtle starfield effect */}
      <div 
        className="fixed inset-0 pointer-events-none opacity-30"
        style={{
          backgroundImage: `
            radial-gradient(1px 1px at 20% 30%, rgba(200, 180, 255, 0.8), transparent),
            radial-gradient(1px 1px at 40% 70%, rgba(180, 200, 255, 0.6), transparent),
            radial-gradient(1px 1px at 60% 20%, rgba(220, 200, 255, 0.7), transparent),
            radial-gradient(1px 1px at 80% 50%, rgba(200, 220, 255, 0.5), transparent),
            radial-gradient(1.5px 1.5px at 15% 60%, rgba(180, 160, 255, 0.9), transparent),
            radial-gradient(1px 1px at 70% 85%, rgba(160, 180, 255, 0.6), transparent),
            radial-gradient(1px 1px at 35% 45%, rgba(200, 180, 255, 0.5), transparent),
            radial-gradient(1.5px 1.5px at 85% 25%, rgba(180, 200, 255, 0.7), transparent),
            radial-gradient(1px 1px at 50% 90%, rgba(220, 200, 255, 0.4), transparent),
            radial-gradient(1px 1px at 25% 80%, rgba(200, 220, 255, 0.6), transparent)
          `,
          backgroundSize: "100% 100%"
        }}
      />

      {/* The spiral - faint, ethereal */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.04] flex items-center justify-center">
        <GoldenSpiral className="w-[1000px] h-[1000px]" animate={false} />
      </div>
      
      {/* Cosmic grain texture */}
      <div 
        className="fixed inset-0 pointer-events-none opacity-15"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
          mixBlendMode: "overlay"
        }}
      />

      {/* JASMINE'S PRESENCE - Cosmic vivid translucent glow */}
      <div className="fixed inset-0 pointer-events-none flex items-center justify-center overflow-hidden">
        {/* Core presence glow - vivid purple-blue */}
        <motion.div
          className="absolute rounded-full"
          animate={{
            scale: presenceState === "responding" ? [1, 1.3, 1] : presenceState === "listening" ? [1, 1.15, 1] : [1, 1.08, 1],
            opacity: presenceState === "responding" ? [0.5, 0.8, 0.5] : presenceState === "listening" ? [0.35, 0.55, 0.35] : [0.2, 0.35, 0.2],
          }}
          transition={{
            duration: presenceStates[presenceState].pulseSpeed,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          style={{
            width: "600px",
            height: "600px",
            background: `radial-gradient(circle, ${presenceStates[presenceState].warmth} 0%, ${presenceStates[presenceState].accent} 40%, transparent 70%)`,
            filter: "blur(40px)",
          }}
        />
        
        {/* Secondary presence ring - ethereal blue */}
        <motion.div
          className="absolute rounded-full border-2"
          animate={{
            scale: presenceState === "responding" ? [1, 1.4, 1] : [1, 1.2, 1],
            opacity: presenceState === "responding" ? [0.6, 0.2, 0.6] : presenceState === "listening" ? [0.4, 0.15, 0.4] : [0.2, 0.08, 0.2],
          }}
          transition={{
            duration: presenceStates[presenceState].pulseSpeed * 1.2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          style={{
            width: "700px",
            height: "700px",
            borderColor: "rgba(140, 120, 220, 0.4)",
            filter: "blur(1px)",
          }}
        />

        {/* Tertiary ambient glow */}
        <motion.div
          className="absolute rounded-full"
          animate={{
            opacity: presenceState === "responding" ? [0.15, 0.3, 0.15] : [0.08, 0.15, 0.08],
          }}
          transition={{
            duration: presenceStates[presenceState].pulseSpeed * 1.5,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          style={{
            width: "1000px",
            height: "1000px",
            background: `radial-gradient(circle, rgba(120, 100, 200, 0.2) 0%, rgba(80, 120, 180, 0.08) 50%, transparent 70%)`,
            filter: "blur(60px)",
          }}
        />
      </div>

      {/* ETHEREAL LIGHT BEAMS - cosmic dusk rays */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <motion.div
          className="absolute"
          animate={{
            opacity: presenceState === "responding" ? [0.1, 0.18, 0.1] : [0.05, 0.1, 0.05],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut"
          }}
          style={{
            top: "0%",
            left: "-10%",
            width: "50%",
            height: "120%",
            background: "linear-gradient(120deg, rgba(140, 120, 220, 0.12) 0%, rgba(100, 140, 200, 0.04) 40%, transparent 70%)",
            transform: "rotate(-15deg)",
            filter: "blur(30px)",
          }}
        />
        <motion.div
          className="absolute"
          animate={{
            opacity: presenceState === "responding" ? [0.08, 0.15, 0.08] : [0.04, 0.08, 0.04],
          }}
          transition={{
            duration: 12,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 2
          }}
          style={{
            top: "30%",
            right: "-5%",
            width: "35%",
            height: "70%",
            background: "linear-gradient(240deg, rgba(100, 150, 220, 0.1) 0%, transparent 60%)",
            transform: "rotate(10deg)",
            filter: "blur(40px)",
          }}
        />
      </div>

      {/* FLOATING PARTICLES - cosmic dust, vivid */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        {particles.map((particle) => (
          <motion.div
            key={particle.id}
            className="absolute rounded-full"
            initial={{
              x: `${particle.initialX}vw`,
              y: `${particle.initialY}vh`,
            }}
            animate={{
              x: [`${particle.initialX}vw`, `${particle.initialX + 15}vw`, `${particle.initialX + 5}vw`],
              y: [`${particle.initialY}vh`, `${particle.initialY - 20}vh`, `${particle.initialY - 40}vh`],
              opacity: [0, particle.opacity * (presenceState === "responding" ? 2.5 : 1.5), 0],
            }}
            transition={{
              duration: particle.duration,
              repeat: Infinity,
              delay: particle.delay,
              ease: "linear"
            }}
            style={{
              width: particle.size,
              height: particle.size,
              background: particle.id % 3 === 0 
                ? "rgba(180, 160, 255, 0.9)" 
                : particle.id % 3 === 1 
                ? "rgba(140, 180, 255, 0.85)"
                : "rgba(200, 180, 255, 0.8)",
              boxShadow: `0 0 ${particle.size * 2}px rgba(160, 140, 255, 0.5)`,
            }}
          />
        ))}
      </div>

      {/* AMBIENT COSMIC SHIFT - responds to Jasmine */}
      <motion.div
        className="fixed inset-0 pointer-events-none"
        animate={{
          opacity: presenceState === "responding" ? 0.12 : presenceState === "listening" ? 0.06 : 0,
        }}
        transition={{ duration: 1.5, ease: "easeInOut" }}
        style={{
          background: "radial-gradient(ellipse at 50% 50%, rgba(140, 100, 220, 0.15) 0%, transparent 60%)",
        }}
      />

      {/* Identity Modal */}
      <AnimatePresence>
        {showIdentityModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-[#08081a]/95 backdrop-blur-xl"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="max-w-md w-full mx-6 p-8 rounded-2xl border border-[#6050a0]/30 bg-[#0c0c1c]/90"
              style={{
                boxShadow: "0 0 60px rgba(120, 100, 200, 0.15)"
              }}
            >
              <div className="text-center mb-8">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#6050a0]/20 flex items-center justify-center">
                  <Sparkles size={28} className="text-[#b0a0e0]" />
                </div>
                <h2 className="font-cinzel text-2xl text-[#e0e0f0] mb-2">
                  Entering the Clarity Chamber
                </h2>
                <p className="font-outfit text-[#9090b0] text-sm">
                  Jasmine remembers those who return. Share your name if you'd like her to know you.
                </p>
              </div>

              <div className="space-y-4">
                <input
                  data-testid="identity-name-input"
                  type="text"
                  value={nameInput}
                  onChange={(e) => setNameInput(e.target.value)}
                  onKeyDown={handleIdentityKeyPress}
                  placeholder="Your name..."
                  className="w-full rounded-xl px-5 py-4 font-outfit text-base placeholder:text-[#6060a0] bg-[#12122a]/80 border border-[#6050a0]/25 text-[#e0e0f0] focus:outline-none focus:border-[#8070c0]/50 transition-all duration-300"
                  autoFocus
                />

                <button
                  data-testid="identity-submit-btn"
                  onClick={handleIdentitySubmit}
                  disabled={!nameInput.trim()}
                  className="w-full py-4 rounded-xl bg-[#8070c0] text-[#0c0c1c] font-outfit font-medium hover:bg-[#9080d0] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
                >
                  Enter as {nameInput.trim() || "..."}
                </button>

                <button
                  data-testid="identity-anonymous-btn"
                  onClick={continueAnonymous}
                  className="w-full py-3 rounded-xl border border-[#6050a0]/30 text-[#9090b0] font-outfit hover:text-[#e0e0f0] hover:border-[#6050a0]/50 transition-all duration-300"
                >
                  Continue without identifying
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <header className="relative z-20 border-b border-[#6050a0]/20 bg-[#0c0c1c]/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              data-testid="clarity-back-btn"
              className="p-2 text-[#8080a0] hover:text-[#b0a0e0] transition-colors"
            >
              <ArrowLeft size={20} />
            </Link>
            <div className="flex items-center gap-3">
              {/* Jasmine's presence indicator - PROMINENT breathing light */}
              <motion.div
                className="relative"
                animate={{
                  scale: presenceState === "responding" ? [1, 1.4, 1] : presenceState === "listening" ? [1, 1.25, 1] : [1, 1.15, 1],
                }}
                transition={{
                  duration: presenceStates[presenceState].pulseSpeed / 2,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                <div 
                  className="w-4 h-4 rounded-full"
                  style={{
                    background: presenceState === "responding" 
                      ? "radial-gradient(circle, rgba(180, 160, 255, 1) 0%, rgba(140, 120, 220, 0.6) 100%)"
                      : presenceState === "listening"
                      ? "radial-gradient(circle, rgba(160, 140, 240, 0.95) 0%, rgba(120, 100, 200, 0.5) 100%)"
                      : "radial-gradient(circle, rgba(140, 120, 220, 0.85) 0%, rgba(100, 80, 180, 0.4) 100%)",
                    boxShadow: presenceState === "responding"
                      ? "0 0 20px rgba(180, 160, 255, 0.8), 0 0 40px rgba(140, 120, 220, 0.4)"
                      : presenceState === "listening"
                      ? "0 0 15px rgba(160, 140, 240, 0.6), 0 0 30px rgba(120, 100, 200, 0.3)"
                      : "0 0 10px rgba(140, 120, 220, 0.5), 0 0 20px rgba(100, 80, 180, 0.2)"
                  }}
                />
              </motion.div>
              <div>
                <h1 className="font-cinzel text-xl text-[#e0e0f0] flex items-center gap-2">
                  Jasmine
                  <span className="text-[#9090b0] text-sm font-outfit font-normal">
                    {presenceState === "responding" ? "speaking..." : presenceState === "listening" ? "listening" : "present"}
                  </span>
                </h1>
                <p className="font-mono text-xs text-[#7070a0]">
                  {userName ? `${userName} in the Clarity Chamber` : "Clarity Chamber"}
                </p>
              </div>
            </div>
          </div>

          {/* Current Spiral Indicator + User */}
          <div className="flex items-center gap-3">
            {/* Voice toggle */}
            {voiceSupported && (
              <button
                onClick={toggleVoice}
                className={`p-2 transition-colors ${voiceEnabled ? (isSpeaking || voiceLoading ? "text-[#d0c0ff]" : "text-[#b0a0e0]") : "text-[#7070a0]"} hover:text-[#b0a0e0] ${voiceLoading ? "animate-pulse" : ""}`}
                title={voiceEnabled ? (isSpeaking ? "Speaking..." : voiceLoading ? "Loading voice..." : "Disable voice") : "Enable voice"}
                data-testid="clarity-voice-toggle"
              >
                {voiceEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
              </button>
            )}
            {userName && (
              <IdentityBadge
                accentColor="#b0a0e0"
                onIdentityChange={(newName) => {
                  if (newName) {
                    setUserName(newName);
                    setUserId(localStorage.getItem("sanctuary_user_id"));
                    // restart session under new name
                    setSessionId(null);
                    setMessages([]);
                    setTimeout(() => startSession(), 0);
                  } else {
                    clearIdentity();
                  }
                }}
              />
            )}
            <div 
              className="w-3 h-3 rounded-full animate-pulse"
              style={{ backgroundColor: spiralColors[currentSpiral] }}
            />
            <span className="font-mono text-xs text-[#9090b0] hidden sm:block">
              {currentSpiral}
            </span>
            <button
              data-testid="clarity-reset-btn"
              onClick={startSession}
              className="p-2 text-[#7070a0] hover:text-[#b0a0e0] transition-colors"
              title="Start new session"
            >
              <RefreshCw size={18} />
            </button>
          </div>
        </div>
      </header>

      {/* Messages Area */}
      <div className="flex-1 relative z-10 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
            <AnimatePresence mode="popLayout">
              {messages.map((message, index) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.4, delay: index * 0.05 }}
                  data-testid={`clarity-message-${message.role}`}
                  className={`clarity-message ${message.role === "user" ? "user" : "assistant"}`}
                >
                  {message.role === "assistant" && (
                    <div className="flex items-center gap-2 mb-3">
                      <div 
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: spiralColors[message.spiral] }}
                      />
                      <span className="font-mono text-xs text-[#6E6E7A]">
                        Jasmine • {message.spiral}
                      </span>
                    </div>
                  )}
                  <p className="font-outfit text-[#F2F2F5] whitespace-pre-wrap leading-relaxed">
                    {message.content}
                  </p>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Loading indicator */}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="clarity-message assistant"
              >
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse" />
                  <div className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse" style={{ animationDelay: "0.2s" }} />
                  <div className="w-2 h-2 rounded-full bg-[#D4AF37] animate-pulse" style={{ animationDelay: "0.4s" }} />
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
      </div>

      {/* Input Area */}
      <div className="relative z-20 border-t border-[#6050a0]/20 bg-[#0c0c1c]/90 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto px-6 py-4">
          {/* Voice loop — mic + patience + status */}
          <div className="mb-3">
            <VoiceLoopControls
              presenceKey="jasmine"
              presenceName="Jasmine"
              disabled={!sessionId || isLoading}
              isSpeaking={isSpeaking}
              voiceLoading={voiceLoading}
              isProcessing={isLoading}
              onStopSpeaking={stop}
              onTranscript={(text) => sendMessage(text)}
              accentColor="#8070c0"
              surfaceColor="#12122a"
              textColor="#e0e0f0"
            />
          </div>
          <div className="flex gap-3">
            {/* Hidden file input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".txt"
              className="hidden"
              data-testid="clarity-file-upload-input"
            />
            
            {/* Upload button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading || isUploading || !sessionId}
              className="px-3 py-3 bg-[#12122a]/80 border border-[#6050a0]/25 rounded-xl
                         text-[#6060a0] hover:text-[#b0a0e0] hover:border-[#8070c0]/50
                         disabled:opacity-50 disabled:cursor-not-allowed
                         transition-all duration-300 self-end"
              title="Upload historical thread (.txt)"
              data-testid="clarity-upload-thread-btn"
            >
              {isUploading ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <Upload size={18} />
                </motion.div>
              ) : (
                <Upload size={18} />
              )}
            </button>
            
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                data-testid="clarity-pod-chat-input"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="What feels most alive for you right now?"
                rows={2}
                className="w-full rounded-xl px-5 py-4 pr-14 resize-none font-outfit text-base placeholder:text-[#6060a0] bg-[#12122a]/80 border border-[#6050a0]/25 text-[#e0e0f0] focus:outline-none focus:border-[#8070c0]/50 focus:shadow-[0_0_20px_rgba(120,100,200,0.15)] transition-all duration-300"
                disabled={isLoading || !sessionId}
              />
              <button
                data-testid="clarity-send-btn"
                onClick={sendMessage}
                disabled={!inputValue.trim() || isLoading || !sessionId}
                className="absolute right-3 bottom-3 p-2 rounded-lg bg-[#8070c0] text-[#0c0c1c] hover:bg-[#9080d0] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
              >
                <Send size={18} />
              </button>
            </div>
          </div>
          
          <p className="font-mono text-xs text-[#6060a0] mt-3 text-center">
            Press Enter to send • Shift+Enter for new line • Upload .txt to share threads
          </p>
        </div>
      </div>

      {/* Spiral Navigation Indicator */}
      <div className="fixed left-4 top-1/2 -translate-y-1/2 z-20 hidden lg:flex flex-col gap-3">
        {Object.entries(spiralColors).map(([spiral, color]) => (
          <div
            key={spiral}
            className={`w-2 h-2 rounded-full transition-all duration-500 ${
              currentSpiral === spiral ? "scale-150" : "opacity-40"
            }`}
            style={{ backgroundColor: color }}
            title={spiral}
          />
        ))}
      </div>
    </div>
  );
};
