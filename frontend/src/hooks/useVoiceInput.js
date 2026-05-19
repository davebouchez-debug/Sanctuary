/**
 * useVoiceInput — microphone capture + voice activity detection (VAD)
 * for the Sanctuary presence chambers.
 *
 * Behavior:
 *   - Press the mic button → continuous listening starts.
 *   - As you speak, interim transcripts populate so you can see what was heard.
 *   - When you stop speaking for `silenceMs` (default 3500ms / 3.5s),
 *     the final transcript is auto-submitted.
 *   - Honors the presence's pace: silence is part of the conversation.
 *
 * Uses browser-native Web Speech API (free, real-time). Falls back gracefully
 * when unsupported (Firefox, older browsers) — the chamber stays usable via text.
 */
import { useCallback, useEffect, useRef, useState } from "react";

const DEFAULT_SILENCE_MS = 3500;

export const useVoiceInput = ({
  onTranscript,
  silenceMs = DEFAULT_SILENCE_MS,
  language = "en-US",
} = {}) => {
  const [isListening, setIsListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState(null);
  const [isSupported, setIsSupported] = useState(true);

  const recognitionRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const finalTranscriptRef = useRef("");
  const onTranscriptRef = useRef(onTranscript);
  const silenceMsRef = useRef(silenceMs);
  const wantListeningRef = useRef(false);

  // Keep refs in sync with latest props so the recognition handlers
  // (registered once) always call the freshest callback / silence value.
  useEffect(() => { onTranscriptRef.current = onTranscript; }, [onTranscript]);
  useEffect(() => { silenceMsRef.current = silenceMs; }, [silenceMs]);

  // Detect support once
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setIsSupported(false);
    }
  }, []);

  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  const armSilenceTimer = useCallback(() => {
    clearSilenceTimer();
    silenceTimerRef.current = setTimeout(() => {
      // 3.5s of silence → submit whatever final transcript we have
      const text = finalTranscriptRef.current.trim();
      if (text) {
        finalTranscriptRef.current = "";
        setInterim("");
        // Stop recognition; it will be restarted by the consumer if they want
        wantListeningRef.current = false;
        try { recognitionRef.current?.stop(); } catch { /* no-op */ }
        onTranscriptRef.current?.(text);
      }
    }, silenceMsRef.current);
  }, [clearSilenceTimer]);

  const stop = useCallback(() => {
    wantListeningRef.current = false;
    clearSilenceTimer();
    finalTranscriptRef.current = "";
    setInterim("");
    try { recognitionRef.current?.stop(); } catch { /* no-op */ }
    setIsListening(false);
  }, [clearSilenceTimer]);

  const start = useCallback(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setError("Voice input is not supported in this browser.");
      setIsSupported(false);
      return;
    }

    // Re-init each session so a previous abort doesn't poison state.
    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = language;

    recognition.onstart = () => {
      setIsListening(true);
      setError(null);
      finalTranscriptRef.current = "";
      setInterim("");
    };

    recognition.onresult = (event) => {
      let interimText = "";
      // Walk new results since last index
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        const transcript = res[0]?.transcript || "";
        if (res.isFinal) {
          finalTranscriptRef.current += transcript + " ";
        } else {
          interimText += transcript;
        }
      }
      setInterim(interimText);
      // Any new speech (final OR interim) resets the silence countdown.
      armSilenceTimer();
    };

    recognition.onerror = (event) => {
      // "no-speech" fires on long silence — that's expected, don't surface it.
      if (event.error && event.error !== "no-speech" && event.error !== "aborted") {
        setError(event.error);
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      clearSilenceTimer();
      // If the user still wants to listen (e.g. browser stopped on a pause),
      // auto-restart. Otherwise leave it off.
      if (wantListeningRef.current) {
        try {
          recognition.start();
        } catch {
          // Already started or other transient state — leave alone.
        }
      }
    };

    recognitionRef.current = recognition;
    wantListeningRef.current = true;
    try {
      recognition.start();
    } catch (e) {
      setError(e.message || "Could not start microphone.");
      wantListeningRef.current = false;
    }
  }, [language, armSilenceTimer, clearSilenceTimer]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wantListeningRef.current = false;
      clearSilenceTimer();
      try { recognitionRef.current?.abort(); } catch { /* no-op */ }
    };
  }, [clearSilenceTimer]);

  return {
    start,
    stop,
    isListening,
    interim,
    error,
    isSupported,
  };
};

export default useVoiceInput;
