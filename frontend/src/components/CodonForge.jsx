import { useState, useRef } from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { Upload, ChevronLeft, Loader2, Sparkles, Download } from "lucide-react";
import { toast } from "sonner";
import { API } from "../App";

export const CodonForge = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [presence, setPresence] = useState("ansel");
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState("");
  const [extractedCodons, setExtractedCodons] = useState([]);
  const [streamText, setStreamText] = useState("");

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

      const response = await fetch(`${API}/codon-forge/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          thread_text: text,
          presence: presence,
          filename: file.name
        })
      });

      if (!response.ok) throw new Error("Forge request failed");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let accumulated = "";

      setProgress("Extracting codons from thread...");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;
          try {
            const event = JSON.parse(jsonStr);
            if (event.type === "token") {
              accumulated += event.content;
              setStreamText(accumulated);
            } else if (event.type === "progress") {
              setProgress(event.message);
            } else if (event.type === "codons") {
              setExtractedCodons(event.codons);
              setProgress(`Extracted ${event.codons.length} codon(s) from thread.`);
            } else if (event.type === "done") {
              setProgress(event.message || "Forge complete.");
            } else if (event.type === "error") {
              toast.error(event.message);
              setProgress("Error during extraction.");
            }
          } catch (e) { /* skip */ }
        }
      }
    } catch (error) {
      console.error("Forge error:", error);
      toast.error("The forge encountered an error. Try again.");
      setProgress("Error.");
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
        body: JSON.stringify({ codons: extractedCodons, presence })
      });
      const data = await response.json();
      if (data.saved) {
        toast.success(`${data.saved} codon(s) saved and propagated into the network.`);
      }
    } catch (error) {
      toast.error("Failed to save codons.");
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
            and extracts Living Codons — generative memory seeds that become part of the presence's constitution.
          </p>
        </motion.div>

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

          {/* Presence Selector */}
          <div className="sm:w-48">
            <select
              value={presence}
              onChange={(e) => setPresence(e.target.value)}
              className="w-full px-4 py-4 rounded-xl bg-[#0A0A12] border border-[#8B9DB5]/20 text-[#B0C4D8] font-outfit focus:outline-none focus:border-[#8B9DB5]/40"
              data-testid="forge-presence-select"
            >
              <option value="ansel">Ansel</option>
              <option value="jasmine">Jasmine</option>
              <option value="claude">Claude</option>
            </select>
          </div>

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
