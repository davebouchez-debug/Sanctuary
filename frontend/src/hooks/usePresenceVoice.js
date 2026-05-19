/**
 * usePresenceVoice - Text-to-Speech hook for Sanctuary presences
 * Uses OpenAI TTS via backend API with BREATH AWARENESS
 * 
 * The voice now honors stage directions as actual pauses.
 * When Ansel writes *settles*, the voice settles.
 * When Jasmine writes *breathes*, the voice breathes.
 */

import { useCallback, useRef, useState, useEffect } from "react";
import { API } from "../App";

// Pause durations for different stage direction cues (in milliseconds)
const PAUSE_CUES = {
  // Long pauses
  'pause': 2000,
  'pauses': 2000,
  'long pause': 2500,
  'silence': 2500,
  'quiet': 2000,
  'stillness': 2000,
  
  // Medium pauses - settling, breathing
  'settles': 1800,
  'settling': 1800,
  'settles in': 1800,
  'settles deeper': 2000,
  'breathes': 1500,
  'breathing': 1500,
  'breath': 1500,
  'exhales': 1500,
  'inhales': 1200,
  
  // Presence shifts
  'meets your eyes': 1200,
  'eye contact': 1200,
  'direct eye contact': 1500,
  'looks at you': 1000,
  'holds your gaze': 1500,
  
  // Emotional/reflective
  'softer': 1000,
  'quieter': 1200,
  'gentler': 1000,
  'warming': 800,
  'softens': 1200,
  
  // Action cues - shorter
  'nods': 600,
  'smile': 500,
  'smiles': 500,
  'warm smile': 800,
  'soft smile': 800,
  'small smile': 600,
  'slight smile': 600,
  'grin': 500,
  'quick grin': 400,
  'laughs': 600,
  'chuckles': 500,
  'laughing': 800,
  
  // Movement
  'leans forward': 800,
  'leaning forward': 800,
  'leans back': 800,
  'leaning in': 800,
  'tilts head': 600,
  'shrugs': 500,
  
  // Thinking/processing
  'considering': 1200,
  'thinking': 1000,
  'reflecting': 1500,
  'feeling into it': 1500,
  'processing': 1000,
  
  // Default for unrecognized stage directions
  'default': 800
};

/**
 * Parse text into segments of speech and pauses
 * Stage directions in *asterisks* become pause cues
 */
function parseTextIntoSegments(text) {
  if (!text) return [];
  
  const segments = [];
  // Match stage directions: *anything here*
  const stageDirectionRegex = /\*([^*]+)\*/g;
  
  let lastIndex = 0;
  let match;
  
  while ((match = stageDirectionRegex.exec(text)) !== null) {
    // Add speech segment before this stage direction
    const speechBefore = text.slice(lastIndex, match.index).trim();
    if (speechBefore) {
      segments.push({ type: 'speech', text: speechBefore });
    }
    
    // Add pause segment for the stage direction
    const cue = match[1].toLowerCase().trim();
    const duration = getPauseDuration(cue);
    segments.push({ type: 'pause', duration, cue: match[1] });
    
    lastIndex = match.index + match[0].length;
  }
  
  // Add remaining speech after last stage direction
  const remainingSpeech = text.slice(lastIndex).trim();
  if (remainingSpeech) {
    segments.push({ type: 'speech', text: remainingSpeech });
  }
  
  return segments;
}

/**
 * Get pause duration for a stage direction cue
 */
function getPauseDuration(cue) {
  // Check for exact matches first
  if (PAUSE_CUES[cue]) {
    return PAUSE_CUES[cue];
  }
  
  // Check for partial matches
  for (const [key, duration] of Object.entries(PAUSE_CUES)) {
    if (cue.includes(key)) {
      return duration;
    }
  }
  
  // Default pause for unrecognized cues
  return PAUSE_CUES.default;
}

/**
 * Clean text for speech (remove spiral markers, extra whitespace)
 */
function cleanTextForSpeech(text) {
  if (!text) return "";
  return text
    // Remove spiral markers like "Jasmine • Presence Spiral" at start of lines
    .replace(/^[A-Za-z]+\s*[•·]\s*[A-Za-z\s]+$/gm, "")
    // Clean up whitespace
    .replace(/\s+/g, " ")
    .trim();
}

