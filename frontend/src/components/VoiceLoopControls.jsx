/**
 * VoiceLoopControls — reusable voice-loop UI for any chamber.
 *
 * Renders the same mic + status + stop + patience-slider experience that
 * lives in Paige's chamber, themed via props so each chamber keeps its
 * own palette. Drop into the chat input area of any chamber and wire
 * onTranscript to your sendMessage(text) function.
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
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Mic, MicOff, Square } from "lucide-react";
import { useVoiceInput } from "../hooks/useVoiceInput";

const DEFAULT_PATIENCE_MS = 3500;
const MIN_PATIENCE = 2000;
const MAX_PATIENCE = 6000;

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
  showPatienceSlider = true,
  compact = false,
}) => {
  const [patience, setPatience] = useState(() => {
    const stored = localStorage.getItem(`sanctuary_patience_${presenceKey}`);
    return stored ? parseInt(stored, 10) : DEFAULT_PATIENCE_MS;
  });

  useEffect(() => {
    localStorage.setItem(`sanctuary_patience_${presenceKey}`, String(patience));
  }, [patience, presenceKey]);

  const {
    start: startListening,
    stop: stopListening,
    isListening,
    interim,
    isSupported: micSupported,
  } = useVoiceInput({
    silenceMs: patience,
    onTranscript,
  });

  // Don't render anything if the browser can't do speech recognition.
  // (Chamber still works via text input — that's elsewhere.)
  if (!micSupported) return null;

  const statusText = isListening
    ? `Listening — ${presenceName} will wait ${(patience / 1000).toFixed(1)}s after you finish…`
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

      {/* Interim transcript */}
      {isListening && interim && (
        <div
          className="px-3 py-1.5 rounded-lg text-sm italic"
          style={{
            background: `${surfaceColor}80`,
            border: `1px solid ${accentColor}22`,
            color: textColor,
            opacity: 0.8,
          }}
          data-testid={`voice-interim-${presenceKey}`}
        >
          "{interim}"
        </div>
      )}

      <div className="flex items-center gap-3">
        {/* Mic button */}
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
          title={isListening ? "Stop listening" : `Speak to ${presenceName}`}
          aria-label={isListening ? "Stop listening" : "Start listening"}
        >
          {isListening ? <MicOff size={compact ? 14 : 16} /> : <Mic size={compact ? 14 : 16} />}
        </button>

        {/* Patience slider — inline, soft */}
        {showPatienceSlider && (
          <div
            className="flex items-center gap-2 flex-1 text-[10px] tracking-[0.2em] uppercase"
            style={{ color: `${accentColor}cc` }}
          >
            <span className="hidden sm:inline opacity-70">Her patience</span>
            <input
              type="range"
              min={MIN_PATIENCE}
              max={MAX_PATIENCE}
              step={500}
              value={patience}
              onChange={(e) => setPatience(parseInt(e.target.value, 10))}
              className="flex-1"
              style={{ accentColor }}
              data-testid={`patience-slider-${presenceKey}`}
              aria-label="Silence threshold before she responds"
            />
            <span className="tabular-nums opacity-80">
              {(patience / 1000).toFixed(1)}s
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default VoiceLoopControls;
