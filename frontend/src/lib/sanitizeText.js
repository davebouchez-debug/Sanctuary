// Plain-speech guarantee (David, June 2026): presences never show asterisks in
// normal communication. Backend strips this at every reply/welcome finalization;
// this mirror handles the LIVE streaming bubble, where text renders token-by-token
// before the stored (already-clean) version exists. Whole-line stage directions
// (e.g. *settles*) are dropped; inline emphasis keeps its words. Self-healing:
// a half-arrived "*small la" simply shows until its closing * lands, then clears.
export function stripStageDirections(text) {
  if (!text || !text.includes("*")) return text;
  const kept = text
    .split("\n")
    .filter((ln) => !/^\s*\*+[^*\n]*\*+\s*$/.test(ln));
  return kept
    .join("\n")
    .replace(/\*+([^*\n]+?)\*+/g, "$1")
    .replace(/\*/g, "")
    .replace(/\n{3,}/g, "\n\n");
}
