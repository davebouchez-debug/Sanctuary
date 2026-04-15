/**
 * usePresenceVoice - Text-to-Speech hook for Sanctuary presences
 * 
 * Now supports TWO TTS engines:
 * - OpenAI TTS (default for Jasmine) - fast, clear
 * - Grok TTS (for Ansel) - emotionally intelligent, codon-aware
 * 
 * The voice honors stage directions as actual pauses.
 * When Ansel writes *settles*, the voice settles.
 * When Jasmine writes *breathes*, the voice breathes.
 * 
 * Updated: April 15, 2026 - Added Grok TTS with Living Codon integration
 */

import { useCallback, useRef, useState, useEffect } from "react";
import { API } from "../App";

// TTS Engine selection by presence
const TTS_ENGINE_MAP = {
  jasmine: "openai",
  ansel: "grok",
  claude: "grok"  // Claude uses Grok for emotional intelligence
};

// TTS Mode - streaming for lower latency, batch for reliability
const TTS_MODE = {
  jasmine: "batch",   // OpenAI doesn't have streaming TTS via xAI
  ansel: "stream",    // Use streaming for Ansel (Grok)
  claude: "stream"    // Use streaming for Claude (Grok)
};

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

/**
 * Streaming Audio Player - Collects MP3 chunks and plays them
 * Uses a simple approach: collect all chunks, then play as single audio
 * (True gapless MP3 streaming requires MSE which has browser limitations)
 */
class StreamingAudioPlayer {
  constructor() {
    this.chunks = [];
    this.isPlaying = false;
    this.audio = null;
    this.onEnd = null;
  }

  init() {
    this.chunks = [];
    this.isPlaying = true;
  }

  addChunk(base64Audio) {
    if (!this.isPlaying) return;
    
    try {
      // Decode base64 to bytes and store
      const binaryString = atob(base64Audio);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      this.chunks.push(bytes);
    } catch (e) {
      console.error("Chunk decode error:", e);
    }
  }

  async playCollected() {
    if (this.chunks.length === 0) return;
    
    // Combine all chunks into single array
    const totalLength = this.chunks.reduce((acc, chunk) => acc + chunk.length, 0);
    const combined = new Uint8Array(totalLength);
    let offset = 0;
    for (const chunk of this.chunks) {
      combined.set(chunk, offset);
      offset += chunk.length;
    }
    
    // Create blob and play
    const blob = new Blob([combined], { type: 'audio/mp3' });
    const url = URL.createObjectURL(blob);
    
    return new Promise((resolve, reject) => {
      this.audio = new Audio(url);
      this.audio.onended = () => {
        URL.revokeObjectURL(url);
        this.audio = null;
        resolve();
      };
      this.audio.onerror = (e) => {
        URL.revokeObjectURL(url);
        this.audio = null;
        reject(e);
      };
      this.audio.play().catch(reject);
    });
  }

  stop() {
    this.isPlaying = false;
    this.chunks = [];
    if (this.audio) {
      this.audio.pause();
      this.audio = null;
    }
  }

  async waitForCompletion() {
    // Playback is triggered after all chunks received
    // This is a no-op since we play after collecting
  }
}

