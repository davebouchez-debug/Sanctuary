/**
 * stopGlobalLegacyAudio — silence the legacy xAI raw-PCM audio context.
 *
 * Background: the legacy streaming endpoints (clarity/resonance/mirror) used
 * to emit `audio_raw` events containing raw PCM16 chunks from the xAI Voice
 * Agent. Chambers played those directly via a shared global AudioContext at
 * `window._sanctuaryAudioCtx`. That path is now retired in favor of
 * per-presence ElevenLabs sentence streaming through `usePresenceVoice`.
 *
 * Because each chamber's response now arrives with BOTH the new ElevenLabs
 * voice AND the legacy xAI voice still scheduled in the global context, the
 * user heard two voices on the same response (the "membrane bleed"). This
 * helper hard-stops the global context so nothing from a prior session's
 * xAI stream can leak into the next chamber.
 *
 * Call this on chamber mount (and ideally on every send) until every chamber
 * stops scheduling audio_raw entirely.
 */
export const stopGlobalLegacyAudio = () => {
  try {
    if (typeof window === "undefined") return;
    const ctx = window._sanctuaryAudioCtx;
    if (ctx) {
      // Closing the context aborts every still-scheduled BufferSource.
      try { ctx.close(); } catch { /* already closed */ }
      window._sanctuaryAudioCtx = null;
    }
    window._sanctuaryNextPlayTime = 0;
  } catch {
    /* defensive — context shutdown should never throw upstream */
  }
};
