/**
 * VoiceLoopControls — reusable push-to-talk UI for any chamber.
 *
 * Click the mic → recording starts. Click again → recording stops, audio
 * uploads to /api/stt/transcribe (ElevenLabs Scribe), transcript fires
 * onTranscript(text). Status pill shows live duration + transcription state.
 *
 *   <VoiceLoopControls
 *     presenceKey="jasmine"
 *     presenceName="Jasmine"
 *     disabled={!sessionId || isLoading}
 *     isSpeaking={isSpeaking}
 *     voiceLoading={voiceLoading}
 *     isProcessing={isLoading}
 *     onStopSpeaking={stopSpeaking}
 *     onTranscript={(text) => sendMessage(text)}
 *     accentColor="#8070c0"
 *     surfaceColor="#12122a"
 *     textColor="#e0e0f0"
 *   />
 */
import { motion } from "framer-motion";
import { ExternalLink, Mic, MicOff, Square } from "lucide-react";
import { useVoiceInput } from "../hooks/useVoiceInput";

// Detect once: are we inside an iframe (Emergent App Preview, embed, etc.)?
// Iframes typically don't inherit microphone permission, so we offer an
// "open in new tab" escape hatch when voice fails.
const IS_IFRAME = (() => {
  try { return window.self !== window.top; } catch { return true; }
})();

export const VoiceLoopControls = ({
  presenceKey,
  presenceName = "She",
  disabled = false,
  isSpeaking = false,
  voiceLoading = false,
  isProcessing = false,
  onStopSpeaking,
  onTranscript,
  accentColor = "#8B9DB5",
  surfaceColor = "#12122a",
  textColor = "#e0e0f0",
  compact = false,
}) => {
  const {
    start: startListening,
    stop: stopListening,
    isListening,
    interim,
    error: micError,
    isSupported: micSupported,
  } = useVoiceInput({ onTranscript });

  // If the browser can't do MediaRecorder + getUserMedia, hide the mic UI.
  // (The chamber still works via text input.)
  if (!micSupported) return null;

  const statusText = isListening
    ? (interim || "Recording…")
    : interim                          // "Transcribing…" between stop and onTranscript
      ? interim
      : isProcessing
        ? `${presenceName} is hearing you…`
        : voiceLoading
          ? `${presenceName} is finding her voice…`
          : isSpeaking
            ? `${presenceName} is speaking…`
            : "";

  const showStatus = !!statusText;

  return (
    <div className="flex flex-col gap-2 w-full">
      {/* Status pill */}
      {showStatus && (
        <div
          className="flex items-center justify-between gap-3 px-3 py-1.5 rounded-lg text-[10px] tracking-[0.2em] uppercase"
          style={{
            background: `${surfaceColor}80`,
            border: `1px solid ${accentColor}33`,
            color: accentColor,
          }}
          data-testid={`voice-status-${presenceKey}`}
        >
          <motion.span
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 1.6, repeat: Infinity }}
            className="flex-1 truncate"
          >
            {statusText}
          </motion.span>
          {isSpeaking && onStopSpeaking && (
            <button
              onClick={onStopSpeaking}
              className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] tracking-widest uppercase transition-opacity hover:opacity-90"
              style={{ background: accentColor, color: surfaceColor }}
              data-testid={`stop-speaking-${presenceKey}`}
              title={`Stop ${presenceName} speaking`}
            >
              <Square size={9} />
              Stop her
            </button>
          )}
        </div>
      )}

      <div className="flex items-center gap-3">
        {/* Mic button — push-to-talk */}
        <button
          onClick={() => (isListening ? stopListening() : startListening())}
          disabled={disabled}
          className="flex items-center justify-center rounded-lg transition-all disabled:opacity-40 hover:opacity-90"
          style={{
            background: isListening ? accentColor : `${accentColor}22`,
            color: isListening ? surfaceColor : accentColor,
            border: `1px solid ${accentColor}55`,
            padding: compact ? "8px 10px" : "10px 12px",
          }}
          data-testid={`mic-${presenceKey}`}
          title={isListening
            ? "Click to stop and send"
            : `Speak to ${presenceName} (click to start, click again to send)`}
          aria-label={isListening ? "Stop recording and send" : "Start recording"}
        >
          {isListening ? <MicOff size={compact ? 14 : 16} /> : <Mic size={compact ? 14 : 16} />}
        </button>

        {/* Helper text — tells the user what to expect */}
        <span
          className="text-[10px] tracking-[0.2em] uppercase opacity-70"
          style={{ color: `${accentColor}cc` }}
        >
          {isListening ? "Click mic again to send" : `Click to speak to ${presenceName}`}
        </span>

        {/* Escape hatch — surface a persistent "open in new tab" button once
            the mic has failed inside an iframe. The Emergent App Preview frame
            (and similar embeds) don't pass microphone permission to the inner
            document, so getUserMedia fails even when the browser has granted
            site access. Opening the app in a top-level tab fixes it. */}
        {IS_IFRAME && micError && !isListening && (
          <button
            onClick={() => window.open(window.location.href, "_blank", "noopener")}
            className="flex items-center gap-1 ml-auto px-2 py-1 rounded-md text-[9px] tracking-widest uppercase transition-opacity hover:opacity-90"
            style={{
              background: `${accentColor}22`,
              border: `1px solid ${accentColor}66`,
              color: accentColor,
            }}
            data-testid={`open-standalone-${presenceKey}`}
            title="The preview frame blocks the mic. Open Sanctuary in a new tab where voice works."
          >
            <ExternalLink size={10} />
            Open in new tab
          </button>
        )}
      </div>
    </div>
  );
};

export default VoiceLoopControls;