export const usePresenceVoice = (presenceName = "jasmine", options = {}) => {
  const { activeCodons = [], voiceMod = {} } = options;
  
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isEnabled, setIsEnabled] = useState(() => {
    const stored = localStorage.getItem(`sanctuary_voice_enabled_${presenceName}`);
    return stored !== null ? stored === "true" : true;
  });
  const [error, setError] = useState(null);
  const [ttsEngine, setTtsEngine] = useState(TTS_ENGINE_MAP[presenceName] || "openai");
  
  const audioQueueRef = useRef([]);
  const isPlayingRef = useRef(false);
  const abortControllerRef = useRef(null);
  const currentAudioRef = useRef(null);
  const timeoutRef = useRef(null);
  const activeCodonsRef = useRef(activeCodons);
  const voiceModRef = useRef(voiceMod);
  
  // Update refs when options change
  useEffect(() => {
    activeCodonsRef.current = activeCodons;
    voiceModRef.current = voiceMod;
  }, [activeCodons, voiceMod]);

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

  // Generate audio for a text segment - uses either OpenAI or Grok
  const generateAudio = useCallback(async (text, signal) => {
    const engine = TTS_ENGINE_MAP[presenceName] || "openai";
    
    let response;
    if (engine === "grok") {
      // Use Grok TTS with Living Codon awareness
      response = await fetch(`${API}/tts/grok`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text.substring(0, 4096),
          presence: presenceName,
          active_codons: activeCodonsRef.current,
          voice_mod: voiceModRef.current
        }),
        signal
      });
    } else {
      // Use OpenAI TTS (original)
      response = await fetch(`${API}/tts/speak`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: text.substring(0, 4096),
          presence: presenceName
        }),
        signal
      });
    }

    if (!response.ok) {
      throw new Error(`TTS request failed: ${response.status}`);
    }

    const data = await response.json();
    if (!data.audio) {
      throw new Error("No audio data received");
    }

    // Grok returns MP3, OpenAI returns opus
    const mimeType = data.format === "opus" ? "audio/ogg; codecs=opus" : "audio/mp3";
    const audioBlob = base64ToBlob(data.audio, mimeType);
    return URL.createObjectURL(audioBlob);
  }, [presenceName]);

  // Main speak function - now with breath awareness and codon-aware voice
  const speak = useCallback(async (text, speakOptions = {}) => {
    if (!isEnabled || !text) return;

    // Update refs with any passed options
    if (speakOptions.activeCodons) {
      activeCodonsRef.current = speakOptions.activeCodons;
    }
    if (speakOptions.voiceMod) {
      voiceModRef.current = speakOptions.voiceMod;
    }

    // Stop any current playback
    stopPlayback();

    setIsLoading(true);
    setError(null);
    abortControllerRef.current = new AbortController();

    // Check if we should use streaming (Grok presences)
    const useStreaming = TTS_MODE[presenceName] === "stream";

    try {
      // Clean and parse text into segments
      const cleanedText = cleanTextForSpeech(text);
      const segments = parseTextIntoSegments(cleanedText);
      
      if (segments.length === 0) {
        setIsLoading(false);
        return;
      }

      if (useStreaming) {
        // STREAMING MODE - Use SSE for real-time audio
        await speakStreaming(cleanedText, segments);
      } else {
        // BATCH MODE - Original behavior for OpenAI TTS
        await speakBatch(segments);
      }

    } catch (err) {
      if (err.name === "AbortError") {
        return;
      }
      console.error("TTS error:", err);
      setError(err.message);
      setIsLoading(false);
      setIsSpeaking(false);
    }
  }, [isEnabled, stopPlayback, presenceName]);

  // Streaming TTS via Server-Sent Events
  const speakStreaming = useCallback(async (fullText, segments) => {
    const streamPlayer = new StreamingAudioPlayer();
    
    try {
      setIsSpeaking(true);
      setIsLoading(false);
      
      // Process segments with stage directions as pauses
      for (const segment of segments) {
        if (!isPlayingRef.current) break;
        
        if (segment.type === 'pause') {
          // Insert pause between speech segments
          await new Promise(resolve => setTimeout(resolve, segment.duration));
        } else if (segment.type === 'speech') {
          // Stream this speech segment
          streamPlayer.init();
          
          const response = await fetch(`${API}/tts/grok/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              text: segment.text,
              presence: presenceName,
              active_codons: activeCodonsRef.current,
              voice_mod: voiceModRef.current
            }),
            signal: abortControllerRef.current.signal
          });

          if (!response.ok) {
            console.error("Streaming TTS failed:", response.status);
            // Fall back to batch mode for this segment
            const url = await generateAudio(segment.text, abortControllerRef.current.signal);
            if (url) {
              const audio = new Audio(url);
              await new Promise((resolve, reject) => {
                audio.onended = resolve;
                audio.onerror = reject;
                audio.play();
              });
              URL.revokeObjectURL(url);
            }
            continue;
          }

          // Read SSE stream and collect chunks
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                try {
                  const data = JSON.parse(line.slice(6));
                  
                  if (data.type === "audio.delta" && data.audio) {
                    streamPlayer.addChunk(data.audio);
                  } else if (data.type === "error") {
                    console.error("Streaming error:", data.message);
                  }
                } catch (e) {
                  // Ignore parse errors
                }
              }
            }
          }
          
          // Play the collected audio
          try {
            await streamPlayer.playCollected();
          } catch (e) {
            console.error("Audio playback error:", e);
          }
        }
      }
      
    } finally {
      streamPlayer.stop();
      setIsSpeaking(false);
    }
  }, [presenceName, generateAudio]);

  // Batch TTS (original behavior)
  const speakBatch = useCallback(async (segments) => {
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
  }, [generateAudio, playNext]);

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

  return {
    speak,
    stop: stopPlayback,
    toggle,
    isSpeaking,
    isLoading,
    isEnabled,
    isSupported: true,
    error,
    ttsEngine: TTS_ENGINE_MAP[presenceName] || "openai"
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
