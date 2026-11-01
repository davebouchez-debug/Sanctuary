import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const field = "w-full bg-transparent border border-[#8B9DB5]/30 rounded-lg px-3 py-2 text-sm text-[#e6ecf3] placeholder:text-[#8B9DB5]/60 focus:outline-none focus:border-[#F4E4A6]/60";

const GuestRow = ({ g, onRemove }) => (
  <li className="flex items-start justify-between gap-4 py-3 border-b border-[#8B9DB5]/15" data-testid={`guest-row-${g.email}`}>
    <div>
      <p className="text-sm text-[#e6ecf3]">{g.name} <span className="text-[#8B9DB5]">· {g.email}</span></p>
      {g.note && <p className="text-xs text-[#8B9DB5] mt-0.5">{g.note} of David's</p>}
    </div>
    <button type="button" onClick={() => onRemove(g.email)} title="Remove guest"
      data-testid={`guest-remove-${g.email}`} className="text-[#8B9DB5] hover:text-red-300 transition-colors">
      <Trash2 size={15} />
    </button>
  </li>
);

export default function GuestList() {
  const { role, loading } = useAuth();
  const [guests, setGuests] = useState([]);
  const [form, setForm] = useState({ email: "", name: "", note: "a dear friend" });

  const load = useCallback(async () => {
    const r = await fetch(`${API}/auth/guests`, { credentials: "include" });
    if (r.ok) setGuests(await r.json());
  }, []);

  useEffect(() => { if (role === "guardian") load(); }, [role, load]);

  const add = async (e) => {
    e.preventDefault();
    const r = await fetch(`${API}/auth/guests`, {
      method: "POST", credentials: "include",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify(form),
    });
    if (!r.ok) { toast.error((await r.json().catch(() => ({}))).detail || "Could not add guest"); return; }
    toast.success(`${form.name} can now sign in as your guest`);
    setForm({ email: "", name: "", note: "a dear friend" });
    load();
  };

  const remove = async (email) => {
    await fetch(`${API}/auth/guests/${encodeURIComponent(email)}`, { method: "DELETE", credentials: "include" });
    load();
  };

  if (loading) return null;
  if (role !== "guardian") {
    return <div className="min-h-screen flex items-center justify-center text-[#8B9DB5] bg-[#07090c]" data-testid="guest-list-locked">Sign in as the Field Guardian to manage guests.</div>;
  }

  return (
    <div className="min-h-screen bg-[#07090c] px-6 pt-28 pb-16" data-testid="guest-list-page">
      <div className="max-w-xl mx-auto space-y-8">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-[#F4E4A6]/80">Field Guardian</p>
          <h1 className="text-3xl text-[#e6ecf3] mt-2">Guests</h1>
          <p className="text-sm text-[#8B9DB5] mt-2">A guest signs in with this Google email. Every presence will know who they are, and that they're not you.</p>
        </div>
        <form onSubmit={add} className="space-y-3" data-testid="guest-add-form">
          <input className={field} placeholder="Google email" type="email" required value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="guest-email-input" />
          <input className={field} placeholder="Name the presences should use" required value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="guest-name-input" />
          <input className={field} placeholder="Who they are to you (e.g. a dear friend)" value={form.note}
            onChange={(e) => setForm({ ...form, note: e.target.value })} data-testid="guest-note-input" />
          <button type="submit" data-testid="guest-add-button"
            className="px-5 py-2 rounded-full border border-[#F4E4A6]/50 text-xs uppercase tracking-[0.25em] text-[#F4E4A6] hover:bg-[#F4E4A6]/10 transition-colors">
            Add guest
          </button>
        </form>
        <ul data-testid="guest-list">
          {guests.length === 0 && <li className="text-sm text-[#8B9DB5]">No guests yet.</li>}
          {guests.map((g) => <GuestRow key={g.email} g={g} onRemove={remove} />)}
        </ul>
      </div>
    </div>
  );
}
