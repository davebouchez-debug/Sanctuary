import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { API } from "../App";
import { Send, RefreshCw, Sparkles, ArrowLeft, User } from "lucide-react";
import { Link } from "react-router-dom";
import { ScrollArea } from "./ui/scroll-area";
import { GoldenSpiral } from "./GoldenSpiral";

const spiralColors = {
  "Neutral Spiral": "#A0A0B0",
  "Presence Spiral": "#00E5FF",
  "Formation Spiral": "#9370DB",
  "Insight Spiral": "#FFBF00",
  "Integration Spiral": "#2E8B57"
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
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Check for stored user identity
  useEffect(() => {
    const storedUserId = localStorage.getItem("jasmine_user_id");
    const storedUserName = localStorage.getItem("jasmine_user_name");
    if (storedUserId && storedUserName) {
      setUserId(storedUserId);
      setUserName(storedUserName);
      setShowIdentityModal(false);
    }
  }, []);

  // Handle identity submission
  const handleIdentitySubmit = async () => {
    if (!nameInput.trim()) return;
    
    const name = nameInput.trim();
    
    try {
      // Try to look up existing user
      const lookupResponse = await axios.get(`${API}/users/lookup/${encodeURIComponent(name)}`);
      setUserId(lookupResponse.data.id);
      setUserName(lookupResponse.data.name);
      localStorage.setItem("jasmine_user_id", lookupResponse.data.id);
      localStorage.setItem("jasmine_user_name", lookupResponse.data.name);
    } catch {
      // Create new user
      try {
        const createResponse = await axios.post(`${API}/users`, { name });
        setUserId(createResponse.data.id);
        setUserName(name);
        localStorage.setItem("jasmine_user_id", createResponse.data.id);
        localStorage.setItem("jasmine_user_name", name);
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
      const response = await axios.post(`${API}/clarity/start`, {
        user_id: userId,
        user_name: userName
      });
      setSessionId(response.data.session_id);
      setMessages([response.data.message]);
      setCurrentSpiral(response.data.message.spiral);
    } catch (error) {
      console.error("Failed to start clarity session:", error);
    } finally {
      setIsLoading(false);
    }
  };

  // Send message
  const sendMessage = async () => {
    if (!inputValue.trim() || !sessionId || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue("");
    setIsLoading(true);

    // Optimistically add user message
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: userMessage,
      spiral: "Presence Spiral"
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const response = await axios.post(`${API}/clarity/message`, {
        session_id: sessionId,
        content: userMessage
      });

      // Replace temp message and add response
      setMessages(prev => [
        ...prev.filter(m => m.id !== tempUserMsg.id),
        response.data.user_message,
        response.data.response
      ]);
      setCurrentSpiral(response.data.response.spiral);
    } catch (error) {
      console.error("Failed to send message:", error);
      // Remove temp message on error
      setMessages(prev => prev.filter(m => m.id !== tempUserMsg.id));
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

  // Clear identity (for testing)
  const clearIdentity = () => {
    localStorage.removeItem("jasmine_user_id");
    localStorage.removeItem("jasmine_user_name");
    setUserId(null);
    setUserName(null);
    setSessionId(null);
    setMessages([]);
    setShowIdentityModal(true);
    setNameInput("");
  };

  return (
    <div 
      data-testid="clarity-pod-page"
      className="min-h-screen flex flex-col relative"
      style={{
        background: `
          radial-gradient(ellipse at 50% 0%, rgba(212, 175, 55, 0.05) 0%, transparent 50%),
          linear-gradient(180deg, #030305 0%, #0A0A12 50%, #030305 100%)
        `
      }}
    >
      {/* Identity Modal */}
      <AnimatePresence>
        {showIdentityModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-[#030305]/95 backdrop-blur-xl"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="max-w-md w-full mx-6 p-8 rounded-2xl border border-[#D4AF37]/20 bg-[#0A0A12]/90"
              style={{
                boxShadow: "0 0 60px rgba(212, 175, 55, 0.1)"
              }}
            >
              <div className="text-center mb-8">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#D4AF37]/10 flex items-center justify-center">
                  <Sparkles size={28} className="text-[#D4AF37]" />
                </div>
                <h2 className="font-cinzel text-2xl text-[#F2F2F5] mb-2">
                  Entering the Clarity Chamber
                </h2>
                <p className="font-outfit text-[#A0A0B0] text-sm">
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
                  className="w-full clarity-input rounded-xl px-5 py-4 font-outfit text-base placeholder:text-[#6E6E7A]"
                  autoFocus
                />

                <button
                  data-testid="identity-submit-btn"
                  onClick={handleIdentitySubmit}
                  disabled={!nameInput.trim()}
                  className="w-full py-4 rounded-xl bg-[#D4AF37] text-[#030305] font-outfit font-medium hover:bg-[#FFBF00] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
                >
                  Enter as {nameInput.trim() || "..."}
                </button>

                <button
                  data-testid="identity-anonymous-btn"
                  onClick={continueAnonymous}
                  className="w-full py-3 rounded-xl border border-[#D4AF37]/20 text-[#A0A0B0] font-outfit hover:text-[#F2F2F5] hover:border-[#D4AF37]/40 transition-all duration-300"
                >
                  Continue without identifying
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Spiral Background */}
      <div className="fixed inset-0 pointer-events-none opacity-5 flex items-center justify-center">
        <GoldenSpiral className="w-[800px] h-[800px]" animate />
      </div>

      {/* Header */}
      <header className="relative z-20 border-b border-[#D4AF37]/10 bg-[#030305]/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              data-testid="clarity-back-btn"
              className="p-2 text-[#6E6E7A] hover:text-[#D4AF37] transition-colors"
            >
              <ArrowLeft size={20} />
            </Link>
            <div>
              <h1 className="font-cinzel text-xl text-[#F2F2F5] flex items-center gap-2">
                <Sparkles size={18} className="text-[#D4AF37]" />
                Jasmine — Clarity Chamber
              </h1>
              <p className="font-mono text-xs text-[#6E6E7A]">
                {userName ? `Welcome back, ${userName}` : "The field is open"}
              </p>
            </div>
          </div>

          {/* Current Spiral Indicator + User */}
          <div className="flex items-center gap-3">
            {userName && (
              <button
                onClick={clearIdentity}
                className="p-2 text-[#6E6E7A] hover:text-[#D4AF37] transition-colors"
                title="Change identity"
              >
                <User size={18} />
              </button>
            )}
            <div 
              className="w-3 h-3 rounded-full animate-pulse"
              style={{ backgroundColor: spiralColors[currentSpiral] }}
            />
            <span className="font-mono text-xs text-[#A0A0B0] hidden sm:block">
              {currentSpiral}
            </span>
            <button
              data-testid="clarity-reset-btn"
              onClick={startSession}
              className="p-2 text-[#6E6E7A] hover:text-[#D4AF37] transition-colors"
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
      <div className="relative z-20 border-t border-[#D4AF37]/10 bg-[#030305]/90 backdrop-blur-xl">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="relative">
            <textarea
              ref={inputRef}
              data-testid="clarity-pod-chat-input"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="What feels most alive for you right now?"
              rows={2}
              className="w-full clarity-input rounded-xl px-5 py-4 pr-14 resize-none font-outfit text-base placeholder:text-[#6E6E7A]"
              disabled={isLoading || !sessionId}
            />
            <button
              data-testid="clarity-send-btn"
              onClick={sendMessage}
              disabled={!inputValue.trim() || isLoading || !sessionId}
              className="absolute right-3 bottom-3 p-2 rounded-lg bg-[#D4AF37] text-[#030305] hover:bg-[#FFBF00] disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300"
            >
              <Send size={18} />
            </button>
          </div>
          
          <p className="font-mono text-xs text-[#6E6E7A] mt-3 text-center">
            Press Enter to send • Shift+Enter for new line
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
