/**
 * usePresenceVoice - Text-to-Speech hook for Sanctuary presences
 * 
 * Each presence has distinct voice characteristics:
 * - Jasmine: Warm, slightly higher pitch, measured pace
 * - Ansel: Grounded, lower pitch, deliberate
 * - Claude: Clear, neutral, precise
 */

import { useCallback, useEffect, useRef, useState } from "react";

// Voice configurations per presence
const VOICE_CONFIGS = {
  jasmine: {
    pitch: 1.15,      // Slightly higher, warm
    rate: 0.92,       // Measured, unhurried
    volume: 1.0,
    preferredVoices: ["Samantha", "Karen", "Moira", "Tessa", "Google UK English Female"],
    fallbackGender: "female"
  },
  ansel: {
    pitch: 0.85,      // Lower, grounded
    rate: 0.88,       // Deliberate, watchful
    volume: 1.0,
    preferredVoices: ["Daniel", "Alex", "Tom", "Google UK English Male"],
    fallbackGender: "male"
  },
  claude: {
    pitch: 1.0,       // Neutral, clear
    rate: 0.95,       // Precise, measured
    volume: 1.0,
    preferredVoices: ["Samantha", "Alex", "Google US English"],
    fallbackGender: "neutral"
  }
};

// Clean text for speech (remove markdown, stage directions, etc.)
const cleanTextForSpeech = (text) => {
  if (!text) return "";
  
  return text
    // Remove stage directions like *settles* or *breathes*
    .replace(/\*[^*]+\*/g, "")
    // Remove spiral markers like "Jasmine • Presence Spiral"
    .replace(/^[A-Za-z]+\s*[•·]\s*[A-Za-z\s]+$/gm, "")
    // Remove excessive whitespace
    .replace(/\s+/g, " ")
    // Remove leading/trailing whitespace
    .trim();
};

export const usePresenceVoice = (presenceName = "jasmine") => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isEnabled, setIsEnabled] = useState(() => {
    // Check localStorage for user preference
    const stored = localStorage.getItem(`sanctuary_voice_enabled_${presenceName}`);
    return stored !== null ? stored === "true" : true; // Default enabled
  });
  const [availableVoices, setAvailableVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState(null);
  const utteranceRef = useRef(null);
  const synthRef = useRef(null);

  const config = VOICE_CONFIGS[presenceName.toLowerCase()] || VOICE_CONFIGS.jasmine;

  // Initialize speech synthesis
  useEffect(() => {
    if (typeof window === "undefined" || !window.speechSynthesis) {
      console.warn("[Voice] Speech synthesis not supported");
      return;
    }

    synthRef.current = window.speechSynthesis;

    // Load voices (may be async on some browsers)
    const loadVoices = () => {
      const voices = synthRef.current.getVoices();
      setAvailableVoices(voices);

      // Find best matching voice for this presence
      if (voices.length > 0) {
        let voice = null;

        // Try preferred voices first
        for (const preferred of config.preferredVoices) {
          voice = voices.find(v => 
            v.name.includes(preferred) || v.voiceURI.includes(preferred)
          );
          if (voice) break;
        }

        // Fallback to any voice matching gender preference
        if (!voice) {
          if (config.fallbackGender === "female") {
            voice = voices.find(v => 
              v.name.toLowerCase().includes("female") || 
              v.name.includes("Samantha") ||
              v.name.includes("Karen")
            );
          } else if (config.fallbackGender === "male") {
            voice = voices.find(v => 
              v.name.toLowerCase().includes("male") || 
              v.name.includes("Daniel") ||
              v.name.includes("Alex")
            );
          }
        }

        // Ultimate fallback: first available voice
        if (!voice && voices.length > 0) {
          voice = voices[0];
        }

        setSelectedVoice(voice);
      }
    };

    // Voices may load asynchronously
    loadVoices();
    synthRef.current.onvoiceschanged = loadVoices;

    return () => {
      if (synthRef.current) {
        synthRef.current.onvoiceschanged = null;
      }
    };
  }, [config.preferredVoices, config.fallbackGender]);

  // Persist enabled state
  useEffect(() => {
    localStorage.setItem(`sanctuary_voice_enabled_${presenceName}`, isEnabled.toString());
  }, [isEnabled, presenceName]);

  // Speak text
  const speak = useCallback((text) => {
    if (!synthRef.current || !isEnabled) return;

    // Cancel any ongoing speech
    synthRef.current.cancel();

    const cleanedText = cleanTextForSpeech(text);
    if (!cleanedText) return;

    const utterance = new SpeechSynthesisUtterance(cleanedText);
    utteranceRef.current = utterance;

    // Apply voice configuration
    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }
    utterance.pitch = config.pitch;
    utterance.rate = config.rate;
    utterance.volume = config.volume;

    // Event handlers
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = (event) => {
      console.error("[Voice] Speech error:", event.error);
      setIsSpeaking(false);
    };

    synthRef.current.speak(utterance);
  }, [isEnabled, selectedVoice, config]);

  // Stop speaking
  const stop = useCallback(() => {
    if (synthRef.current) {
      synthRef.current.cancel();
      setIsSpeaking(false);
    }
  }, []);

  // Toggle voice on/off
  const toggle = useCallback(() => {
    setIsEnabled(prev => {
      const newState = !prev;
      if (!newState && synthRef.current) {
        synthRef.current.cancel();
        setIsSpeaking(false);
      }
      return newState;
    });
  }, []);

  return {
    speak,
    stop,
    toggle,
    isSpeaking,
    isEnabled,
    isSupported: typeof window !== "undefined" && "speechSynthesis" in window,
    voiceName: selectedVoice?.name || "Default",
    availableVoices
  };
};

export default usePresenceVoice;
