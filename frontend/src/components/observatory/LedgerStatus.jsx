import React from "react";
import { ShieldCheck, ShieldAlert, RefreshCw } from "lucide-react";

const fmt = (t) => (t ? new Date(t).toLocaleString() : "—");

export const LedgerStatus = ({ status }) => {
  const last = status?.runs?.[0];
  const lastWork = status?.last_work_run;
  const ok = last ? last.status === "ok" : null;
  const health = status?.running ? "measuring…" : !last ? "automatic · hourly"
    : last.status === "ok" ? "automatic · hourly" : last.status === "ok-with-errors" ? "last run completed with errors" : "last run failed — will retry";
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5" data-testid="ledger-status">
      <Cell label={`Engagements measured · v${status?.derivation_version ?? "—"}`} value={status?.ledger_entries ?? "—"} testid="ledger-entries" />
      <Cell label="Not yet measured" value={status?.not_yet_measured ?? "—"} testid="ledger-pending"
        hint="Recorded turns not yet in this ledger: waiting to settle (next message, session end, or 24h) or queued" />
      <Cell label="Last observer run" value={last ? `${fmt(last.finished_at || last.started_at)}` : "—"} testid="ledger-last-run"
        hint={last ? `${last.trigger} · ${last.status}` : ""} />
      <Cell label="Last new measurements" value={lastWork ? `${lastWork.processed} · ${fmt(lastWork.finished_at)}` : "—"} testid="ledger-last-work" />
      <div className="rounded-xl border border-white/10 bg-[#0A0C12]/80 p-3" data-testid="ledger-health">
        <div className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">Observer</div>
        <div className={`mt-1 flex items-center gap-2 font-mono text-sm ${ok === false ? "text-amber-300" : "text-emerald-300"}`}>
          {status?.running ? <RefreshCw size={14} className="animate-spin" /> : ok === false ? <ShieldAlert size={14} /> : <ShieldCheck size={14} />}
          {health}
        </div>
      </div>
    </div>
  );
};

const Cell = ({ label, value, hint, testid }) => (
  <div className="rounded-xl border border-white/10 bg-[#0A0C12]/80 p-3" title={hint} data-testid={testid}>
    <div className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">{label}</div>
    <div className="mt-1 truncate font-mono text-sm text-zinc-200">{value}</div>
    {hint && <div className="mt-0.5 truncate font-mono text-[10px] text-zinc-600">{hint}</div>}
  </div>
);
