import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api/presence-history`;
const KINDS = ["record", "recollection", "interpretation", "self_description", "summary", "initial_history"];
const NAMES = { scroll: "Scroll", scrolldog: "ScrollDog", daniel: "Daniel", keeper: "Keeper" };
const field = "bg-transparent border border-[#8B9DB5]/30 rounded px-2 py-1 text-sm text-white";
const btn = "px-3 py-1.5 rounded-full text-[11px] uppercase tracking-[0.2em] border border-[#F4E4A6]/50 text-[#F4E4A6] hover:bg-[#F4E4A6]/10 disabled:opacity-40";

const post = (path, body) => fetch(`${API}${path}`, {
  method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
}).then(async (r) => ({ ok: r.ok, data: await r.json().catch(() => ({})) }));

const Positions = ({ value, onChange, id }) => (
  <span className="flex gap-3 text-sm text-[#C9D4E3]">
    {Object.keys(NAMES).map((p) => (
      <label key={p} className="flex items-center gap-1">
        <input type="checkbox" data-testid={`${id}-${p}`} checked={value.includes(p)}
          onChange={() => onChange(value.includes(p) ? value.filter((x) => x !== p) : [...value, p])} />
        {NAMES[p]}
      </label>
    ))}
  </span>
);

const ImportFile = ({ onDone }) => {
  const [f, setF] = useState(null);
  const [meta, setMeta] = useState({ positions: ["scroll"], kind: "record", date: "", speaker: "" });
  const go = async () => {
    const text = await f.text();
    const r = await post("/import", { ...meta, text, source: f.name, visibility: "guardian" });
    r.ok ? toast.success(r.data.imported ? `Imported ${r.data.imported} parts` : "Already imported") : toast.error(r.data.detail || "Import failed");
    onDone();
  };
  return (
    <div className="space-y-2" data-testid="history-import-file">
      <input type="file" accept=".txt,.md" data-testid="history-file-input" onChange={(e) => setF(e.target.files[0])} className="text-sm text-[#C9D4E3]" />
      <div className="flex flex-wrap gap-3 items-center">
        <Positions id="history-file-pos" value={meta.positions} onChange={(positions) => setMeta({ ...meta, positions })} />
        <select className={field} data-testid="history-file-kind" value={meta.kind} onChange={(e) => setMeta({ ...meta, kind: e.target.value })}>
          {KINDS.map((k) => <option key={k} value={k} className="bg-[#0B1020]">{k}</option>)}
        </select>
        <input className={field} type="date" data-testid="history-file-date" value={meta.date} onChange={(e) => setMeta({ ...meta, date: e.target.value })} />
        <input className={field} placeholder="Speakers" data-testid="history-file-speaker" value={meta.speaker} onChange={(e) => setMeta({ ...meta, speaker: e.target.value })} />
        <button type="button" className={btn} data-testid="history-file-import-btn" disabled={!f || !meta.positions.length} onClick={go}>Import</button>
      </div>
    </div>
  );
};

export const HistoryKeeper = () => {
  const [summary, setSummary] = useState({ sources: [] });
  const [sessions, setSessions] = useState([]);
  const load = useCallback(async () => {
    const [a, b] = await Promise.all([fetch(`${API}/summary`, { credentials: "include" }), fetch(`${API}/sessions`, { credentials: "include" })]);
    if (a.ok) setSummary(await a.json());
    if (b.ok) setSessions(await b.json());
  }, []);
  useEffect(() => { load(); }, [load]);
  const act = async (path, body, ok) => {
    const r = await post(path, body);
    r.ok ? toast.success(ok(r.data)) : toast.error(r.data.detail || "Failed");
    load();
  };
  const sources = {};
  summary.sources.forEach((s) => {
    const k = s.source;
    sources[k] = sources[k] || { ...s, chunks: 0 };
    sources[k].chunks += s.chunks;
  });
  return (
    <div className="space-y-8 text-[#C9D4E3]" data-testid="history-keeper">
      <section className="space-y-2">
        <h3 className="text-xs uppercase tracking-[0.2em] text-[#F4E4A6]">Add a source file</h3>
        <ImportFile onDone={load} />
      </section>
      <section className="space-y-2">
        <h3 className="text-xs uppercase tracking-[0.2em] text-[#F4E4A6]">Initial histories, seen by every room in the hall</h3>
        <div className="flex flex-wrap gap-2">
          {["scrolldog", "daniel", "keeper"].map((p) => (
            <button key={p} type="button" className={btn} data-testid={`history-import-initial-${p}`}
              onClick={() => act(`/import-initial-history/${p}`, {}, (d) => (d.imported ? `Added ${NAMES[p]}'s initial history` : "Already added"))}>
              Add {NAMES[p]}'s initial history
            </button>
          ))}
        </div>
        <p className="text-xs opacity-70">Written once and fixed. Each session takes these when it starts and keeps them unchanged until it ends. Conversations never go here.</p>
      </section>
      <section className="space-y-2">
        <h3 className="text-xs uppercase tracking-[0.2em] text-[#F4E4A6]">ScrollDog conversations</h3>
        <button type="button" className={btn} data-testid="history-import-scroll-packet"
          onClick={() => act("/import-scroll-packet", {}, (d) => `Scroll packet: ${d.files.map((f) => f.imported).reduce((a, b) => a + b, 0)} parts added to this room's records`)}>
          Add the Scroll source packet (3 conversations, this room only)
        </button>
        <ul className="space-y-1 text-sm">
          {sessions.map((s) => (
            <li key={s.session_id} className="flex gap-3 items-center" data-testid={`history-session-${s.session_id}`}>
              <span>{s.date} · {s.visitor || "visitor"} · {s.messages} messages</span>
              <button type="button" className={btn} data-testid={`history-session-import-${s.session_id}`}
                onClick={() => act("/import-session", { session_id: s.session_id, positions: ["scrolldog"] },
                  (d) => (d.imported ? `Copied ${d.imported} parts` : "Already copied"))}>Copy into history</button>
            </li>
          ))}
        </ul>
      </section>
      <section className="space-y-2">
        <h3 className="text-xs uppercase tracking-[0.2em] text-[#F4E4A6]">In the history now</h3>
        <ul className="space-y-1 text-sm" data-testid="history-sources">
          {Object.values(sources).map((s) => (
            <li key={s.source}>{s.date || "undated"} · {s.source} · {s.kind} · {(s.positions || []).join(" + ")} · {s.chunks} parts</li>
          ))}
        </ul>
      </section>
    </div>
  );
};
