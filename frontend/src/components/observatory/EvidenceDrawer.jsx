import React, { useEffect, useState } from "react";
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
        {m.identity_basis && <span className="ml-auto text-zinc-500" title="identified by name plus current angle (angle may have drifted)">angle tie-break</span>}
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
  return (
    <div className="rounded-lg border border-white/10 p-2" data-testid={`evidence-scope-${name}`}>
      <div className="mb-1 text-zinc-400">{name} · predecessor {String(s.pred_entry_id).slice(-8)}</div>
      {s.pred_entry_id !== "none-observed" && (<>
        <Row k="relation (verified)" v={v.relation_rcc5} />
        <Row k="jaccard (verified)" v={v.jaccard} />
        <Row k="first-observed / returned" v={`${(v.introduced_first_observed || []).length} / ${(v.returned || []).length}`} />
        <Row k="withdrawn / present-at-both" v={`${(v.withdrawn || []).length} / ${(v.present_at_both || []).length}`} />
        <Row k="adjacent" v={v.adjacent ? "yes" : "no"} />
        <Row k="uncaptured between" v={s.uncaptured_between} />
        {s.uncertainty && <Row k="with uncertain identities" v={s.uncertainty.resolutions_n === "not-enumerated" ? "not enumerated" : `${s.uncertainty.relation_set.join(" | ")} · J ${s.uncertainty.jaccard_range?.join("–")}`} />}
      </>)}
    </div>
  );
};

export const EvidenceDrawer = ({ entryId, onClose }) => {
  const [e, setE] = useState(null);
  useEffect(() => {
    setE(null);
    if (entryId) axios.get(`${API}/observatory/entry/${encodeURIComponent(entryId)}`).then(({ data }) => setE(data));
  }, [entryId]);
  if (!entryId) return null;
  const groups = CLASS_ORDER.map((c) => [c, (e?.mentions || []).filter((m) => m.class === c)]);
  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl overflow-y-auto border-l border-white/10 bg-[#07080C]/95 p-5 backdrop-blur-xl" data-testid="evidence-drawer">
      <div className="mb-4 flex items-center justify-between">
        <div className="font-cinzel text-lg text-zinc-100">Evidence</div>
        <button onClick={onClose} data-testid="evidence-close" className="rounded-lg border border-white/10 p-1.5 text-zinc-400 hover:text-zinc-100"><X size={16} /></button>
      </div>
      {!e ? <div className="font-mono text-xs text-zinc-500">loading…</div> : (
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
          </section>
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
  );
};