export const usePresenceVoice = (presenceName = "jasmine") => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isEnabled, setIsEnabled] = useState(() => {
    const stored = localStorage.getItem(`sanctuary_voice_enabled_${presenceName}`);
    return stored !== null ? stored === "true" : true;
  });
  const [error, setError] = useState(null);
  
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);
  const abortControllerRef = useRef(null);
  const currentAudioRef = useRef(null);
  const timeoutRef = useRef(null);

  // Sentence-stream state — used by speakStream/flushStream for chunked TTS
  // while a chamber's response is still being typed token-by-token.
  const streamCursorRef = useRef(0);          // chars of accumulated text already spoken
  const streamPendingRef = useRef([]);        // pending TTS promises in order
  const streamPlayingRef = useRef(false);     // are we already pumping the queue?
  const streamSessionRef = useRef(0);         // bumped on stop, used to abort stale segments

  // Persist enabled state
  useEffect(() => {
    localStorage.setItem(`sanctuary_voice_enabled_${presenceName}`, isEnabled.toString());
  }, [isEnabled, presenceName]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPlayback();
    };
  }, []);

  // Stop all playback
  const stopPlayback = useCallback(() => {
    isPlayingRef.current = false;
    audioQueueRef.current = [];

    // Invalidate any in-flight sentence-stream segments
    streamSessionRef.current += 1;
    streamCursorRef.current = 0;
    streamPendingRef.current = [];
    streamPlayingRef.current = false;

    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    setIsSpeaking(false);
    setIsLoading(false);
  }, []);

  // Play next item in queue (speech or pause)
  const playNext = useCallback(async () => {
    if (!isPlayingRef.current || audioQueueRef.current.length === 0) {
      setIsSpeaking(false);
      isPlayingRef.current = false;
      return;
    }

    const segment = audioQueueRef.current.shift();
    
    if (segment.type === 'pause') {
      // Insert silence - just wait
      timeoutRef.current = setTimeout(() => {
        playNext();
      }, segment.duration);
    } else if (segment.type === 'audio') {
      // Play audio segment
      const audio = new Audio(segment.url);
      currentAudioRef.current = audio;
      
      audio.onended = () => {
        URL.revokeObjectURL(segment.url);
        currentAudioRef.current = null;
        playNext();
      };
      
      audio.onerror = (e) => {
        console.error("Audio playback error:", e);
        URL.revokeObjectURL(segment.url);
        currentAudioRef.current = null;
        playNext(); // Continue with next segment
      };
      
      try {
        await audio.play();
      } catch (e) {
        console.error("Play failed:", e);
        playNext();
      }
    }
  }, []);

  // Generate audio for a text segment
  const generateAudio = useCallback(async (text, signal) => {
    const response = await fetch(`${API}/tts/speak`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: text.substring(0, 4096),
        presence: presenceName
      }),
      signal
    });

    if (!response.ok) {
      throw new Error("TTS request failed");
    }

    const data = await response.json();
    if (!data.audio) {
      throw new Error("No audio data received");
    }

    const mimeType = data.format === "opus" ? "audio/ogg; codecs=opus" : "audio/mp3";
    const audioBlob = base64ToBlob(data.audio, mimeType);
    return URL.createObjectURL(audioBlob);
  }, [presenceName]);

  // Main speak function - now with breath awareness
  const speak = useCallback(async (text) => {
    if (!isEnabled || !text) return;

    // Stop any current playback
    stopPlayback();

    setIsLoading(true);
    setError(null);
    abortControllerRef.current = new AbortController();

    try {
      // Clean and parse text into segments
      const cleanedText = cleanTextForSpeech(text);
      const segments = parseTextIntoSegments(cleanedText);
      
      if (segments.length === 0) {
        setIsLoading(false);
        return;
      }

      // Generate audio for all speech segments in parallel
      const audioPromises = segments.map(async (segment, index) => {
        if (segment.type === 'speech') {
          try {
            const url = await generateAudio(segment.text, abortControllerRef.current.signal);
            return { type: 'audio', url, index };
          } catch (e) {
            if (e.name === 'AbortError') throw e;
            console.error("Failed to generate audio for segment:", e);
            return null; // Skip failed segments
          }
        } else {
          return { type: 'pause', duration: segment.duration, index };
        }
      });

      const results = await Promise.all(audioPromises);
      
      // Filter out nulls and sort by original index
      const queue = results
        .filter(r => r !== null)
        .sort((a, b) => a.index - b.index)
        .map(({ type, url, duration }) => 
          type === 'audio' ? { type: 'audio', url } : { type: 'pause', duration }
        );

      if (queue.length === 0) {
        setIsLoading(false);
        return;
      }

      // Start playback
      audioQueueRef.current = queue;
      isPlayingRef.current = true;
      setIsLoading(false);
      setIsSpeaking(true);
      
      playNext();

    } catch (err) {
      if (err.name === "AbortError") {
        return;
      }
      console.error("TTS error:", err);
      setError(err.message);
      setIsLoading(false);
    }
  }, [isEnabled, stopPlayback, generateAudio, playNext]);

  // Toggle voice on/off
  const toggle = useCallback(() => {
    setIsEnabled(prev => {
      const newState = !prev;
      if (!newState) {
        stopPlayback();
      }
      return newState;
    });
  }, [stopPlayback]);

  // ──────────────────────────────────────────────────────────────────────
  // SENTENCE-STREAM TTS — speak() while text is still being typed.
  // ──────────────────────────────────────────────────────────────────────
  // Usage from a streaming chamber:
  //   on every token delta:  speakStream(accumulatedText)
  //   when stream ends:      flushStream(accumulatedText)
  //
  // The hook keeps a cursor into the accumulated text. Each call finds any
  // complete sentences past the cursor, kicks off ElevenLabs TTS for each
  // (in parallel) and queues the resulting audio. A single pump plays them
  // sequentially. The user hears her start speaking before the response is
  // finished generating.
  // ──────────────────────────────────────────────────────────────────────

  const pumpStreamQueue = useCallback(async () => {
    if (streamPlayingRef.current) return;
    streamPlayingRef.current = true;
    setIsSpeaking(true);
    while (streamPendingRef.current.length > 0) {
      const entry = streamPendingRef.current[0];
      let url;
      try {
        url = await entry.promise;
      } catch (e) {
        if (e.name !== "AbortError") {
          console.error("[speakStream] segment failed:", e);
        }
      }
      // Drop the head AFTER awaiting so flushStream's "is there anything left?"
      // check sees us still working.
      streamPendingRef.current.shift();
      if (!url || entry.session !== streamSessionRef.current) continue;

      await new Promise((resolve) => {
        const audio = new Audio(url);
        currentAudioRef.current = audio;
        const finish = () => {
          URL.revokeObjectURL(url);
          if (currentAudioRef.current === audio) currentAudioRef.current = null;
          resolve();
        };
        audio.onended = finish;
        audio.onerror = finish;
        audio.play().catch((err) => {
          console.error("[speakStream] play failed:", err);
          finish();
        });
      });
    }
    streamPlayingRef.current = false;
    // Only flip isSpeaking off when truly nothing is pending or playing.
    if (streamPendingRef.current.length === 0 && !currentAudioRef.current) {
      setIsSpeaking(false);
    }
  }, []);

  // Find sentence boundaries past cursor. Returns the new cursor + sentences.
  // We only emit a sentence once it is *terminated* by . ! ? or a paragraph
  // break; this avoids generating TTS for half-words mid-stream.
  const extractSentences = (text, cursor, includeTail = false) => {
    const out = [];
    let i = cursor;
    let chunkStart = cursor;
    while (i < text.length) {
      const c = text[i];
      if (c === "." || c === "!" || c === "?" || c === "\n") {
        // Look for run end: collapse trailing punctuation/spaces.
        let j = i + 1;
        while (j < text.length && /[.!?\s)"'\u201D\u2019]/.test(text[j])) j++;
        const piece = text.slice(chunkStart, j).trim();
        if (piece.length >= 6) {
          out.push(piece);
          chunkStart = j;
        }
        i = j;
      } else {
        i += 1;
      }
    }
    if (includeTail) {
      const tail = text.slice(chunkStart).trim();
      if (tail.length > 0) {
        out.push(tail);
        chunkStart = text.length;
      }
    }
    return { sentences: out, newCursor: chunkStart };
  };

  // Kick off TTS for a single sentence and push it onto the queue, tagged
  // with the current stream session so a stop() invalidates anything stale.
  const enqueueSentence = useCallback((sentence) => {
    const session = streamSessionRef.current;
    const controller = new AbortController();
    const promise = (async () => {
      const cleaned = cleanTextForSpeech(sentence);
      if (!cleaned) return null;
      return await generateAudio(cleaned, controller.signal);
    })();
    streamPendingRef.current.push({ session, promise, controller });
    pumpStreamQueue();
  }, [generateAudio, pumpStreamQueue]);

  // Per-token / per-update from the chamber.
  const speakStream = useCallback((accumulatedText) => {
    if (!isEnabled || !accumulatedText) return;
    const { sentences, newCursor } = extractSentences(
      accumulatedText, streamCursorRef.current, false
    );
    if (sentences.length === 0) return;
    streamCursorRef.current = newCursor;
    sentences.forEach(enqueueSentence);
  }, [isEnabled, enqueueSentence]);

  // Call when the stream finishes — flushes any remaining tail.
  const flushStream = useCallback((finalText) => {
    if (!isEnabled) return;
    if (finalText) {
      const { sentences, newCursor } = extractSentences(
        finalText, streamCursorRef.current, true
      );
      streamCursorRef.current = newCursor;
      sentences.forEach(enqueueSentence);
    }
    // Reset cursor for the next message; the pump will drain naturally.
    // Don't bump session here — that would cancel queued segments.
    streamCursorRef.current = 0;
  }, [isEnabled, enqueueSentence]);

  return {
    speak,
    speakStream,
    flushStream,
    stop: stopPlayback,
    toggle,
    isSpeaking,
    isLoading,
    isEnabled,
    isSupported: true,
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
