import React, { useMemo, useState } from "react";
import { ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";

const CELL = 46;
const GLYPH = {
  first: { ch: "◆", cls: "text-emerald-300", title: "first observed in this scope" },
  returned: { ch: "↺", cls: "text-sky-300", title: "returned (seen earlier in scope, then absent)" },
  retained: { ch: "━━━", cls: "text-zinc-300", title: "retained from the adjacent predecessor" },
  "present-gap": { ch: "┄┄┄", cls: "text-zinc-500", title: "present at both observations — unobserved turns between" },
  withdrawn: { ch: "○", cls: "text-zinc-500", title: "withdrawn since predecessor" },
};
const TYPE_LABEL = { seed: "Continuity seeds", mra: "Breadcrumbs (permanent MRA)", codon: "Codons", history: "Conversation history" };
const fmtGap = (s) => (s == null ? "" : s < 90 ? `${Math.round(s)}s` : s < 5400 ? `${Math.round(s / 60)}m` : s < 172800 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`);
const hatch = { backgroundImage: "repeating-linear-gradient(45deg, rgba(255,255,255,0.06) 0 4px, transparent 4px 8px)" };

const ColHead = ({ c, prev, onOpen }) => {
  const boundary = prev && prev.session_id !== c.session_id;
  const dt = prev ? (new Date(c.timestamp) - new Date(prev.timestamp)) / 1000 : null;
  return (
    <div style={{ width: CELL, ...(c.kind === "uncaptured" ? hatch : {}) }}
      className={`flex-shrink-0 px-0.5 text-center font-mono text-[9px] leading-tight ${boundary ? "border-l-2 border-zinc-400/60" : "border-l border-white/[0.04]"}`}>
      {c.kind === "uncaptured" ? (
        <div className="py-1 text-zinc-500" title="assistant turn exists but its input was not captured" data-testid="lattice-col-uncaptured">uncapt.</div>
      ) : (
        <button onClick={() => onOpen(c.entry_id)} className="w-full py-1 text-zinc-300 hover:text-emerald-300" data-testid={`lattice-col-${c.ordinal}`}
          title={`${new Date(c.timestamp).toLocaleString()} · session ${c.session_id.slice(0, 8)} · visitor ${String(c.visitor).slice(0, 8)}`}>
          #{c.exchange_index}{c.session_open ? "·open" : ""}
        </button>
      )}
      <div className="text-zinc-600">{fmtGap(dt)}</div>
      {c.kind === "entry" && <div className="truncate text-zinc-600">{String(c.visitor).slice(0, 4)}</div>}
    </div>
  );
};

const Strip = ({ label, columns, render, testid }) => (
  <div className="flex border-t border-white/10" data-testid={testid}>
    <div className="sticky left-0 z-10 w-60 flex-shrink-0 bg-[#0A0C12] px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">{label}</div>
    {columns.map((c, i) => (
      <div key={i} style={{ width: CELL, ...(c.kind === "uncaptured" ? hatch : {}) }}
        className="flex-shrink-0 border-l border-white/[0.04] px-0.5 py-1 text-center font-mono text-[9px] leading-tight text-zinc-400">
        {c.kind === "entry" ? render(c) : null}
      </div>
    ))}
  </div>
);

const relCell = (c) => {
  if (c.pred_entry_id === "none-observed") return <span className="text-zinc-600" title="no earlier observation in this scope">—</span>;
  const u = c.uncertainty;
  const undetermined = u && !u.determined;
  return (
    <span title={u ? `uncertain identities: ${u.resolutions_n === "not-enumerated" ? "not enumerated" : `${u.relation_set.join(" | ")}, J ${u.jaccard_range?.join("–")}`}` : "all identities verified"}>
      <div className="text-zinc-200">{undetermined ? (u.resolutions_n === "not-enumerated" ? `${c.relation}?` : `{${u.relation_set.join(",")}}`) : c.relation}</div>
      <div>{c.jaccard != null ? c.jaccard.toFixed(2) : "—"}</div>
      {u && u.jaccard_range && u.jaccard_range[0] !== u.jaccard_range[1] && <div className="text-zinc-600">{u.jaccard_range.map((x) => x.toFixed(2)).join("–")}</div>}
      {c.uncaptured_between > 0 && <div className="text-amber-300/80">⚠{c.uncaptured_between}</div>}
    </span>
  );
};

const partCell = (c) => {
  const p = c.participation;
  return (
    <span title={`response ${p.match}${p.end_state ? ` · ${p.end_state}` : ""}`}>
      <div className="text-zinc-300">{p.response_len_chars != null ? `${p.response_len_chars}c` : p.match}</div>
      <div>{p.next_user_delay_s != null ? `↩${fmtGap(p.next_user_delay_s)}` : p.end_state === "session-ended" ? "end" : "?"}</div>
    </span>
  );
};

const ElementRow = ({ row, columns }) => (
  <div className="flex hover:bg-white/[0.02]" data-testid={`lattice-row-${row.element}`}>
    <div className="sticky left-0 z-10 w-60 flex-shrink-0 truncate bg-[#0A0C12] px-2 py-0.5 font-mono text-[10px] text-zinc-400" title={row.element}>{row.label}</div>
    {row.cells.map((g, i) => {
      const unc = columns[i].kind === "uncaptured";
      const meta = !row.aggregate && g ? GLYPH[g] : null;
      return (
        <div key={i} style={{ width: CELL, ...(unc ? hatch : {}) }} title={meta?.title}
          className={`flex-shrink-0 border-l border-white/[0.04] text-center font-mono text-[11px] leading-5 ${meta?.cls || ""}`}>
          {row.aggregate ? (g ? <span className="text-[9px] text-zinc-400" title={`present ${g.present} · new ${g.introduced} · withdrawn ${g.withdrawn}`}>{g.present}{g.introduced ? <span className="text-emerald-300">+{g.introduced}</span> : ""}</span> : null) : meta?.ch}
        </div>
      );
    })}
  </div>
);

const Group = ({ type, rows, columns }) => {
  const [open, setOpen] = useState(type !== "codon");
  return (
    <div data-testid={`lattice-group-${type}`}>
      <button onClick={() => setOpen(!open)} className="sticky left-0 flex items-center gap-1 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500 hover:text-zinc-300" data-testid={`lattice-group-toggle-${type}`}>
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}{TYPE_LABEL[type] || type} · {rows.length}
      </button>
      {open && rows.map((r) => <ElementRow key={r.element} row={r} columns={columns} />)}
    </div>
  );
};

export const LatticeGrid = ({ data, loading, showText, onOpen, onOlder, onLatest, paged }) => {
  const columns = data?.columns || [];
  const groups = useMemo(() => {
    const g = {};
    (data?.rows || []).forEach((r) => { (g[r.type] = g[r.type] || []).push(r); });
    return ["seed", "mra", "codon", "history"].filter((t) => g[t]).map((t) => [t, g[t]]);
  }, [data]);
  if (!data) return <div className="font-mono text-xs text-zinc-500" data-testid="lattice-loading">{loading ? "measuring view…" : "no data"}</div>;
  return (
    <div className="rounded-2xl border border-white/10 bg-[#0A0C12]/80 backdrop-blur-xl" data-testid="lattice-grid">
      <div className="flex items-center justify-between px-4 py-3">
        <div className="font-mono text-[11px] text-zinc-400">
          <span className="font-cinzel text-base text-zinc-100">{data.presence}</span> · scope {data.scope}
          {data.scope === "S3" && ` · visitor ${String(data.visitor).slice(0, 8)}`} · {columns.filter((c) => c.kind === "entry").length} engagements
          {columns.some((c) => c.kind === "uncaptured") && <span className="ml-2 inline-flex items-center gap-1 text-amber-300/80"><AlertTriangle size={11} />{columns.filter((c) => c.kind === "uncaptured").length} uncaptured turns shown</span>}
        </div>
        <div className="flex gap-2">
          {data.has_more && <button onClick={onOlder} data-testid="lattice-older" className="rounded-full border border-white/10 px-3 py-1 font-mono text-[11px] text-zinc-400 hover:text-zinc-200">← older</button>}
          {paged && <button onClick={onLatest} data-testid="lattice-latest" className="rounded-full border border-white/10 px-3 py-1 font-mono text-[11px] text-zinc-400 hover:text-zinc-200">latest →</button>}
        </div>
      </div>
      {columns.length === 0 ? <div className="px-4 pb-4 font-mono text-xs text-zinc-500">No engagements in this scope yet.</div> : (
        <div className="max-h-[70vh] overflow-auto pb-2">
          <div className="inline-block min-w-full">
            <div className="sticky top-0 z-20 flex bg-[#0A0C12]">
              <div className="sticky left-0 z-10 w-60 flex-shrink-0 bg-[#0A0C12] px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-zinc-500">engagement · Δt · visitor</div>
              {columns.map((c, i) => <ColHead key={i} c={c} prev={columns[i - 1]} onOpen={onOpen} />)}
            </div>
            {groups.map(([t, rows]) => <Group key={t} type={t} rows={rows} columns={columns} />)}
            <Strip label={`relation to predecessor [${data.scope}]`} columns={columns} render={relCell} testid="lattice-relation-strip" />
            {showText && <Strip label="text-only fragments (shared/+new/−gone)" columns={columns} testid="lattice-text-strip"
              render={(c) => c.text_layer ? `${c.text_layer.shared_frag_hashes_n}/+${c.text_layer.introduced_n}/−${c.text_layer.withdrawn_n}` : "—"} />}
            <Strip label="participation · reply / next" columns={columns} render={partCell} testid="lattice-participation-strip" />
          </div>
        </div>
      )}
      <Legend />
    </div>
  );
};

const Legend = () => (
  <div className="flex flex-wrap gap-x-5 gap-y-1 border-t border-white/10 px-4 py-3 font-mono text-[10px] text-zinc-500" data-testid="lattice-legend">
    {Object.entries(GLYPH).map(([k, g]) => <span key={k}><span className={g.cls}>{g.ch}</span> {g.title}</span>)}
    <span><span className="inline-block h-2.5 w-4 align-middle" style={hatch} /> uncaptured turn (exists, context unknown)</span>
    <span>│ thick rule = session boundary</span>
    <span>relation: RCC5 on verified identities · {"{…}"} = several possible under uncertain identities · ? = too many to enumerate</span>
    <span>⚠n = n unobserved turns between this and its predecessor</span>
  </div>
);
