import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Upload, ChevronLeft, Loader2, Sparkles, Download, Copy, X } from "lucide-react";
import { toast } from "sonner";
import { API } from "../App";

export const CodonForge = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState("");
  const [phrases, setPhrases] = useState([]);
  const [saved, setSaved] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [mode, setMode] = useState("relational");

  const handleFileSelect = (e) => {
    const selected = e.target.files[0];
    if (selected && selected.name.endsWith(".txt")) {
      setFile(selected);
      setPhrases([]);
      setSaved(false);
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
    setPhrases([]);
    setSaved(false);

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

      setProgress("Distilling phrases from the text...");

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
            if (Array.isArray(job.phrases) && job.phrases.length > 0) {
              setPhrases(job.phrases);
            }

            if (job.status === "done") {
              setProgress(job.progress || `Forge complete. ${(job.phrases || []).length} phrase(s) distilled.`);
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
    if (phrases.length === 0) return;
    try {
      const response = await fetch(`${API}/codon-forge/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phrases, filename: file?.name || "thread.txt", mode })
      });
      if (!response.ok) throw new Error();
      const data = await response.json();
      setSaved(true);
      toast.success(`${data.saved} phrase(s) added to the field${data.skipped ? ` · ${data.skipped} already there` : ""}.`);
    } catch (error) {
      toast.error("Failed to save phrases.");
    }
  };

  const handleCopyDistillate = async () => {
    // The "double whammy" — summary + codons in one concentrated paste,
    // ready to hand directly to a presence in conversation.
    const codonsBlock = phrases.map(p => `- ${p}`).join("\n");
    const combined = [
      "## Forge Distillate",
      file?.name ? `Source: ${file.name}` : "",
      "",
      "### Reader's Digest",
      streamText.trim(),
      "",
      "### Field Phrases",
      codonsBlock,
    ].filter(Boolean).join("\n");

    try {
      await navigator.clipboard.writeText(combined);
      toast.success("Summary + phrases copied. Paste it to a presence in conversation.");
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
            Upload a conversation thread or a wisdom text. The forge distills what came true in it into
            essence phrases and adds them to the living field, where every presence draws on them
            whenever a moment carries the same meaning.
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
                Dialogue & narrative threads — distills what came true between the people in it.
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
                Wisdom literature like Proverbs — distills each teaching into a phrase.
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

          

          {/* Forge Button */}
          <button
            onClick={handleForge}
            disabled={!file || isProcessing}
            className="flex items-center justify-center gap-3 px-8 py-4 rounded-xl bg-[#8B9DB5]/15 border border-[#8B9DB5]/40 text-[#F2F2F5] font-outfit font-medium hover:bg-[#8B9DB5]/25 hover:border-[#B0C4D8]/60 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            data-testid="forge-extract-btn"
          >
            {isProcessing ? <Loader2 size={20} className="animate-spin" /> : <Sparkles size={20} />}
            {isProcessing ? "Forging..." : "Distill Phrases"}
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
            <h3 className="font-cinzel text-sm tracking-wider text-[#8B9DB5]/60 mb-4">DIGEST</h3>
            <div className="rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/10 p-6 max-h-[500px] overflow-y-auto">
              <p className="font-outfit text-sm text-[#A0A0B0] whitespace-pre-wrap leading-relaxed" data-testid="forge-digest">
                {streamText}
              </p>
            </div>
          </motion.div>
        )}

        {/* Extracted Codons */}
        {phrases.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-cinzel text-sm tracking-wider text-[#8B9DB5]/60">
                PHRASES ({phrases.length})
              </h3>
              <button
                onClick={handleSaveCodons}
                disabled={saved || isProcessing}
                className="disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 px-6 py-2 rounded-full bg-[#8B9DB5]/15 border border-[#8B9DB5]/40 text-[#B0C4D8] font-outfit text-sm hover:bg-[#8B9DB5]/25 transition-all"
                data-testid="forge-save-btn"
              >
                <Download size={16} />
                {saved ? "Added to the field" : "Add to the field"}
              </button>
              <button
                onClick={handleCopyDistillate}
                className="flex items-center gap-2 px-6 py-2 rounded-full bg-[#8B9DB5]/10 border border-[#8B9DB5]/30 text-[#B0C4D8] font-outfit text-sm hover:bg-[#8B9DB5]/20 transition-all"
                data-testid="forge-copy-distillate-btn"
                title="Copy summary + phrases, ready to paste into a conversation"
              >
                <Copy size={16} />
                Copy Summary + Phrases
              </button>
              <button
                onClick={() => { setPhrases([]); setStreamText(""); setFile(null); setProgress(""); setSaved(false); }}
                className="flex items-center gap-2 px-6 py-2 rounded-full border border-[#8B9DB5]/20 text-[#8B9DB5] font-outfit text-sm hover:bg-[#8B9DB5]/10 transition-all"
                data-testid="forge-clear-btn"
              >
                Clear Forge
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {phrases.map((p, i) => (
                <div
                  key={p}
                  className="flex items-start justify-between gap-3 rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/15 px-5 py-4"
                  data-testid={`forge-phrase-${i}`}
                >
                  <p className="font-cinzel text-base text-[#B0C4D8] leading-snug">{p}</p>
                  {!saved && (
                    <button
                      onClick={() => setPhrases(ps => ps.filter(x => x !== p))}
                      className="text-[#6E6E7A] hover:text-[#B0C4D8] transition-colors"
                      title="Leave this one out"
                      data-testid={`forge-phrase-remove-${i}`}
                    >
                      <X size={16} />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};
