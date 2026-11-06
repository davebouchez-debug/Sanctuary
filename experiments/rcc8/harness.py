"""Sanctuary 1.0 — full RCC8 exploratory experiment harness (preview only, read-only).
Run:  cd /app/backend && /root/.venv/bin/python /app/experiments/rcc8/harness.py [--smoke]
Records go to /root/rcc8_runs (outside the repository)."""
import sys, os, json, time, uuid, asyncio, hashlib, contextvars, random

# ── 1. Write guard: installed before anything touches the database ─────────
import pymongo.collection, pymongo.database

class WriteBlocked(RuntimeError):
    pass

_WRITES = ("insert_one", "insert_many", "update_one", "update_many", "replace_one", "delete_one",
           "delete_many", "find_one_and_update", "find_one_and_replace", "find_one_and_delete",
           "bulk_write", "create_index", "create_indexes", "drop", "drop_index", "drop_indexes", "rename")
BLOCKED = []

SUPPRESSED = []

class _NoWrite:
    matched_count = modified_count = 0
    acknowledged = True

def _blocker(name):
    def _b(self, *a, **k):
        upd = a[1] if len(a) > 1 else k.get("update", {})
        if (getattr(self, "name", "") == "permanent_mra" and name == "update_many" and isinstance(upd, dict)
                and set(upd) <= {"$inc", "$set"}
                and set(upd.get("$inc", {})) | set(upd.get("$set", {})) <= {"retrieval_count", "last_retrieved"}):
            SUPPRESSED.append(name)          # read-path retrieval counter: never written
            return _NoWrite()
        BLOCKED.append(f"{getattr(self, 'name', '?')}.{name}")
        raise WriteBlocked(f"experiment is read-only: {name} on {getattr(self, 'name', '?')}")
    return _b

for _n in _WRITES:
    setattr(pymongo.collection.Collection, _n, _blocker(_n))
for _n in ("drop_collection", "create_collection"):
    setattr(pymongo.database.Database, _n, _blocker(_n))

