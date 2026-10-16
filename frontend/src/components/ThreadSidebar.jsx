import { Fragment, useCallback, useEffect, useState } from "react";
import { History, Plus, Trash2, MessageSquare } from "lucide-react";
import { toast } from "sonner";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "./ui/sheet";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "./ui/alert-dialog";
import { useIdentity } from "../context/IdentityContext";
import { currentThread } from "../lib/threadSession";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const formatWhen = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
};

const ThreadRow = ({ thread, isCurrent, onOpen, onDelete }) => (
  <div
    data-testid={`thread-item-${thread.session_id}`}
    className={`group flex items-start gap-2 rounded-lg px-3 py-2.5 cursor-pointer transition-colors duration-200 ${
      isCurrent ? "bg-white/10" : "hover:bg-white/5"
    }`}
    onClick={() => onOpen(thread)}
  >
    <MessageSquare className="w-4 h-4 mt-0.5 shrink-0 text-stone-500" />
    <div className="min-w-0 flex-1">
      <p className="text-sm text-stone-200 truncate">{thread.title}</p>
      <p className="text-xs text-stone-500 mt-0.5">
        {formatWhen(thread.last_activity)} · {thread.message_count} messages{isCurrent ? " · open now" : ""}
      </p>
    </div>
    <button
      type="button"
      data-testid={`thread-delete-btn-${thread.session_id}`}
      aria-label="Delete thread"
      className="p-1 rounded text-stone-500 opacity-60 group-hover:opacity-100 hover:text-red-300 transition-opacity duration-200"
      onClick={(e) => { e.stopPropagation(); onDelete(thread); }}
    >
      <Trash2 className="w-4 h-4" />
    </button>
  </div>
);

const ThreadSidebar = ({ presence, onOpenThread, onNewThread }) => {
  const { userId } = useIdentity();
  const [open, setOpen] = useState(false);
  const [threads, setThreads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [toDelete, setToDelete] = useState(null);
  const current = open ? currentThread(presence) : null;

  const load = useCallback(async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const r = await fetch(`${API}/threads/${presence}?user_id=${encodeURIComponent(userId)}`);
      const d = await r.json();
      setThreads(d.threads || []);
    } catch {
      toast.error("Couldn't load your threads");
    } finally {
      setLoading(false);
    }
  }, [presence, userId]);

  useEffect(() => { if (open) load(); }, [open, load]);

  const openThread = (t) => {
    setOpen(false);
    if (t.session_id !== currentThread(presence)) onOpenThread(t.session_id);
  };

  const confirmDelete = async () => {
    const t = toDelete;
    setToDelete(null);
    try {
      const r = await fetch(`${API}/threads/${presence}/${t.session_id}?user_id=${encodeURIComponent(userId)}`, { method: "DELETE" });
      if (!r.ok) throw new Error();
      setThreads((prev) => prev.filter((x) => x.session_id !== t.session_id));
      toast.success("Thread deleted");
      if (t.session_id === currentThread(presence)) { setOpen(false); onNewThread(); }
    } catch {
      toast.error("Couldn't delete that thread");
    }
  };

  return (
    <>
      <button
        type="button"
        data-testid="threads-open-btn"
        onClick={() => setOpen(true)}
        className="fixed left-4 bottom-28 md:bottom-auto md:top-24 z-40 flex items-center gap-2 rounded-full border border-white/15 bg-black/60 backdrop-blur-md px-4 py-2 text-xs tracking-[0.2em] uppercase text-stone-300 hover:bg-black/80 hover:text-white transition-colors duration-200"
      >
        <History className="w-4 h-4" /> Threads
      </button>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="left" data-testid="threads-sidebar" className="bg-[#0c0b0a]/95 backdrop-blur-xl border-white/10 text-stone-200 p-0 flex flex-col">
          <SheetHeader className="px-5 pt-6 pb-3 text-left">
            <SheetTitle className="text-stone-100 text-base tracking-wide">Your threads</SheetTitle>
            <SheetDescription className="text-stone-500 text-xs">Every conversation stays here. Tap one to pick it back up.</SheetDescription>
          </SheetHeader>
          <div className="px-4 pb-3">
            <button
              type="button"
              data-testid="threads-new-btn"
              onClick={() => { setOpen(false); onNewThread(); }}
              className="w-full flex items-center justify-center gap-2 rounded-full border border-white/15 px-4 py-2 text-sm text-stone-200 hover:bg-white/10 transition-colors duration-200"
            >
              <Plus className="w-4 h-4" /> New thread
            </button>
          </div>
          <div className="flex-1 overflow-y-auto px-2 pb-6" data-testid="threads-list">
            {loading && <p className="px-3 py-2 text-xs text-stone-500">Loading…</p>}
            {!loading && threads.length === 0 && (
              <p className="px-3 py-2 text-xs text-stone-500" data-testid="threads-empty">No saved threads yet.</p>
            )}
            {threads.map((t) => (
              <ThreadRow key={t.session_id} thread={t} isCurrent={t.session_id === current}
                onOpen={openThread} onDelete={setToDelete} />
            ))}
          </div>
        </SheetContent>
      </Sheet>

      <AlertDialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <AlertDialogContent data-testid="thread-delete-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this thread?</AlertDialogTitle>
            <AlertDialogDescription>
              "{toDelete?.title}" will be removed from your list. It can still be recovered later if you change your mind.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="thread-delete-cancel-btn">Cancel</AlertDialogCancel>
            <AlertDialogAction data-testid="thread-delete-confirm-btn" onClick={confirmDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

// Remounts the chamber (via key) whenever a different thread is chosen.
export const ThreadedChamber = ({ presence, render }) => {
  const [state, setState] = useState({ nonce: 0, intent: null });
  const openWith = (intent) => setState((s) => ({ nonce: s.nonce + 1, intent }));
  return (
    <>
      <ThreadSidebar
        presence={presence}
        onOpenThread={(id) => openWith({ session_id: id })}
        onNewThread={() => openWith({ new_thread: true })}
      />
      <Fragment key={state.nonce}>{render(state.intent)}</Fragment>
    </>
  );
};
