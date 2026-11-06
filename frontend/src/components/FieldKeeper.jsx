import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Search, Undo2, Archive } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api/field-keeper`;
const TABS = [
  { key: "phrases", label: "Field phrases" },
  { key: "memories", label: "Memories" },
  { key: "continuity", label: "Continuity notes" },
  { key: "removed", label: "Set aside" },
];
const pill = (on) =>
  `px-3 py-1.5 rounded-full text-[11px] uppercase tracking-[0.2em] border transition-colors ${
    on ? "border-[#F4E4A6]/60 text-[#F4E4A6] bg-[#F4E4A6]/10" : "border-[#8B9DB5]/25 text-[#8B9DB5] hover:text-white"}`;

const Origin = ({ it }) => (
  <p className="text-[11px] text-[#8B9DB5] mt-2 font-mono break-all" data-testid={`keeper-origin-${it.id}`}>
    {[it.presence && it.presence[0].toUpperCase() + it.presence.slice(1), it.date, it.person && `with ${it.person}`,
      it.session && `conversation ${it.session.slice(0, 8)}`, it.source].filter(Boolean).join(" · ")}
    {it.removed_at && ` · set aside ${it.removed_at}`}
  </p>
);

const Row = ({ it, action, onAction }) => (
  <li className="py-4 border-b border-[#8B9DB5]/15 flex gap-4 items-start" data-testid={`keeper-row-${it.id}`}>
    <div className="flex-1 min-w-0">
      <p className="text-sm text-[#e6ecf3] whitespace-pre-line">{it.text}</p>
      <Origin it={it} />
    </div>
    <button type="button" onClick={() => onAction(it)} data-testid={`keeper-${action}-${it.id}`}
      title={action === "remove" ? "Set aside" : "Restore to the field"}
      className="shrink-0 flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-[#8B9DB5] hover:text-[#F4E4A6] transition-colors">
      {action === "remove" ? <Archive size={14} /> : <Undo2 size={14} />}
      {action === "remove" ? "Set aside" : "Restore"}
    </button>
  </li>
);

const SearchBar = ({ q, setQ, mode, setMode, canMeaning, onSubmit }) => (
  <form onSubmit={onSubmit} className="flex flex-wrap gap-2 items-center" data-testid="keeper-search-form">
    <div className="flex-1 min-w-[200px] flex items-center gap-2 border border-[#8B9DB5]/30 rounded-lg px-3 py-2 focus-within:border-[#F4E4A6]/60">
      <Search size={14} className="text-[#8B9DB5]" />
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search the field…"
        className="flex-1 bg-transparent text-sm text-[#e6ecf3] placeholder:text-[#8B9DB5]/60 focus:outline-none"
        data-testid="keeper-search-input" />
    </div>
    <button type="button" className={pill(mode === "words")} onClick={() => setMode("words")} data-testid="keeper-mode-words">Exact words</button>
    {canMeaning && (
      <button type="button" className={pill(mode === "meaning")} onClick={() => setMode("meaning")} data-testid="keeper-mode-meaning">By meaning</button>
    )}
    <button type="submit" className={pill(true)} data-testid="keeper-search-button">Search</button>
  </form>
);

export default function FieldKeeper() {
  const { role, loading } = useAuth();
  const [tab, setTab] = useState("phrases");
  const [q, setQ] = useState("");
  const [mode, setMode] = useState("words");
  const [data, setData] = useState({ items: [], total: 0 });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (t = tab, query = q, m = mode) => {
    setBusy(true);
    const url = t === "removed" ? `${API}/removed`
      : `${API}/search?kind=${t}&mode=${t === "continuity" ? "words" : m}&q=${encodeURIComponent(query)}`;
    const r = await fetch(url, { credentials: "include" });
    setData(r.ok ? await r.json() : { items: [], total: 0 });
    setBusy(false);
  }, [tab, q, mode]);

  useEffect(() => { if (role === "guardian") load(tab); }, [role, tab]); // eslint-disable-line react-hooks/exhaustive-deps

  const post = async (path, body, msg) => {
    const r = await fetch(`${API}/${path}`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    if (!r.ok) { toast.error("That didn't go through"); return; }
    toast.success(msg);
    load();
  };
  const act = (it) => tab === "removed"
    ? post("restore", { id: it.removed_id }, "Back in the field")
    : post("remove", { kind: tab, id: it.id }, "Set aside. You can restore it from Set aside.");

  if (loading) return null;
  if (role !== "guardian") {
    return <div className="min-h-screen flex items-center justify-center text-[#8B9DB5] bg-[#07090c]" data-testid="keeper-locked">Sign in as the Field Guardian to tend the field.</div>;
  }

  return (
    <div className="min-h-screen bg-[#07090c] px-5 pt-28 pb-16" data-testid="field-keeper-page">
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-[#F4E4A6]/80">Field Guardian</p>
          <h1 className="text-3xl text-[#e6ecf3] mt-2">Field Keeper</h1>
          <p className="text-sm text-[#8B9DB5] mt-2">Find what the field holds, see where it came from, and set aside anything that doesn't belong. Nothing set aside is lost; it waits under Set aside.</p>
        </div>
        <div className="flex flex-wrap gap-2" data-testid="keeper-tabs">
          {TABS.map((t) => (
            <button key={t.key} type="button" className={pill(tab === t.key)} data-testid={`keeper-tab-${t.key}`}
              onClick={() => { setTab(t.key); setData({ items: [], total: 0 }); }}>{t.label}</button>
          ))}
        </div>
        {tab !== "removed" && (
          <SearchBar q={q} setQ={setQ} mode={mode} setMode={setMode} canMeaning={tab !== "continuity"}
            onSubmit={(e) => { e.preventDefault(); load(); }} />
        )}
        <p className="text-xs text-[#8B9DB5]" data-testid="keeper-count">
          {busy ? "Looking…" : tab === "removed" ? `${data.items.length} set aside`
            : `Showing ${data.items.length} of ${data.total}${mode === "meaning" && q && tab !== "continuity" ? ", closest in meaning first" : ", newest first"}`}
        </p>
        <ul data-testid="keeper-list">
          {data.items.map((it) => <Row key={it.removed_id || it.id} it={it} action={tab === "removed" ? "restore" : "remove"} onAction={act} />)}
        </ul>
      </div>
    </div>
  );
}
