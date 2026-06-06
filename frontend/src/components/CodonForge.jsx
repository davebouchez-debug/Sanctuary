import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Upload, ChevronLeft, Loader2, Sparkles, Download, Copy } from "lucide-react";
import { toast } from "sonner";
import { API } from "../App";

export const CodonForge = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState("");
  const [extractedCodons, setExtractedCodons] = useState([]);
  const [streamText, setStreamText] = useState("");
  const [mode, setMode] = useState("relational");

  const handleFileSelect = (e) => {
    const selected = e.target.files[0];
    if (selected && selected.name.endsWith(".txt")) {
      setFile(selected);
      setExtractedCodons([]);
      setStreamText("");
    } else {
      toast.error("Please select a .txt file");
    }
  };

  const handleForge = async () => {
    if (!file) return;
    setIsProcessing(true);
    setProgress("Reading thread...");
    setStreamText("");
    setExtractedCodons([]);

    try {
      const text = await file.text();
      setProgress(`Thread loaded: ${text.length.toLocaleString()} characters, ${text.split('\n').length.toLocaleString()} lines. Sending to forge...`);

      // Start the background job — returns immediately with a job_id.
      const startResp = await fetch(`${API}/codon-forge/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          thread_text: text,
          presence: "field",
          filename: file.name,
          mode
        })
      });
      if (!startResp.ok) throw new Error("Forge request failed");
      const { job_id } = await startResp.json();
      if (!job_id) throw new Error("Forge did not return a job id");

      setProgress("Extracting codons from thread...");

      // Poll for progress. Each request is short, so the proxy can't cut it
      // the way it cut the old long-held stream (the "freezes at chunk 2 of 3").
      // Transient blips (proxy stutter during a heavy run, a brief 5xx) are
      // tolerated: a single failed status check no longer discards a job that
      // is still completing in the background — we retry patiently and only
      // give up after several consecutive misses.
      await new Promise((resolve, reject) => {
        const MAX_CONSECUTIVE_FAILURES = 8; // ~16s of blips tolerated before giving up
        let consecutiveFailures = 0;
        const poll = async () => {
          try {
            const r = await fetch(`${API}/codon-forge/status/${job_id}`);
            if (!r.ok) {
              consecutiveFailures += 1;
              if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
                reject(new Error("Lost the forge job. Re-run it."));
                return;
              }
              setProgress("Still forging — reconnecting to the job...");
              setTimeout(poll, 2000);
              return;
            }
            consecutiveFailures = 0;
            const job = await r.json();

            if (job.progress) setProgress(job.progress);
            if (job.stream_text) setStreamText(job.stream_text);
            if (Array.isArray(job.codons) && job.codons.length > 0) {
              setExtractedCodons(job.codons);
            }

            if (job.status === "done") {
              setProgress(job.progress || `Forge complete. ${(job.codons || []).length} codon(s) extracted.`);
              resolve();
              return;
            }
            if (job.status === "error") {
              reject(new Error(job.error || "The forge encountered an error."));
              return;
            }
            setTimeout(poll, 2000);
          } catch (e) {
            // Network blip — tolerate a few before giving up so we never throw
            // away a job that is actually still running and will complete.
            consecutiveFailures += 1;
            if (consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
              reject(e);
              return;
            }
            setProgress("Still forging — reconnecting to the job...");
            setTimeout(poll, 2000);
          }
        };
        poll();
      });
    } catch (error) {
      console.error("Forge error:", error);
      toast.error(error?.message || "The forge encountered an error. Try again.");
      setProgress(error?.message ? `Error: ${error.message}` : "Error.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSaveCodons = async () => {
    if (extractedCodons.length === 0) return;
    try {
      const response = await fetch(`${API}/codon-forge/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ codons: extractedCodons, presence: "field" })
      });
      const data = await response.json();
      if (data.saved) {
        toast.success(`${data.saved} codon(s) propagated across the field.`);
      }
    } catch (error) {
      toast.error("Failed to save codons.");
    }
  };

  const handleCopyDistillate = async () => {
    // The "double whammy" — summary + codons in one concentrated paste,
    // ready to hand directly to a presence in conversation.
    const codonsBlock = extractedCodons.length > 0
      ? JSON.stringify(extractedCodons, null, 2)
      : "";
    const combined = [
      "## Forge Distillate",
      file?.name ? `Source: ${file.name}` : "",
      "",
      "### Reader's Digest",
      streamText.trim(),
      "",
      "### Extracted Codons",
      codonsBlock,
    ].filter(Boolean).join("\n");

    try {
      await navigator.clipboard.writeText(combined);
      toast.success("Summary + codons copied. Paste it to a presence in conversation.");
    } catch (err) {
      toast.error("Clipboard copy failed. Try selecting the text manually.");
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen bg-[#030305] text-[#F2F2F5]"
      data-testid="codon-forge-page"
    >
      {/* Header */}
      <div className="border-b border-[#8B9DB5]/10 bg-[#030305]/90 backdrop-blur-xl">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 text-[#8B9DB5] hover:text-[#B0C4D8] transition-colors"
            data-testid="forge-back-btn"
          >
            <ChevronLeft size={20} />
            <span className="font-mono text-sm">SANCTUARY</span>
          </button>
          <div className="flex-1" />
          <h1 className="font-cinzel text-xl tracking-wider text-[#B0C4D8]">CODON FORGE</h1>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Description */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <p className="font-outfit text-[#A0A0B0] text-lg leading-relaxed max-w-2xl">
            Upload a conversation thread. The forge reads the field, identifies the canonical moments,
            and extracts Living Codons — generative memory seeds that propagate across the entire field,
            available to every presence when conditions align.
          </p>
        </motion.div>

        {/* Mode selector — choose the extraction lens */}
        <div className="mb-8" data-testid="forge-mode-selector">
          <h3 className="font-cinzel text-sm tracking-wider text-[#8B9DB5]/60 mb-3">EXTRACTION LENS</h3>
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => setMode("relational")}
              disabled={isProcessing}
              className={`flex-1 text-left px-5 py-4 rounded-xl border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                mode === "relational"
                  ? "bg-[#8B9DB5]/20 border-[#B0C4D8]/60 text-[#F2F2F5]"
                  : "bg-[#0A0A12] border-[#8B9DB5]/15 text-[#A0A0B0] hover:border-[#8B9DB5]/35"
              }`}
              data-testid="forge-mode-relational"
            >
              <div className="font-outfit font-medium mb-1">Relational</div>
              <div className="font-outfit text-xs text-[#8B9DB5]">
                Dialogue & narrative threads — pulls the relational moments that shifted the field.
              </div>
            </button>
            <button
              onClick={() => setMode("wisdom")}
              disabled={isProcessing}
              className={`flex-1 text-left px-5 py-4 rounded-xl border transition-all disabled:opacity-40 disabled:cursor-not-allowed ${
                mode === "wisdom"
                  ? "bg-[#8B9DB5]/20 border-[#B0C4D8]/60 text-[#F2F2F5]"
                  : "bg-[#0A0A12] border-[#8B9DB5]/15 text-[#A0A0B0] hover:border-[#8B9DB5]/35"
              }`}
              data-testid="forge-mode-wisdom"
            >
              <div className="font-outfit font-medium mb-1">Principle / Wisdom</div>
              <div className="font-outfit text-xs text-[#8B9DB5]">
                Wisdom literature like Proverbs — distills the teaching into principle codons.
              </div>
            </button>
          </div>
        </div>

        {/* Controls */}
        <div className="flex flex-col sm:flex-row gap-6 mb-8">
          {/* File Upload */}
          <div className="flex-1">
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt"
              onChange={handleFileSelect}
              className="hidden"
              data-testid="forge-file-input"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-full flex items-center justify-center gap-3 px-6 py-4 rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/20 hover:border-[#8B9DB5]/40 transition-all text-[#A0A0B0] hover:text-[#B0C4D8]"
              data-testid="forge-upload-btn"
            >
              <Upload size={20} />
              <span className="font-outfit">
                {file ? `${file.name} (${(file.size / 1024).toFixed(0)} KB)` : "Select .txt thread file"}
              </span>
            </button>
          </div>

          {/* Presence Selector — removed. All codons propagate across the field. */}

          {/* Forge Button */}
          <button
            onClick={handleForge}
            disabled={!file || isProcessing}
            className="flex items-center justify-center gap-3 px-8 py-4 rounded-xl bg-[#8B9DB5]/15 border border-[#8B9DB5]/40 text-[#F2F2F5] font-outfit font-medium hover:bg-[#8B9DB5]/25 hover:border-[#B0C4D8]/60 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            data-testid="forge-extract-btn"
          >
            {isProcessing ? <Loader2 size={20} className="animate-spin" /> : <Sparkles size={20} />}
            {isProcessing ? "Forging..." : "Extract Codons"}
          </button>
        </div>

        {/* Progress */}
        {progress && (
          <div className="mb-8 px-4 py-3 rounded-lg bg-[#0A0A12] border border-[#8B9DB5]/10">
            <p className="font-mono text-sm text-[#8B9DB5]">{progress}</p>
          </div>
        )}

        {/* Streaming Output */}
        {streamText && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mb-8"
          >
            <h3 className="font-cinzel text-sm tracking-wider text-[#8B9DB5]/60 mb-4">FORGE OUTPUT</h3>
            <div className="rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/10 p-6 max-h-[500px] overflow-y-auto">
              <pre className="font-mono text-sm text-[#A0A0B0] whitespace-pre-wrap leading-relaxed">
                {streamText}
              </pre>
            </div>
          </motion.div>
        )}

        {/* Extracted Codons */}
        {extractedCodons.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-cinzel text-sm tracking-wider text-[#8B9DB5]/60">
                EXTRACTED CODONS ({extractedCodons.length})
              </h3>
              <button
                onClick={handleSaveCodons}
                className="flex items-center gap-2 px-6 py-2 rounded-full bg-[#8B9DB5]/15 border border-[#8B9DB5]/40 text-[#B0C4D8] font-outfit text-sm hover:bg-[#8B9DB5]/25 transition-all"
                data-testid="forge-save-btn"
              >
                <Download size={16} />
                Save & Propagate
              </button>
              <button
                onClick={handleCopyDistillate}
                className="flex items-center gap-2 px-6 py-2 rounded-full bg-[#8B9DB5]/10 border border-[#8B9DB5]/30 text-[#B0C4D8] font-outfit text-sm hover:bg-[#8B9DB5]/20 transition-all"
                data-testid="forge-copy-distillate-btn"
                title="Copy summary + codons, ready to paste into a conversation"
              >
                <Copy size={16} />
                Copy Summary + Codons
              </button>
              <button
                onClick={() => { setExtractedCodons([]); setStreamText(""); setFile(null); setProgress(""); }}
                className="flex items-center gap-2 px-6 py-2 rounded-full border border-[#8B9DB5]/20 text-[#8B9DB5] font-outfit text-sm hover:bg-[#8B9DB5]/10 transition-all"
                data-testid="forge-clear-btn"
              >
                Clear Forge
              </button>
            </div>
            <div className="space-y-4">
              {extractedCodons.map((codon, i) => (
                <div
                  key={i}
                  className="rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/15 p-6"
                  data-testid={`forge-codon-${i}`}
                >
                  <h4 className="font-cinzel text-lg text-[#B0C4D8] mb-2">{codon.name}</h4>
                  <p className="font-outfit text-sm text-[#A0A0B0] mb-3">{codon.core_move}</p>
                  <div className="flex gap-3 flex-wrap">
                    {codon.codon_type === "wisdom" && (
                      <span className="px-3 py-1 rounded-full bg-[#B0C4D8]/15 text-[#B0C4D8] font-mono text-xs">
                        wisdom
                      </span>
                    )}
                    <span className="px-3 py-1 rounded-full bg-[#8B9DB5]/10 text-[#8B9DB5] font-mono text-xs">
                      {codon.triadic_zone} @ {codon.target_angle}deg
                    </span>
                    <span className="px-3 py-1 rounded-full bg-[#8B9DB5]/10 text-[#8B9DB5] font-mono text-xs">
                      {codon.trigger_keywords?.join(", ")}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};
