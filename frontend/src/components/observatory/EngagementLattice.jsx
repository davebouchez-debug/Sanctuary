import React, { useCallback, useEffect, useState } from "react";
import axios from "axios";
import { API } from "../../App";
import { LatticeGrid } from "./LatticeGrid";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { LedgerStatus } from "./LedgerStatus";

const REFRESH_MS = 60000;
const SCOPES = [
  { key: "S1", label: "Same conversation" },
  { key: "S2", label: "Same presence · any visitor" },
  { key: "S3", label: "Same presence · same visitor" },
];

const Chip = ({ active, onClick, children, testid }) => (
  <button onClick={onClick} data-testid={testid}
    className={`rounded-full border px-3 py-1 font-mono text-[11px] tracking-wider transition-colors ${active ? "border-emerald-400/50 bg-emerald-400/10 text-emerald-300" : "border-white/10 text-zinc-400 hover:text-zinc-200"}`}>
    {children}
  </button>
);

export const EngagementLattice = () => {
  const [status, setStatus] = useState(null);
  const [presence, setPresence] = useState("");
  const [scope, setScope] = useState("S2");
  const [visitor, setVisitor] = useState("");
  const [visitors, setVisitors] = useState([]);
  const [before, setBefore] = useState(null);
  const [showText, setShowText] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [entryId, setEntryId] = useState(null);

  const loadStatus = useCallback(async () => {
    const { data: s } = await axios.get(`${API}/observatory/status`);
    setStatus(s);
    setPresence((p) => p || s.presences?.[0]?.presence || "");
  }, []);

  const loadLattice = useCallback(async () => {
    if (!presence) return;
    setLoading(true);
    try {
      const params = { presence, scope, limit: 24 };
      if (scope === "S3" && visitor) params.visitor = visitor;
      if (before != null) params.before_ordinal = before;
      const { data: d } = await axios.get(`${API}/observatory/lattice`, { params });
      setData(d);
      if (scope === "S3" && !visitor && d.visitor) setVisitor(d.visitor);
    } finally {
      setLoading(false);
    }
  }, [presence, scope, visitor, before]);

  useEffect(() => { loadStatus(); const t = setInterval(loadStatus, REFRESH_MS); return () => clearInterval(t); }, [loadStatus]);
  useEffect(() => { loadLattice(); }, [loadLattice]);
  useEffect(() => {
    if (before != null) return undefined;
    const t = setInterval(loadLattice, REFRESH_MS);
    return () => clearInterval(t);
  }, [loadLattice, before]);
  useEffect(() => {
    if (!presence) return;
    axios.get(`${API}/observatory/visitors`, { params: { presence } }).then(({ data: v }) => setVisitors(v.visitors || []));
  }, [presence]);

  const pickPresence = (p) => { setPresence(p); setVisitor(""); setBefore(null); };
  const pickScope = (s) => { setScope(s); setBefore(null); };

  return (
    <div className="space-y-5" data-testid="engagement-lattice">
      <LedgerStatus status={status} />
      <div className="rounded-2xl border border-white/10 bg-[#0A0C12]/80 p-4 backdrop-blur-xl">
        <div className="flex flex-wrap gap-2" data-testid="lattice-presence-picker">
          {(status?.presences || []).map((p) => (
            <Chip key={p.presence} active={presence === p.presence} onClick={() => pickPresence(p.presence)}
              testid={`lattice-presence-${p.presence}`}>{p.presence} {p.entries}</Chip>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2" data-testid="lattice-scope-picker">
          <span className="mr-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">compare with</span>
          {SCOPES.map((s) => (
            <Chip key={s.key} active={scope === s.key} onClick={() => pickScope(s.key)} testid={`lattice-scope-${s.key}`}>
              {s.key} · {s.label}
            </Chip>
          ))}
          {scope === "S3" && (
            <select value={visitor} onChange={(e) => { setVisitor(e.target.value); setBefore(null); }}
              data-testid="lattice-visitor-select"
              className="rounded-full border border-white/10 bg-black/40 px-3 py-1 font-mono text-[11px] text-zinc-300">
              {visitors.map((v) => <option key={v.visitor} value={v.visitor}>visitor {String(v.visitor).slice(0, 8)} · {v.entries}</option>)}
            </select>
          )}
          <label className="ml-auto flex items-center gap-2 font-mono text-[11px] text-zinc-400">
            <input type="checkbox" checked={showText} onChange={(e) => setShowText(e.target.checked)} data-testid="lattice-text-toggle" />
            text-only layer
          </label>
        </div>
      </div>
      <LatticeGrid data={data} loading={loading} showText={showText} onOpen={setEntryId}
        onOlder={() => setBefore(data?.first_ordinal)} onLatest={() => setBefore(null)} paged={before != null} />
      <EvidenceDrawer entryId={entryId} onClose={() => setEntryId(null)} />
    </div>
  );
};
