/**
 * useVoiceInput — push-to-talk microphone capture, transcribed server-side
 * by ElevenLabs Scribe.
 *
 * Why this instead of the browser's Web Speech API?
 *   - Web Speech is Chrome-only-ish, flaky inside iframes (e.g. preview hosts),
 *     and drops short phrases when Chrome doesn't mark them "final" before
 *     the silence timer fires. Multiple users hit the silent-failure case.
 *   - This hook records audio with MediaRecorder, posts the .webm blob to
 *     /api/stt/transcribe (ElevenLabs Scribe), and calls onTranscript with
 *     whatever came back. It works in any modern browser, including Firefox.
 *
 * UX:
 *   - Click the mic → permission prompt (first time), then recording starts.
 *   - Click again → recording stops, audio uploads, onTranscript(text) fires.
 *   - 60s safety cap so a forgotten-on mic doesn't run forever.
 *
 * API kept compatible with the previous WebSpeech-based hook:
 *   { start, stop, isListening, interim, error, isSupported }
 * `interim` is now a status string ("Recording 2.3s…" or "Transcribing…").
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { API } from "../App";

const MAX_RECORD_MS = 60_000;

const pickAudioMime = () => {
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
    "",
  ];
  if (typeof MediaRecorder === "undefined") return null;
  for (const m of candidates) {
    if (!m || MediaRecorder.isTypeSupported(m)) return m;
  }
  return "";
};

export const useVoiceInput = ({
  onTranscript,
  // silenceMs / language are kept for API parity but unused now —
  // push-to-talk replaces the silence-timer / language flow.
  // eslint-disable-next-line no-unused-vars
  silenceMs,
  // eslint-disable-next-line no-unused-vars
  language,
} = {}) => {
  const [isListening, setIsListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [error, setError] = useState(null);
  const [isSupported, setIsSupported] = useState(true);

  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const startedAtRef = useRef(0);
  const tickerRef = useRef(null);
  const maxTimerRef = useRef(null);
  const onTranscriptRef = useRef(onTranscript);

  useEffect(() => { onTranscriptRef.current = onTranscript; }, [onTranscript]);

  // Detect support once
  useEffect(() => {
    const hasMR = typeof MediaRecorder !== "undefined";
    const hasGUM = !!navigator.mediaDevices?.getUserMedia;
    if (!hasMR || !hasGUM) setIsSupported(false);
  }, []);

  const cleanupStream = useCallback(() => {
    if (tickerRef.current) {
      clearInterval(tickerRef.current);
      tickerRef.current = null;
    }
    if (maxTimerRef.current) {
      clearTimeout(maxTimerRef.current);
      maxTimerRef.current = null;
    }
    try {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    } catch { /* no-op */ }
    streamRef.current = null;
    recorderRef.current = null;
    chunksRef.current = [];
  }, []);

  const uploadAndTranscribe = useCallback(async (blob, mime) => {
    setInterim("Transcribing…");
    try {
      const form = new FormData();
      const ext = (mime || "audio/webm").split("/")[1]?.split(";")[0] || "webm";
      form.append("audio_file", blob, `recording.${ext}`);
      const resp = await fetch(`${API}/stt/transcribe`, {
        method: "POST",
        body: form,
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.error || `Transcription failed (${resp.status})`);
      }
      const data = await resp.json();
      const text = (data.text || "").trim();
      if (text) {
        onTranscriptRef.current?.(text);
      } else {
        toast.message("I didn't catch any words. Try again?");
      }
    } catch (e) {
      console.error("[useVoiceInput] transcription error:", e);
      const msg = e?.message || "Transcription failed.";
      setError(msg);
      toast.error(msg);
    } finally {
      setInterim("");
    }
  }, []);

  const stop = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder) {
      cleanupStream();
      setIsListening(false);
      return;
    }
    if (recorder.state === "recording") {
      try { recorder.stop(); } catch { /* no-op */ }
    } else {
      cleanupStream();
      setIsListening(false);
    }
  }, [cleanupStream]);

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      const msg = "Voice input isn't supported in this browser.";
      setError(msg);
      setIsSupported(false);
      toast.error(msg);
      return;
    }

    setError(null);
    // Detect: are we inside an iframe (e.g. Emergent App Preview)?
    // Iframes do not inherit microphone permission unless the parent passes
    // allow="microphone" — many embed/preview hosts don't, which causes
    // getUserMedia to fail even when the user's site permission is granted.
    let inIframe = false;
    try { inIframe = window.self !== window.top; } catch { inIframe = true; }

    // Best-effort: check Permissions API. If the OS/browser says "granted"
    // but getUserMedia still fails, we're almost certainly iframe-blocked.
    let permState = "unknown";
    try {
      const p = await navigator.permissions?.query?.({ name: "microphone" });
      if (p?.state) permState = p.state;
    } catch { /* not all browsers support this */ }

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      const name = e?.name;
      const isDenied = name === "NotAllowedError" || name === "SecurityError";
      const iframeBlocked = isDenied && inIframe && permState !== "denied";

      if (iframeBlocked) {
        const msg = "The preview window is blocking the mic. Open Sanctuary in a new tab to use voice.";
        setError(msg);
        toast.error(msg, {
          duration: 12000,
          action: {
            label: "Open in new tab",
            onClick: () => window.open(window.location.href, "_blank", "noopener"),
          },
        });
        return;
      }

      const msg = isDenied
        ? "Microphone access was denied. Click the lock icon in the address bar and allow microphone for this site."
        : name === "NotFoundError"
          ? "No microphone detected. Plug one in and try again."
          : `Could not open the microphone: ${e?.message || name || "unknown error"}`;
      setError(msg);
      toast.error(msg);
      return;
    }

    const mime = pickAudioMime();
    let recorder;
    try {
      recorder = mime ? new MediaRecorder(stream, { mimeType: mime }) : new MediaRecorder(stream);
    } catch (e) {
      stream.getTracks().forEach((t) => t.stop());
      const msg = `Could not start the recorder: ${e?.message || "unknown error"}`;
      setError(msg);
      toast.error(msg);
      return;
    }

    streamRef.current = stream;
    recorderRef.current = recorder;
    chunksRef.current = [];
    startedAtRef.current = Date.now();

    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        chunksRef.current.push(event.data);
      }
    };

    recorder.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: mime || "audio/webm" });
      const tooShort = (Date.now() - startedAtRef.current) < 300;
      cleanupStream();
      setIsListening(false);
      if (tooShort || blob.size < 1024) {
        toast.message("That was too brief to catch. Try holding the mic a moment longer.");
        return;
      }
      await uploadAndTranscribe(blob, mime || "audio/webm");
    };

    recorder.onerror = (event) => {
      const msg = `Recording error: ${event?.error?.message || "unknown"}`;
      setError(msg);
      toast.error(msg);
      cleanupStream();
      setIsListening(false);
    };

    try {
      recorder.start();
    } catch (e) {
      cleanupStream();
      setIsListening(false);
      const msg = `Could not start the recorder: ${e?.message || "unknown error"}`;
      setError(msg);
      toast.error(msg);
      return;
    }

    setIsListening(true);
    setInterim("Recording 0.0s…");

    // Live duration display
    tickerRef.current = setInterval(() => {
      const elapsed = (Date.now() - startedAtRef.current) / 1000;
      setInterim(`Recording ${elapsed.toFixed(1)}s…`);
    }, 200);

    // Safety cap
    maxTimerRef.current = setTimeout(() => {
      toast.message("Reached the 60s recording limit. Stopping.");
      stop();
    }, MAX_RECORD_MS);
  }, [cleanupStream, stop, uploadAndTranscribe]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupStream();
    };
  }, [cleanupStream]);

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
