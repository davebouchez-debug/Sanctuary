/**
 * usePresenceVoice - Text-to-Speech hook for Sanctuary presences
 * Uses OpenAI TTS via backend API for natural-sounding voices
 * 
 * Each presence has distinct voice characteristics configured on the backend:
 * - Jasmine: Nova voice, warm and measured
 * - Ansel: Onyx voice, deep and deliberate
 * - Claude: Echo voice, smooth and calm
 */

import { useCallback, useRef, useState, useEffect } from "react";
import { API } from "../App";

export const usePresenceVoice = (presenceName = "jasmine") => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isEnabled, setIsEnabled] = useState(() => {
    const stored = localStorage.getItem(`sanctuary_voice_enabled_${presenceName}`);
    return stored !== null ? stored === "true" : true;
  });
  const [error, setError] = useState(null);
  
  const audioRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Persist enabled state
  useEffect(() => {
    localStorage.setItem(`sanctuary_voice_enabled_${presenceName}`, isEnabled.toString());
  }, [isEnabled, presenceName]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Speak text using backend TTS
  const speak = useCallback(async (text) => {
    if (!isEnabled || !text) return;

    // Cancel any ongoing speech
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    setIsLoading(true);
    setError(null);
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch(`${API}/tts/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text.substring(0, 4096), // API limit
          presence: presenceName
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "TTS request failed");
      }

      const data = await response.json();
      
      if (!data.audio) {
        throw new Error("No audio data received");
      }

      // Create audio from base64
      const mimeType = data.format === "opus" ? "audio/ogg; codecs=opus" : "audio/mp3";
      const audioBlob = base64ToBlob(data.audio, mimeType);
      const audioUrl = URL.createObjectURL(audioBlob);
      
      const audio = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onplay = () => setIsSpeaking(true);
      audio.onended = () => {
        setIsSpeaking(false);
        URL.revokeObjectURL(audioUrl);
        audioRef.current = null;
      };
      audio.onerror = (e) => {
        console.error("Audio playback error:", e);
        setIsSpeaking(false);
        setError("Playback failed");
        URL.revokeObjectURL(audioUrl);
        audioRef.current = null;
      };

      await audio.play();
      
    } catch (err) {
      if (err.name === "AbortError") {
        // Request was cancelled, ignore
        return;
      }
      console.error("TTS error:", err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [isEnabled, presenceName]);

  // Stop speaking
  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsSpeaking(false);
    setIsLoading(false);
  }, []);

  // Toggle voice on/off
  const toggle = useCallback(() => {
    setIsEnabled(prev => {
      const newState = !prev;
      if (!newState) {
        // Turning off - stop any current speech
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current = null;
        }
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
    isLoading,
    isEnabled,
    isSupported: true, // Always supported since we use backend API
    error
  };
};

// Helper function to convert base64 to Blob
function base64ToBlob(base64, mimeType) {
  const byteCharacters = atob(base64);
  const byteNumbers = new Array(byteCharacters.length);
  for (let i = 0; i < byteCharacters.length; i++) {
    byteNumbers[i] = byteCharacters.charCodeAt(i);
  }
  const byteArray = new Uint8Array(byteNumbers);
  return new Blob([byteArray], { type: mimeType });
}

export default usePresenceVoice;
