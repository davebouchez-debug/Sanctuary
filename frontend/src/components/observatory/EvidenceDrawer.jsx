import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import axios from "axios";
import { X, ChevronDown, ChevronRight } from "lucide-react";
import { API } from "../../App";

const CLASS_ORDER = ["VERIFIED", "CANDIDATES", "UNRESOLVED", "TEXT_ONLY"];

const Mention = ({ m }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-white/[0.04] py-1.5" data-testid={`evidence-mention-${m.mention_id}`}>
      <button onClick={() => setOpen(!open)} className="flex w-full items-center gap-2 text-left font-mono text-[11px] text-zinc-300">
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <span className="w-16 text-zinc-500">{m.type}</span>
        <span className="truncate">{m.element || (m.candidates ? `${m.candidates.length} candidates` : `#${m.frag_hash.slice(0, 10)}`)}</span>
        {m.render_matches_current_record === false && <span className="ml-auto text-amber-300/80" title="rendered text differs from the stored record as it reads now">≠ store</span>}
        {m.identity_basis === "name+current-angle" && <span className="ml-auto text-zinc-500" title="identified by name plus current angle (angle may have drifted)">angle tie-break</span>}
        {m.identity_basis === "mutable-angle" && <span className="ml-auto text-violet-300/80" title="conditional: identified only by the mutable current angle within the loader scope">∠ conditional</span>}
        {m.reason && <span className="ml-auto text-zinc-500" data-testid={`evidence-reason-${m.mention_id}`}>{m.reason}</span>}
      </button>
      {open && (
        <div className="ml-5 mt-1 space-y-1 font-mono text-[10px] text-zinc-500">
          <div>field {m.field}{m.start != null ? ` [${m.start}–${m.end}]` : ""} · frag {m.frag_hash.slice(0, 16)}</div>
          {m.candidates && <div>candidates: {m.candidates.join(", ")}</div>}
          {m.record_fingerprint && <div>record fingerprint {m.record_fingerprint.slice(0, 16)}</div>}
          <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded bg-black/40 p-2 text-zinc-300">{m.evidence_text}</pre>
        </div>
      )}
    </div>
  );
};

const Row = ({ k, v }) => (
  <div className="flex justify-between gap-3 py-0.5"><span className="text-zinc-500">{k}</span><span className="truncate text-right text-zinc-300">{String(v ?? "—")}</span></div>
);

const ScopeBlock = ({ name, s }) => {
  const v = s.verified || {};
  const u = s.uncertainty;
  const enumerated = u && u.resolutions_n !== "not-enumerated";
  return (
    <div className="rounded-lg border border-white/10 p-2" data-testid={`evidence-scope-${name}`}>
      <div className="mb-1 text-zinc-400">{name} · predecessor {String(s.pred_entry_id).slice(-8)}</div>
      {s.pred_entry_id !== "none-observed" && (<>
        {u && <Row k="compatible outcomes" v={enumerated ? `${u.relation_set.join(" | ")} · J ${u.jaccard_range?.join("–")} · ${u.resolutions_n} resolutions` : "not enumerated (too many resolutions)"} />}
        <Row k="relation (verified-only)" v={v.relation_rcc5} />
        <Row k="jaccard (verified-only)" v={v.jaccard} />
        <Row k="first-observed / returned" v={`${(v.introduced_first_observed || []).length} / ${(v.returned || []).length}`} />
        <Row k="withdrawn / present-at-both" v={`${(v.withdrawn || []).length} / ${(v.present_at_both || []).length}`} />
        <Row k="adjacent" v={v.adjacent ? "yes" : "no"} />
        <Row k="uncaptured between" v={s.uncaptured_between} />
        {s.uncaptured_unplaceable > 0 && <Row k="uncaptured, time unknown" v={s.uncaptured_unplaceable} />}
        {s.conditional_identity_n > 0 && <Row k="conditional identities (∠ angle)" v={s.conditional_identity_n} />}
      </>)}
    </div>
  );
};

