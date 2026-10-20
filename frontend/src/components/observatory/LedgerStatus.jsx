import React from "react";
import { ShieldCheck, ShieldAlert, RefreshCw } from "lucide-react";

const fmt = (t) => (t ? new Date(t).toLocaleString() : "—");

export const LedgerStatus = ({ status }) => {
  const last = status?.runs?.[0];
  const lastWork = status?.last_work_run;
  const ok = last ? last.status === "ok" : null;
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5" data-testid="ledger-status">
      <Cell label="Engagements measured" value={status?.ledger_entries ?? "—"} testid="ledger-entries" />
      <Cell label="Awaiting settlement" value={status?.pending ?? "—"} testid="ledger-pending"
        hint="Turns whose outcome is not yet known (next message, session end, or 24h)" />
      <Cell label="Last observer run" value={last ? `${fmt(last.finished_at || last.started_at)}` : "—"} testid="ledger-last-run"
        hint={last ? `${last.trigger} · ${last.status}` : ""} />
      <Cell label="Last new measurements" value={lastWork ? `${lastWork.processed} · ${fmt(lastWork.finished_at)}` : "—"} testid="ledger-last-work" />
      <div className="rounded-xl border border-white/10 bg-[#0A0C12]/80 p-3" data-testid="ledger-health">
        <div className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">Observer</div>
        <div className={`mt-1 flex items-center gap-2 font-mono text-sm ${ok === false ? "text-amber-300" : "text-emerald-300"}`}>
          {status?.running ? <RefreshCw size={14} className="animate-spin" /> : ok === false ? <ShieldAlert size={14} /> : <ShieldCheck size={14} />}
          {status?.running ? "measuring…" : ok === false ? "last run failed — will retry" : "automatic · hourly"}
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