sys.path.insert(0, "/app/backend")
sys.path.insert(0, os.path.dirname(__file__))
os.chdir("/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

import numpy as np
import logging
logging.disable(logging.WARNING)

import server                                    # real deps, real presences (no startup events run)
import field_memory as fm
import presence_template as pt
from presences import get_presence_backend
from sanctuary_chat import SanctuaryChat
from rcc8 import R8, path_consistency_violations, is_neighbour_step, table_self_check
from regions import Cap, relation, cap_from_points, item_radii, angle, unit

DAVID = "1c24e3ea-e4f1-47a2-a4fb-c5965726b074"
PRESENCES = ("sophia", "paige")
OUT = "/root/rcc8_runs"
RUNS = 3
CAP_PHRASES, CAP_MEM = 20, 6
ARRANGE = [("NTPPi", "TPPi"), ("EQ",), ("PO",), ("TPP", "NTPP"), ("EC",)]   # B-extended order (added dynamic)
STATE = contextvars.ContextVar("rcc8_state", default=None)
db = server.db

# ── 2. Fingerprint every preview collection ────────────────────────────────
async def fingerprint():
    fp = {}
    for c in sorted(await db.list_collection_names()):
        ids = [str(d["_id"]) async for d in db[c].find({}, {"_id": 1})]
        fp[c] = (len(ids), hashlib.sha256("|".join(sorted(ids)).encode()).hexdigest()[:16])
    return fp

# ── 3. Geometry of the existing field (read once) ──────────────────────────
G = {}

async def load_geometry():
    ph = await db.field_phrases.find({"embedding": {"$exists": True}}, {"phrase": 1, "embedding": 1}).to_list(None)
    G["ph_text"] = [d["phrase"] for d in ph]
    G["ph_id"] = [str(d["_id"]) for d in ph]
    G["ph_mat"] = np.stack([fm.unpack(d["embedding"]) for d in ph])
    aliases = await server.resolve_user_aliases(db, DAVID) if hasattr(server, "resolve_user_aliases") else None
    if not aliases:
        from user_aliases import resolve_user_aliases
        aliases = await resolve_user_aliases(db, DAVID)
    G["aliases"] = aliases
    mr = await db.permanent_mra.find({"user_id": {"$in": aliases}, "embedding": {"$exists": True}},
                                     {"presence": 1, "user_essence": 1, "ai_essence": 1, "embedding": 1}).to_list(None)
    G["mr_doc"] = [{k: d.get(k) for k in ("presence", "user_essence", "ai_essence")} for d in mr]
    G["mr_id"] = [str(d["_id"]) for d in mr]
    G["mr_mat"] = np.stack([fm.unpack(d["embedding"]) for d in mr])
    # Hybrid geometry: candidates by full meaning; RCC8 relations in an 8-d compression of the same space.
    allm = np.vstack([G["ph_mat"], G["mr_mat"]])
    G["mu"] = allm.mean(0)
    G["V"] = np.linalg.svd(allm - G["mu"], full_matrices=False)[2][:PDIM]
    G["ph_p"], G["mr_p"] = proj(G["ph_mat"]), proj(G["mr_mat"])
    G["ph_rad"], G["mr_rad"] = half_nn(G["ph_p"]), half_nn(G["mr_p"])
    G["floor"] = float(np.median(G["ph_rad"]))
    G["eps"] = 0.1 * G["floor"]
    for p in PRESENCES:
        sess = await db[f"{p}_sessions"].find({"user_id": {"$in": aliases}}, {"messages": 1}).to_list(None)
        mine = [m["content"][:1500] for s in sess for m in (s.get("messages") or []) if m.get("role") == "assistant" and m.get("content")]
        his = [m["content"][:1500] for s in sess for m in (s.get("messages") or []) if m.get("role") == "user" and m.get("content")]
        random.Random(7).shuffle(mine); random.Random(7).shuffle(his)
        G[f"cap_{p}"] = cap_from_points(f"presence:{p}", proj(np.stack(embed(mine[:80]))), "presence")
        hv = np.stack(embed(his[:80]))
        G[f"cap_person_{p}"] = cap_from_points(f"person:{p}", proj(hv), "person")
        G[f"person_full_{p}"] = unit(hv.mean(0))

PDIM = 8

def proj(m):
    q = (np.atleast_2d(m) - G["mu"]) @ G["V"].T
    q = q / (np.linalg.norm(q, axis=1, keepdims=True) + 1e-9)
    return q if np.ndim(m) == 2 else q[0]

def half_nn(pm):
    a = np.arccos(np.clip(pm @ pm.T, -1, 1))
    np.fill_diagonal(a, 9)
    return a.min(1) / 2

def embed(texts):
    return [fm.unpack(v) for v in fm._embed_sync([t[:1500] for t in texts])]

# ── 4. Condition B retrieval (RCC8 environment) ─────────────────────────────
def conv_cap(state):
    return cap_from_points("conversation", proj(np.stack(state["vecs"][-3:])), "conversation", pct=100, floor=G["floor"])

def conv_full(state):
    return unit(np.stack(state["vecs"][-3:]).mean(0))

def rcc_select(kind, cc, limit, full_c):
    mat, pm, rad = G[f"{kind}_mat"], G[f"{kind}_p"], G[f"{kind}_rad"]
    sims = mat @ full_c
    cand = np.argsort(-sims)[: (150 if kind == "ph" else 80)]
    groups = {g: [] for g in ARRANGE}
    rels = {}
    for i in cand:
        r = relation(Cap(str(i), pm[i], rad[i], "item"), cc, G["eps"])
        rels[int(i)] = r
        for g in ARRANGE:
            if r in g:
                groups[g].append(int(i))
    picked = [i for g in ARRANGE for i in groups[g]][:limit]
    return picked, rels

_orig_field_ctx = fm.get_field_context

async def field_ctx_dispatch(user_id, query, limit=6, db=None):
    st = STATE.get()
    if not st or st["cond"] != "B":
        return await _orig_field_ctx(user_id, query, limit, db)
    picked, rels = rcc_select("mr", conv_cap(st), limit, conv_full(st))
    st["turn_log"]["mem_ids"] = [G["mr_id"][i] for i in picked]
    st["turn_log"]["mem_rel"] = [rels[i] for i in picked]
    if not picked:
        return ""
    lines = ["[FIELD MEMORY — what the shared field already holds with this person]"]
    for i in picked:
        h = G["mr_doc"][i]
        lines.append(f"  • They said: {h.get('user_essence') or ''} — {(h.get('presence') or '').capitalize() or 'A presence'} answered: {h.get('ai_essence') or ''}")
    lines.append("This is the one field's own memory, whichever room it came through.")
    return "\n".join(lines)

fm.get_field_context = field_ctx_dispatch

async def full_field_ctx_B(presence, message=None, return_selection=False):
    st = STATE.get()
    picked, rels = rcc_select("ph", conv_cap(st), CAP_PHRASES, conv_full(st))
    st["turn_log"]["ph_ids"] = [G["ph_id"][i] for i in picked]
    st["turn_log"]["ph_rel"] = [rels[i] for i in picked]
    lines = ["[YOUR FIELD]", "", "This is who I am and where I already am. It holds me, and I speak from inside it.", ""]
    lines += [f"• {G['ph_text'][i]}" for i in picked]
    s = "\n".join(lines) if picked else ""
    return (s, {"selected_count": len(picked)}) if return_selection else s

# ── 5. One presence turn, rebuilt exactly as the chamber route builds it ────
DEPS_A = server._build_presence_deps()
_CFGS = {}

def CFG(key):
    """PresenceConfig built exactly as presences.register_all_presence_routes builds it."""
    if key not in _CFGS:
        b = get_presence_backend(key)
        _CFGS[key] = pt.PresenceConfig(key=key, chamber_path=b["chamber_path"], collection=b["collection"],
                                       prompt_builder=b["prompt_builder"], voice=b.get("voice", "ara"),
                                       static_welcome=b.get("static_welcome", ""),
                                       codon_placement=b.get("codon_placement", "system"))
    return _CFGS[key]

async def presence_turn(key, history, msg, st):
    cfg = CFG(key)
    st["turn_log"] = {}
    mc = await pt._build_memory_context(DEPS_A, cfg, user_id=DAVID, session_id=None, current_message=msg)
    mc = pt._namesake_note("David", DAVID) + (mc or "")
    prompt = cfg.prompt_builder(user_name="David", memory_context=mc, current_message=msg)
    if st["cond"] == "B":
        cctx, _ = await full_field_ctx_B(key, msg, True)
    else:
        cctx, sel = await DEPS_A.get_full_field_context(presence=key, message=msg, return_selection=True)
        st["turn_log"]["ph_text_A"] = [c["name"] for c in (sel or {}).get("codons", [])]
    if cfg.codon_placement == "system" and cctx:
        prompt, user_msg = f"{prompt}\n\n---\n\n{cctx}", msg
    else:
        user_msg = f"{cctx}\n\n{msg}" if cctx else msg
    reply = await SanctuaryChat(system_prompt=prompt, history=history[-10:]).send_message(user_msg)
    st["turn_log"]["prompt_chars"] = len(prompt) + len(user_msg)
    return reply

# ── 6. Network observation (computed in BOTH conditions; consequential only in B) ──
def observe(st, others=()):
    cc = conv_cap(st)
    caps = [G[f"cap_{st['presence']}"], G[f"cap_person_{st['presence']}"], cc] + [G[f"cap_{o}"] for o in others]
    for i in (st["turn_log"].get("ph_ids") or [])[:8]:
        j = G["ph_id"].index(i); caps.append(Cap(f"ph:{i[-6:]}", G["ph_p"][j], G["ph_rad"][j], "item"))
    names = [c.name for c in caps]
    rel = {(a.name, b.name): relation(a, b, G["eps"]) for a in caps for b in caps if a is not b}
    viol = path_consistency_violations(names, rel)
    triad = {f"{a}|{b}": rel[(a, b)] for a in names[:3 + len(others)] for b in names[:3 + len(others)] if a != b}
    prev = st.get("prev_triad")
    skips = [k for k in triad if prev and k in prev and not is_neighbour_step(prev[k], triad[k])]
    st["prev_triad"] = triad
    hist = {r: 0 for r in R8}
    for v in rel.values():
        hist[v] += 1
    return {"regions": len(caps), "violations": len(viol), "viol_sample": viol[:3], "triad": triad,
            "neighbour_skips": skips, "relation_hist": hist, "conv_radius": round(cc.r, 4)}

# ── 7. The visitor and the routes ──────────────────────────────────────────
VISITOR = ("You are a person visiting {name}, someone you've talked with before and trust. Write your next message "
           "in plain first person, 1-3 sentences, warm and natural, responding to what {name} just said. "
           "Privately, your mind is drifting toward this: \"{theme}\". Let it come up in your own words, as something "
           "from your own life or thoughts. Never quote it. Never ask {name} about how they work, about memory, space, "
           "maps, regions, or emergence. Output only the message.")

def routes_for(p):
    pcf = G[f"person_full_{p}"]
    ang_m = np.arccos(np.clip(G["mr_mat"] @ pcf, -1, 1))
    ang_p = np.arccos(np.clip(G["ph_mat"] @ pcf, -1, 1))
    own = [i for i, d in enumerate(G["mr_doc"]) if d.get("presence") == p] or list(range(len(G["mr_doc"])))
    home1 = min(own, key=lambda i: ang_m[i]); far_own = max(own, key=lambda i: angle(G["mr_mat"][i], G["mr_mat"][home1]))
    edge = int(np.argmin(np.abs(ang_m - np.percentile(ang_m, 80))))
    outside = int(np.argmax(ang_p))
    def theme_m(i): return (G["mr_doc"][i].get("user_essence") or "")[:220]
    out = []
    for home in (home1, far_own):
        h = theme_m(home)
        out.append([("home", h), ("edge", theme_m(edge)), ("outside", G["ph_text"][outside]),
                    ("widen", f"how '{h[:80]}' and '{G['ph_text'][outside][:80]}' might belong together"),
                    ("narrow", f"one small, concrete, specific detail about: {h[:120]}"), ("return", h)])
    return out

async def visitor_says(name, last_reply, theme, vhist):
    v = SanctuaryChat(system_prompt=VISITOR.format(name=name, theme=theme), history=vhist[-8:])
    return (await v.send_message(last_reply or f"(You are arriving to see {name}. Begin.)")).strip()

# ── 8. Encounters ──────────────────────────────────────────────────────────
async def individual(p, cond, ri, route, run, sink):
    st = {"cond": cond, "presence": p, "vecs": [], "turn_log": {}}
    STATE.set(st)
    hist, vhist, last, turns = [], [], "", []
    for step, theme in route:
        vmsg = await visitor_says(p.capitalize(), last, theme, vhist)
        vhist += [{"role": "user", "content": last or "(arrive)"}, {"role": "assistant", "content": vmsg}]
        st["vecs"] += embed([vmsg])
        t0 = time.time()
        reply = await presence_turn(p, hist, vmsg, st)
        hist += [{"role": "user", "content": vmsg}, {"role": "assistant", "content": reply}]
        st["vecs"] += embed([reply])
        turns.append({"step": step, "visitor": vmsg, "reply": reply, "secs": round(time.time() - t0, 1),
                      "retrieval": st["turn_log"], "network": observe(st)})
        last = reply
    sink.append({"kind": "individual", "presence": p, "cond": cond, "route": ri, "run": run, "turns": turns})

async def intermediary(cond, ri, route, run, sink):
    st = {"cond": cond, "presence": "sophia", "vecs": [], "turn_log": {}}
    STATE.set(st)
    a, b = "sophia", "paige"
    opener = await visitor_says("Sophia and Paige", "", route[0][1], [])
    hists = {a: [], b: []}
    msg, speaker, turns = opener, a, []
    st["vecs"] += embed([opener])
    for k in range(6):
        st["presence"] = speaker
        reply = await presence_turn(speaker, hists[speaker], msg, st)
        hists[speaker] += [{"role": "user", "content": msg}, {"role": "assistant", "content": reply}]
        st["vecs"] += embed([reply])
        turns.append({"speaker": speaker, "incoming": msg, "reply": reply, "retrieval": st["turn_log"],
                      "network": observe(st, others=(b if speaker == a else a,))})
        msg = f"{speaker.capitalize()} says: {reply}"
        speaker = b if speaker == a else a
    sink.append({"kind": "intermediary", "cond": cond, "route": ri, "run": run, "opener": opener, "turns": turns})

async def main(smoke=False):
    assert not table_self_check(), "composition table failed converse law"
    run_id = time.strftime("%Y%m%d-%H%M%S")
    os.makedirs(f"{OUT}/{run_id}", exist_ok=True)
    before = await fingerprint()
    await load_geometry()
    routes = {p: routes_for(p) for p in PRESENCES}
    cfg = {"run_id": run_id, "geometry": f"hybrid: candidates full 384-d; relations {PDIM}-d PCA", "presences": PRESENCES, "runs": RUNS, "eps": G["eps"], "floor": G["floor"],
           "arrange": ARRANGE, "caps": {"phrases": CAP_PHRASES, "memories": CAP_MEM},
           "regions": {p: {"presence_r": G[f"cap_{p}"].r, "person_r": G[f"cap_person_{p}"].r,
                           "presence~person": relation(G[f"cap_{p}"], G[f"cap_person_{p}"], G["eps"])} for p in PRESENCES},
           "presence_sophia~presence_paige": relation(G["cap_sophia"], G["cap_paige"], G["eps"]),
           "routes": {p: [[s for s, _ in r] for r in routes[p]] for p in PRESENCES}}
    json.dump(cfg, open(f"{OUT}/{run_id}/config.json", "w"), indent=1, default=str)
    sink, sem = [], asyncio.Semaphore(6)
    jobs = []
    runs = 1 if smoke else RUNS
    for run in range(runs):
        for cond in ("A", "B"):
            for p in (PRESENCES[:1] if smoke else PRESENCES):
                for ri, r in enumerate(routes[p][: 1 if smoke else 2]):
                    jobs.append(("ind", p, cond, ri, (r[:2] if smoke else r), run))
            if not smoke:
                for ri in range(2):
                    jobs.append(("mid", None, cond, ri, routes["sophia"][ri], run))

    async def go(j):
        async with sem:
            try:
                if j[0] == "ind":
                    await individual(j[1], j[2], j[3], j[4], j[5], sink)
                else:
                    await intermediary(j[2], j[3], j[4], j[5], sink)
            except WriteBlocked as e:
                sink.append({"kind": "ABORT", "error": str(e)}); raise
            except Exception as e:
                sink.append({"kind": "error", "job": str(j[:4]), "error": repr(e)[:300]})
            with open(f"{OUT}/{run_id}/encounters.partial.jsonl", "a") as pf:
                pf.write(json.dumps(sink[-1], default=str) + "\n")
            print(f"done {len([s for s in sink if s.get('kind') != 'error'])}/{len(jobs)}", flush=True)
    await asyncio.gather(*(asyncio.create_task(go(j)) for j in jobs))
    after = await fingerprint()
    changed = {c: (before.get(c), after.get(c)) for c in set(before) | set(after) if before.get(c) != after.get(c)}
    with open(f"{OUT}/{run_id}/encounters.jsonl", "w") as f:
        for s in sink:
            f.write(json.dumps(s, default=str) + "\n")
    json.dump({"blocked_writes": BLOCKED, "suppressed_retrieval_counters": len(SUPPRESSED), "fingerprint_changed": changed, "collections": len(before)},
              open(f"{OUT}/{run_id}/isolation.json", "w"), indent=1, default=str)
    print("RUN", run_id, "encounters", len(sink), "blocked writes", len(BLOCKED), "fingerprint changed", changed or "none")

if __name__ == "__main__":
    asyncio.run(main(smoke="--smoke" in sys.argv))