export const EvidenceDrawer = ({ entryId, onClose }) => {
  const [e, setE] = useState(null);
  const [err, setErr] = useState(null);
  useEffect(() => {
    let live = true;
    setE(null); setErr(null);
    if (entryId) {
      axios.get(`${API}/observatory/entry/${encodeURIComponent(entryId)}`)
        .then(({ data }) => live && setE(data))
        .catch(() => live && setErr("Could not load this entry."));
    }
    return () => { live = false; };
  }, [entryId]);
  useEffect(() => {
    if (!entryId) return undefined;
    const onKey = (ev) => ev.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [entryId, onClose]);
  if (!entryId) return null;
  const groups = CLASS_ORDER.map((c) => [c, (e?.mentions || []).filter((m) => m.class === c)]);
  return createPortal(
    <>
    <div className="fixed inset-0 z-[70] bg-black/40" onClick={onClose} data-testid="evidence-backdrop" />
    <div className="fixed inset-y-0 right-0 z-[71] w-full max-w-xl overflow-y-auto border-l border-white/10 bg-[#07080C]/95 p-5 backdrop-blur-xl" data-testid="evidence-drawer">
      <div className="mb-4 flex items-center justify-between">
        <div className="font-cinzel text-lg text-zinc-100">Evidence</div>
        <button onClick={onClose} data-testid="evidence-close" className="rounded-lg border border-white/10 p-1.5 text-zinc-400 hover:text-zinc-100"><X size={16} /></button>
      </div>
      {err ? <div className="font-mono text-xs text-amber-300" data-testid="evidence-error">{err}</div> : !e ? <div className="font-mono text-xs text-zinc-500">loading…</div> : (
        <div className="space-y-4 font-mono text-[11px]">
          <section className="rounded-lg border border-white/10 p-3" data-testid="evidence-source">
            <Row k="presence · turn" v={`${e.chronology.presence} · #${e.chronology.exchange_index}`} />
            <Row k="time" v={new Date(e.chronology.timestamp).toLocaleString()} />
            <Row k="session" v={e.chronology.session_id} />
            <Row k="visitor" v={`${e.visitor.resolved_visitor} (${e.visitor.resolution})`} />
            <Row k="provenance" v={e.source.provenance_id} />
            <Row k="input integrity" v={e.source.integrity_verified ? "hash verified" : "MISMATCH"} />
            <Row k="chain position" v={`#${e.chronology.ordinal} · ${e.chain.entry_hash.slice(0, 16)}`} />
            <Row k="method" v={`v${e.derivation_version} · ${e.norm_version} · run ${String(e.run_id).slice(0, 8)} · commit ${String(e.run?.code_commit).slice(0, 8)}`} />
            <Row k="response" v={`${e.participation.match} · ${e.participation.response_len_chars ?? "—"} chars · ${e.participation.end_state}`} />
            {e.gaps.length > 0 && <Row k="gaps" v={e.gaps.join(", ")} />}
            {e.configuration_complete != null && <Row k="configuration" v={e.configuration_complete ? "complete" : "partial (unresolved observed material)"} />}
          </section>
          {e.completeness && (
            <section className="rounded-lg border border-white/10 p-3" data-testid="evidence-completeness">
              <div className="mb-1 uppercase tracking-widest text-zinc-500">section completeness</div>
              {Object.entries(e.completeness).map(([t, r]) => (
                <Row key={t} k={t} v={`${r.status}${r.unresolved_n ? ` · ${r.unresolved_n} unresolved` : ""}${r.unattributed_lines_n ? ` · ${r.unattributed_lines_n} lines unattributed` : ""}`} />
              ))}
            </section>
          )}
          <section className="grid gap-2" data-testid="evidence-scopes">
            {["S1", "S2", "S3"].map((s) => <ScopeBlock key={s} name={s} s={e.scopes[s]} />)}
          </section>
          {groups.map(([c, ms]) => ms.length > 0 && (
            <section key={c} data-testid={`evidence-class-${c}`}>
              <div className="mb-1 uppercase tracking-widest text-zinc-500">{c.replace("_", "-").toLowerCase()} · {ms.length}</div>
              {ms.map((m) => <Mention key={m.mention_id} m={m} />)}
            </section>
          ))}
        </div>
      )}
    </div>
    </>,
    document.body
  );
};
