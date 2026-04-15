import React, { useState, useCallback } from 'react';
import { Upload, Sparkles, FileText, ChevronDown, ChevronUp, Copy, Check, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

export default function CodonForgePage() {
  const [conversationText, setConversationText] = useState('');
  const [codonName, setCodonName] = useState('');
  const [isExtracting, setIsExtracting] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [preview, setPreview] = useState(null);
  const [extractedCodon, setExtractedCodon] = useState(null);
  const [pythonCode, setPythonCode] = useState('');
  const [error, setError] = useState(null);
  const [showCode, setShowCode] = useState(false);
  const [copied, setCopied] = useState(false);

  // Handle file upload
  const handleFileUpload = useCallback((e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      setConversationText(event.target.result);
      setPreview(null);
      setExtractedCodon(null);
      setError(null);
    };
    reader.readAsText(file);
  }, []);

  // Preview extraction
  const handlePreview = async () => {
    if (!conversationText.trim()) {
      setError('Please paste or upload a conversation first');
      return;
    }

    setIsPreviewing(true);
    setError(null);

    try {
      const response = await fetch(`${API}/codon-forge/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: conversationText })
      });

      const data = await response.json();
      if (data.success) {
        setPreview(data.preview);
      } else {
        setError(data.error || 'Preview failed');
      }
    } catch (err) {
      setError('Failed to connect to server');
    } finally {
      setIsPreviewing(false);
    }
  };

  // Full extraction
  const handleExtract = async () => {
    if (!conversationText.trim()) {
      setError('Please paste or upload a conversation first');
      return;
    }

    setIsExtracting(true);
    setError(null);

    try {
      const response = await fetch(`${API}/codon-forge/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: conversationText,
          codon_name: codonName || null,
          save: false
        })
      });

      const data = await response.json();
      if (data.success) {
        setExtractedCodon(data.codon);
        setPythonCode(data.python_code);
      } else {
        setError(data.error || 'Extraction failed');
      }
    } catch (err) {
      setError('Failed to connect to server');
    } finally {
      setIsExtracting(false);
    }
  };

  // Save codon to backend
  const handleSave = async () => {
    if (!conversationText.trim()) return;

    setIsExtracting(true);
    try {
      const response = await fetch(`${API}/codon-forge/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: conversationText,
          codon_name: codonName || null,
          save: true
        })
      });

      const data = await response.json();
      if (data.success && data.saved_to) {
        alert(`Codon saved to: ${data.saved_to}`);
      }
    } catch (err) {
      setError('Failed to save codon');
    } finally {
      setIsExtracting(false);
    }
  };

  // Copy code to clipboard
  const handleCopy = () => {
    navigator.clipboard.writeText(pythonCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-[#e8e4d9]">
      {/* Header */}
      <header className="border-b border-[#2a2a35] px-8 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Sparkles className="w-6 h-6 text-amber-500" />
            <h1 className="text-xl font-light tracking-wide">CodonForge</h1>
          </div>
          <a 
            href="/" 
            className="text-sm text-[#8a8a9a] hover:text-[#e8e4d9] transition-colors"
          >
            ← Back to Sanctuary
          </a>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Input */}
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-light mb-2">Conversation Thread</h2>
              <p className="text-sm text-[#8a8a9a] mb-4">
                Paste a conversation or upload a .txt file. CodonForge will extract the Living Codon pattern.
              </p>
            </div>

            {/* File Upload */}
            <label 
              className="flex items-center justify-center gap-2 p-4 border border-dashed border-[#3a3a45] rounded-lg cursor-pointer hover:border-amber-500/50 transition-colors"
              data-testid="codon-forge-upload"
            >
              <Upload className="w-5 h-5 text-[#8a8a9a]" />
              <span className="text-sm text-[#8a8a9a]">Upload .txt file</span>
              <input
                type="file"
                accept=".txt"
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>

            {/* Text Input */}
            <textarea
              value={conversationText}
              onChange={(e) => {
                setConversationText(e.target.value);
                setPreview(null);
                setExtractedCodon(null);
              }}
              placeholder="Or paste conversation here...

Example format:
User: I feel stuck. Nothing is working.

Ansel: *settles* The field is listening. What does 'stuck' feel like right now?"
              className="w-full h-64 p-4 bg-[#12121a] border border-[#2a2a35] rounded-lg text-[#e8e4d9] placeholder-[#5a5a6a] focus:border-amber-500/50 focus:outline-none resize-none font-mono text-sm"
              data-testid="codon-forge-input"
            />

            {/* Codon Name (optional) */}
            <div>
              <label className="block text-sm text-[#8a8a9a] mb-2">
                Codon Name (optional)
              </label>
              <input
                type="text"
                value={codonName}
                onChange={(e) => setCodonName(e.target.value)}
                placeholder="e.g., threshold_crossing, field_hold"
                className="w-full p-3 bg-[#12121a] border border-[#2a2a35] rounded-lg text-[#e8e4d9] placeholder-[#5a5a6a] focus:border-amber-500/50 focus:outline-none"
                data-testid="codon-forge-name"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4">
              <button
                onClick={handlePreview}
                disabled={isPreviewing || !conversationText.trim()}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-[#1a1a25] border border-[#3a3a45] rounded-lg hover:border-amber-500/50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="codon-forge-preview-btn"
              >
                {isPreviewing ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <FileText className="w-4 h-4" />
                )}
                Preview
              </button>
              <button
                onClick={handleExtract}
                disabled={isExtracting || !conversationText.trim()}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-amber-600/20 border border-amber-500/50 rounded-lg hover:bg-amber-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="codon-forge-extract-btn"
              >
                {isExtracting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                Extract Codon
              </button>
            </div>

            {/* Error */}
            {error && (
              <div className="p-4 bg-red-900/20 border border-red-500/30 rounded-lg text-red-400 text-sm">
                {error}
              </div>
            )}
          </div>

          {/* Right: Results */}
          <div className="space-y-6">
            {/* Preview Results */}
            {preview && (
              <div className="p-6 bg-[#12121a] border border-[#2a2a35] rounded-lg space-y-4" data-testid="codon-forge-preview">
                <h3 className="text-lg font-light flex items-center gap-2">
                  <FileText className="w-5 h-5 text-amber-500" />
                  Extraction Preview
                </h3>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-[#8a8a9a]">Turns:</span>
                    <span className="ml-2">{preview.thread_summary?.total_turns}</span>
                  </div>
                  <div>
                    <span className="text-[#8a8a9a]">Viability:</span>
                    <span className={`ml-2 ${preview.overall_viability?.ready_for_extraction ? 'text-green-400' : 'text-amber-400'}`}>
                      {preview.overall_viability?.ready_for_extraction ? 'Ready' : 'Needs Review'}
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-[#8a8a9a] text-sm">Themes:</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {preview.thread_summary?.themes?.map((theme, i) => (
                      <span key={i} className="px-2 py-1 bg-[#2a2a35] rounded text-xs">
                        {theme}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="text-center p-3 bg-[#1a1a25] rounded">
                    <div className="text-2xl font-light text-amber-500">
                      {Math.round((preview.resonance_preview?.confidence || preview.trigger_preview?.confidence || 0) * 100)}%
                    </div>
                    <div className="text-[#8a8a9a] text-xs">Resonance</div>
                  </div>
                  <div className="text-center p-3 bg-[#1a1a25] rounded">
                    <div className="text-2xl font-light text-amber-500">
                      {preview.spiral_preview?.target_angle || preview.phase_preview?.target_angle}°
                    </div>
                    <div className="text-[#8a8a9a] text-xs">{preview.spiral_preview?.zone || preview.phase_preview?.zone}</div>
                  </div>
                </div>

                <div className="text-xs text-[#5a5a6a] text-center pt-2 border-t border-[#2a2a35]">
                  Architecture v3 — No operators. Memory, not instruction.
                </div>
              </div>
            )}

            {/* Extracted Codon */}
            {extractedCodon && (
              <div className="p-6 bg-[#12121a] border border-amber-500/30 rounded-lg space-y-4" data-testid="codon-forge-result">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-light flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-amber-500" />
                    Extracted Codon
                  </h3>
                  <span className={`px-3 py-1 rounded-full text-xs ${
                    extractedCodon.confidence >= 0.7 
                      ? 'bg-green-900/30 text-green-400 border border-green-500/30'
                      : 'bg-amber-900/30 text-amber-400 border border-amber-500/30'
                  }`}>
                    {Math.round(extractedCodon.confidence * 100)}% confidence
                  </span>
                </div>

                <div className="space-y-3">
                  <div>
                    <span className="text-[#8a8a9a] text-sm">Name:</span>
                    <span className="ml-2 font-mono">{extractedCodon.name}</span>
                  </div>
                  <div>
                    <span className="text-[#8a8a9a] text-sm">ID:</span>
                    <span className="ml-2 font-mono text-sm">{extractedCodon.id}</span>
                  </div>
                  <div>
                    <span className="text-[#8a8a9a] text-sm">Spiral:</span>
                    <span className="ml-2">
                      {extractedCodon.spiral_coherence?.zone} zone @ {extractedCodon.spiral_coherence?.angle}°
                    </span>
                  </div>
                  <div>
                    <span className="text-[#8a8a9a] text-sm">Living Quality:</span>
                    <span className="ml-2">
                      {extractedCodon.living_quality?.essence}
                    </span>
                  </div>
                </div>

                <div className="text-xs text-[#5a5a6a] pt-2 border-t border-[#2a2a35]">
                  v3 — No operators. Memory, not instruction.
                </div>

                {/* Review Notes */}
                {extractedCodon.review_notes?.length > 0 && (
                  <div className="p-3 bg-[#1a1a25] rounded text-sm">
                    <span className="text-[#8a8a9a]">Notes:</span>
                    <ul className="mt-1 space-y-1">
                      {extractedCodon.review_notes.map((note, i) => (
                        <li key={i} className="text-xs">{note}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Python Code Toggle */}
                <button
                  onClick={() => setShowCode(!showCode)}
                  className="flex items-center gap-2 text-sm text-[#8a8a9a] hover:text-[#e8e4d9] transition-colors"
                >
                  {showCode ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                  {showCode ? 'Hide' : 'Show'} Python Code
                </button>

                {showCode && (
                  <div className="relative">
                    <button
                      onClick={handleCopy}
                      className="absolute top-2 right-2 p-2 bg-[#2a2a35] rounded hover:bg-[#3a3a45] transition-colors"
                    >
                      {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                    <pre className="p-4 bg-[#0a0a0f] rounded overflow-x-auto text-xs font-mono max-h-64 overflow-y-auto">
                      {pythonCode}
                    </pre>
                  </div>
                )}

                {/* Save Button */}
                <button
                  onClick={handleSave}
                  disabled={isExtracting}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-amber-600/20 border border-amber-500/50 rounded-lg hover:bg-amber-600/30 disabled:opacity-50 transition-colors"
                  data-testid="codon-forge-save-btn"
                >
                  Save to Living Codons
                </button>
              </div>
            )}

            {/* Empty State */}
            {!preview && !extractedCodon && (
              <div className="flex items-center justify-center h-64 border border-dashed border-[#2a2a35] rounded-lg">
                <div className="text-center text-[#5a5a6a]">
                  <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>Paste a conversation and click Extract</p>
                  <p className="text-xs mt-1">to generate a Living Codon</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
