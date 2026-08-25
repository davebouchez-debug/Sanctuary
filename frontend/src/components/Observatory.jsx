import React, { useEffect, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { API } from "../App";
import {
  Activity, ArrowLeft, RefreshCw, Hash, Layers, Compass, Radio, X, Clock, Cpu,
} from "lucide-react";

const POLL_MS = 4000;

const zoneColor = (branch) => {
  if (!branch) return "text-zinc-400";
  if (branch.startsWith("keyword")) return "text-emerald-300";
  if (branch.startsWith("phase")) return "text-sky-300";
  return "text-amber-300";
};

const fmtTime = (iso) => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return iso;
  }
};

const Stat = ({ icon: Icon, label, value }) => (
  <div className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900/60 px-4 py-3">
    <Icon className="h-4 w-4 text-zinc-500" />
    <div>
      <div className="text-[11px] uppercase tracking-widest text-zinc-500">{label}</div>
      <div className="text-lg font-medium text-zinc-100" data-testid={`stat-${label}`}>{value}</div>
    </div>
  </div>
);

export default function Observatory() {
  const [stats, setStats] = useState(null);
  const [turns, setTurns] = useState([]);
  const [presenceFilter, setPresenceFilter] = useState("");
  const [live, setLive] = useState(true);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [pulse, setPulse] = useState(false);
  const lastTopId = useRef(null);

  const load = useCallback(async () => {
    try {
      const [s, t] = await Promise.all([
        axios.get(`${API}/provenance/stats`),
        axios.get(`${API}/provenance/turns`, { params: { limit: 60, presence: presenceFilter || undefined } }),
      ]);
      setStats(s.data);
      setTurns(t.data.turns || []);
      const topId = t.data.turns?.[0]?.provenance_id;
      if (topId && lastTopId.current && topId !== lastTopId.current) {
        setPulse(true);
        setTimeout(() => setPulse(false), 900);
      }
      lastTopId.current = topId;
    } catch (e) {
      // observation is best-effort; never blocks the view
    }
  }, [presenceFilter]);

  useEffect(() => {
    load();
    if (!live) return;
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, [load, live]);

  const openDetail = async (row) => {
    setSelected(row);
    setDetail(null);
    try {
      const r = await axios.get(`${API}/provenance/turn/${row.provenance_id}`);
      setDetail(r.data);
    } catch (e) {
      setDetail({ error: "Could not load record." });
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-200" data-testid="observatory-page">
      <div className="mx-auto max-w-7xl px-6 py-8">
        {/* Header */}
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <Link to="/" className="mb-3 inline-flex items-center gap-2 text-sm text-zinc-500 hover:text-zinc-300" data-testid="observatory-back">
              <ArrowLeft className="h-4 w-4" /> Sanctuary
            </Link>
            <h1 className="flex items-center gap-3 text-3xl font-light tracking-tight text-zinc-100">
              <Radio className="h-7 w-7 text-emerald-400" />
              The Observatory
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-zinc-500">
              A read-only window onto the exact model-visible context of every generated turn.
              It watches — it never touches, decides, or feeds back. Live capture, as it happens.
            </p>
          </div>
          <button
            onClick={() => setLive((v) => !v)}
            data-testid="observatory-live-toggle"
            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-colors ${
              live ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-zinc-700 text-zinc-400"
            }`}
          >
            <span className={`h-2 w-2 rounded-full ${live ? "bg-emerald-400 animate-pulse" : "bg-zinc-600"}`} />
            {live ? "Live" : "Paused"}
          </button>
        </div>

        {/* Stats */}
        {stats && (
          <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat icon={Activity} label="Turns Captured" value={stats.total} />
            <Stat icon={Layers} label="Presences" value={stats.per_presence?.length ?? 0} />
            <Stat icon={Clock} label="Last Capture" value={fmtTime(stats.latest_timestamp)} />
            <Stat icon={RefreshCw} label="Refresh" value={live ? "4s" : "off"} />
          </div>
        )}

        {/* Presence filter chips */}
        <div className="mb-4 flex flex-wrap gap-2">
          <button
            onClick={() => setPresenceFilter("")}
            data-testid="filter-all"
            className={`rounded-full px-3 py-1 text-xs transition-colors ${presenceFilter === "" ? "bg-zinc-200 text-zinc-900" : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"}`}
          >
            all
          </button>
          {stats?.per_presence?.map((p) => (
            <button
              key={p.presence}
              onClick={() => setPresenceFilter(p.presence)}
              data-testid={`filter-${p.presence}`}
              className={`rounded-full px-3 py-1 text-xs transition-colors ${presenceFilter === p.presence ? "bg-zinc-200 text-zinc-900" : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"}`}
            >
              {p.presence} <span className="opacity-60">{p.count}</span>
            </button>
          ))}
        </div>

        {/* Live feed */}
        <div className={`overflow-hidden rounded-xl border transition-colors ${pulse ? "border-emerald-500/50" : "border-zinc-800"}`} data-testid="observatory-feed">
          <div className="grid grid-cols-12 gap-2 border-b border-zinc-800 bg-zinc-900/60 px-4 py-2 text-[11px] uppercase tracking-widest text-zinc-500">
            <div className="col-span-2">Presence</div>
            <div className="col-span-1">Turn</div>
            <div className="col-span-2">Selection</div>
            <div className="col-span-1">Codons</div>
            <div className="col-span-1">Phase</div>
            <div className="col-span-2">Prompt</div>
            <div className="col-span-3">Time · Hash</div>
          </div>
          <div className="max-h-[52vh] overflow-y-auto">
            {turns.length === 0 && (
              <div className="px-4 py-10 text-center text-sm text-zinc-600" data-testid="observatory-empty">
                No turns captured yet. Speak with a presence and they will appear here in real time.
              </div>
            )}
            {turns.map((t) => (
              <button
                key={t.provenance_id}
                onClick={() => openDetail(t)}
                data-testid={`turn-row-${t.provenance_id}`}
                className="grid w-full grid-cols-12 items-center gap-2 border-b border-zinc-900 px-4 py-3 text-left text-sm hover:bg-zinc-900/70"
              >
                <div className="col-span-2 truncate font-medium text-zinc-100">{t.presence}</div>
                <div className="col-span-1 text-zinc-400">#{t.exchange_index ?? "—"}</div>
                <div className={`col-span-2 truncate text-xs ${zoneColor(t.selection_branch)}`}>{t.selection_branch || "—"}</div>
                <div className="col-span-1 text-zinc-300">{t.selected_count ?? "—"}</div>
                <div className="col-span-1 text-zinc-300">{t.inferred_phase ?? "—"}°</div>
                <div className="col-span-2 text-zinc-500">{(t.system_prompt_bytes / 1024).toFixed(1)} KB</div>
                <div className="col-span-3 flex items-center gap-2 text-xs text-zinc-500">
                  <span>{fmtTime(t.timestamp)}</span>
                  <span className="inline-flex items-center gap-1 text-zinc-600"><Hash className="h-3 w-3" />{t.content_hash?.slice(0, 8)}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Detail drawer */}
      {selected && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={() => setSelected(null)} data-testid="detail-overlay">
          <div className="h-full w-full max-w-2xl overflow-y-auto border-l border-zinc-800 bg-zinc-950 p-6" onClick={(e) => e.stopPropagation()} data-testid="detail-drawer">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <div className="text-xs uppercase tracking-widest text-zinc-500">Model-visible context</div>
                <h2 className="text-xl font-light text-zinc-100">{selected.presence} · turn #{selected.exchange_index}</h2>
              </div>
              <button onClick={() => setSelected(null)} data-testid="detail-close" className="rounded-full p-2 text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200">
                <X className="h-5 w-5" />
              </button>
            </div>

            {!detail && <div className="text-sm text-zinc-500">Loading record…</div>}
            {detail?.error && <div className="text-sm text-red-400">{detail.error}</div>}

            {detail && !detail.error && (
              <div className="space-y-6 text-sm">
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-lg border border-zinc-800 p-3">
                    <div className="text-[11px] uppercase tracking-widest text-zinc-500">Model</div>
                    <div className="flex items-center gap-2 text-zinc-200"><Cpu className="h-3.5 w-3.5 text-zinc-500" />{detail.model}</div>
                  </div>
                  <div className="rounded-lg border border-zinc-800 p-3">
                    <div className="text-[11px] uppercase tracking-widest text-zinc-500">Integrity hash</div>
                    <div className="truncate font-mono text-xs text-emerald-300" data-testid="detail-hash">{detail.content_hash}</div>
                  </div>
                </div>

                {/* Codon selection */}
                {detail.components?.codon_selection && (
                  <div>
                    <div className="mb-2 flex items-center gap-2 text-zinc-300"><Compass className="h-4 w-4 text-sky-400" /> Codon selection</div>
                    <div className="mb-2 text-xs text-zinc-500">
                      branch <span className={zoneColor(detail.components.codon_selection.selection_branch)}>{detail.components.codon_selection.selection_branch}</span>
                      {" · "}phase {detail.components.codon_selection.inferred_phase}°
                      {" · "}{detail.components.codon_selection.selected_count} surfaced
                    </div>
                    <div className="max-h-52 space-y-1 overflow-y-auto rounded-lg border border-zinc-800 bg-zinc-900/40 p-2">
                      {(detail.components.codon_selection.codons || []).map((c, i) => (
                        <div key={i} className="flex items-center justify-between gap-2 text-xs">
                          <span className="truncate text-zinc-200">{c.name}</span>
                          <span className="shrink-0 text-zinc-500">{c.triadic_zone} · {c.target_angle}°</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Assembled messages */}
                <div>
                  <div className="mb-2 text-zinc-300">Assembled input (as sent)</div>
                  <div className="space-y-2">
                    {(detail.assembled_messages || []).map((m, i) => (
                      <div key={i} className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-3">
                        <div className="mb-1 text-[11px] uppercase tracking-widest text-zinc-500">{m.role}</div>
                        <pre className="max-h-64 overflow-y-auto whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-zinc-400">{m.content}</pre>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
