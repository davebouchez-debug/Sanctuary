/**
 * useVoiceInput — microphone capture + voice activity detection (VAD)
 * for the Sanctuary presence chambers.
 *
 * Behavior:
 *   - Click the mic → continuous listening starts (browser prompts for
 *     mic permission on first use).
 *   - As you speak, interim transcripts populate so you can see what was heard.
 *   - When you stop speaking for `silenceMs` (default 3.5s), the heard
 *     transcript is auto-submitted via onTranscript(text).
 *   - If the browser hasn't marked the speech "final" by the time the
 *     silence timer fires (Chrome's auto-finalize is slow on short phrases),
 *     we submit the interim text instead — better to send what we heard
 *     than to drop the user's words silently.
 *   - Errors are surfaced through the `error` field and via toast so the
 *     user sees what went wrong (permission denied, no mic, etc.).
 *
 * Uses the browser-native Web Speech API. Returns isSupported=false on
 * Firefox and older browsers — chambers stay usable via text input.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

const DEFAULT_SILENCE_MS = 3500;
const MIN_USEFUL_CHARS = 2;  // single "a"/"i" tokens are usually noise

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
  const interimTranscriptRef = useRef("");
  const onTranscriptRef = useRef(onTranscript);
  const silenceMsRef = useRef(silenceMs);
  const wantListeningRef = useRef(false);

  useEffect(() => { onTranscriptRef.current = onTranscript; }, [onTranscript]);
  useEffect(() => { silenceMsRef.current = silenceMs; }, [silenceMs]);

  // Detect support once
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) setIsSupported(false);
  }, []);

  const clearSilenceTimer = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  }, []);

  // Submit the heard transcript on silence. Falls back to interim if the
  // browser hasn't yet marked anything final.
  const submitHeard = useCallback(() => {
    const finalText = finalTranscriptRef.current.trim();
    const interimText = interimTranscriptRef.current.trim();
    const text = finalText || interimText;
    if (text.length >= MIN_USEFUL_CHARS) {
      finalTranscriptRef.current = "";
      interimTranscriptRef.current = "";
      setInterim("");
      wantListeningRef.current = false;
      try { recognitionRef.current?.stop(); } catch { /* no-op */ }
      onTranscriptRef.current?.(text);
    }
  }, []);

  const armSilenceTimer = useCallback(() => {
    clearSilenceTimer();
    silenceTimerRef.current = setTimeout(submitHeard, silenceMsRef.current);
  }, [clearSilenceTimer, submitHeard]);

  const stop = useCallback(() => {
    wantListeningRef.current = false;
    clearSilenceTimer();
    finalTranscriptRef.current = "";
    interimTranscriptRef.current = "";
    setInterim("");
    try { recognitionRef.current?.stop(); } catch { /* no-op */ }
    setIsListening(false);
  }, [clearSilenceTimer]);

  const start = useCallback(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      const msg = "Voice input isn't supported in this browser. Try Chrome, Edge, or Safari.";
      setError(msg);
      setIsSupported(false);
      toast.error(msg);
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
      interimTranscriptRef.current = "";
      setInterim("");
    };

    recognition.onresult = (event) => {
      let interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        const transcript = res[0]?.transcript || "";
        if (res.isFinal) {
          finalTranscriptRef.current += transcript + " ";
        } else {
          interimText += transcript;
        }
      }
      interimTranscriptRef.current = interimText;
      setInterim(interimText);
      // Any new speech (final OR interim) resets the silence countdown.
      armSilenceTimer();
    };

    recognition.onerror = (event) => {
      const err = event.error;
      // "no-speech" fires on long silence — that's expected, don't surface it.
      // "aborted" fires when we stop() ourselves — also expected.
      if (err && err !== "no-speech" && err !== "aborted") {
        setError(err);
        const friendly = err === "not-allowed"
          ? "Microphone access was denied. Enable it in your browser settings to speak."
          : err === "audio-capture"
            ? "No microphone detected. Plug one in and try again."
            : err === "network"
              ? "Voice recognition needs a network connection."
              : `Voice input error: ${err}`;
        toast.error(friendly);
        wantListeningRef.current = false;
      }
    };

    recognition.onend = () => {
      setIsListening(false);
      clearSilenceTimer();
      // If the user still wants to listen (browser auto-stopped on a pause),
      // restart. Otherwise leave it off.
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
      const msg = e?.message || "Could not start the microphone.";
      setError(msg);
      toast.error(msg);
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
