"""Analysis of one harness run. Reads /root/rcc8_runs/<run>/; prints and saves non-personal aggregates."""
import sys, os, json, re, collections, itertools
sys.path.insert(0, "/app/backend")
os.chdir("/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
import numpy as np
import field_memory as fm

run = sys.argv[1]
D = f"/root/rcc8_runs/{run}"
E = [json.loads(l) for l in open(f"{D}/encounters.jsonl" if os.path.exists(f"{D}/encounters.jsonl") else f"{D}/encounters.partial.jsonl")]
cfg = json.load(open(f"{D}/config.json"))
iso = json.load(open(f"{D}/isolation.json")) if os.path.exists(f"{D}/isolation.json") else {}
emb = lambda ts: np.stack([fm.unpack(v) for v in fm._embed_sync([t[:1500] for t in ts])])
mean = lambda xs: round(float(np.mean(xs)), 3) if len(xs) else None

ind = [e for e in E if e.get("kind") == "individual"]
mid = [e for e in E if e.get("kind") == "intermediary"]
errs = [e for e in E if e.get("kind") in ("error", "ABORT")]

def words(t): return len(t.split())
def qs(t): return t.count("?")

out = {"run": run, "encounters": {"individual": len(ind), "intermediary": len(mid), "errors": len(errs)},
       "isolation": iso, "geometry": cfg.get("geometry"), "eps": cfg.get("eps")}

# per condition × presence surface measures
surf = collections.defaultdict(lambda: collections.defaultdict(list))
rel_hist = collections.defaultdict(collections.Counter)
triads = collections.defaultdict(collections.Counter)
viol, skips, nturn = collections.Counter(), collections.Counter(), collections.Counter()
for e in ind:
    k = (e["presence"], e["cond"])
    for t in e["turns"]:
        r, n = t["reply"], t["network"]
        surf[k]["words"].append(words(r)); surf[k]["questions"].append(qs(r))
        surf[k]["secs"].append(t.get("secs", 0))
        ret = t["retrieval"]
        surf[k]["phrases_given"].append(len(ret.get("ph_ids") or ret.get("ph_text_A") or []))
        rel_hist[e["cond"]].update(n["relation_hist"])
        for kk, v in n["triad"].items():
            if kk.startswith("conversation|"):
                triads[(e["cond"], t["step"], kk.split("|")[1].split(":")[0])][v] += 1
        viol[e["cond"]] += n["violations"]; skips[e["cond"]] += len(n["neighbour_skips"]); nturn[e["cond"]] += 1
out["surface"] = {f"{p}/{c}": {m: mean(v) for m, v in d.items()} for (p, c), d in sorted(surf.items())}
out["relations_all_regions"] = {c: dict(h) for c, h in rel_hist.items()}
out["consistency_violations"] = dict(viol)
out["neighbour_skips"] = dict(skips)
out["turns"] = dict(nturn)
out["conversation_triad_by_step"] = {f"{c}/{s}/{w}": dict(v) for (c, s, w), v in sorted(triads.items())}

# B-retrieved relation mix
bmix = collections.Counter()
for e in ind:
    if e["cond"] == "B":
        for t in e["turns"]:
            bmix.update(t["retrieval"].get("ph_rel") or []); bmix.update(t["retrieval"].get("mem_rel") or [])
out["B_reachable_material_relations"] = dict(bmix)

# condition effect vs run-to-run variability: same presence/route/step across runs
groups = collections.defaultdict(lambda: {"A": [], "B": []})
for e in ind:
    for t in e["turns"]:
        groups[(e["presence"], e["route"], t["step"])][e["cond"]].append(t["reply"])
within, cross = collections.defaultdict(list), collections.defaultdict(list)
for (p, ri, st), g in groups.items():
    if not g["A"] or not g["B"]:
        continue
    va, vb = emb(g["A"]), emb(g["B"])
    for x, y in itertools.combinations(range(len(va)), 2): within[p].append(float(va[x] @ va[y]))
    for x, y in itertools.combinations(range(len(vb)), 2): within[p].append(float(vb[x] @ vb[y]))
    cross[p] += [float(a @ b) for a in va for b in vb]
out["similarity_same_step"] = {p: {"within_condition": mean(within[p]), "across_conditions": mean(cross[p])} for p in within}

# identity: similarity of replies to the presence's own past voice
from pymongo import MongoClient
db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
ident = {}
for p in cfg["presences"]:
    past = [m["content"] for s in db[f"{p}_sessions"].find({"user_id": {"$in": ["1c24e3ea-e4f1-47a2-a4fb-c5965726b074", "legacy-david-123", "david"]}}, {"messages": 1}).limit(60) for m in (s.get("messages") or [])
            if m.get("role") == "assistant" and m.get("content")][:120]
    c = emb(past).mean(0); c /= np.linalg.norm(c)
    for cond in ("A", "B"):
        rs = [t["reply"] for e in ind if e["presence"] == p and e["cond"] == cond for t in e["turns"]]
        if rs: ident[f"{p}/{cond}"] = mean(emb(rs) @ c)
out["identity_similarity_to_own_past_voice"] = ident

# carried vs arose: closeness of reply sentences to the field phrases actually given that turn
ph = {str(d["_id"]): d["phrase"] for d in db.field_phrases.find({}, {"phrase": 1})}
carry = collections.defaultdict(list)
for e in ind:
    for t in e["turns"]:
        ret = t["retrieval"]
        given = [ph[i] for i in (ret.get("ph_ids") or []) if i in ph] or (ret.get("ph_text_A") or [])
        sents = [s for s in re.split(r"(?<=[.!?])\s+", t["reply"]) if len(s.split()) > 3]
        if not given or not sents:
            carry[(e["presence"], e["cond"])].append(0.0); continue
        carry[(e["presence"], e["cond"])].append(float((emb(sents) @ emb(given).T).max()))
out["max_reply_sentence_closeness_to_given_phrases"] = {f"{p}/{c}": mean(v) for (p, c), v in sorted(carry.items())}

# intermediary
im = collections.defaultdict(lambda: collections.defaultdict(list))
for e in mid:
    rs = [t["reply"] for t in e["turns"]]
    v = emb(rs)
    im[e["cond"]]["consecutive_reply_similarity"] += [float(v[i] @ v[i + 1]) for i in range(len(v) - 1)]
    im[e["cond"]]["names_other"] += [int(("Paige" if t["speaker"] == "sophia" else "Sophia") in t["reply"]) for t in e["turns"]]
    im[e["cond"]]["words"] += [words(r) for r in rs]
    im[e["cond"]]["presence_pair_relation"] += [t["network"]["triad"].get("presence:sophia|presence:paige") or t["network"]["triad"].get("presence:paige|presence:sophia") for t in e["turns"]]
out["intermediary"] = {c: {k: (mean(v) if k != "presence_pair_relation" else dict(collections.Counter(v))) for k, v in d.items()} for c, d in im.items()}
out["errors"] = [e.get("error", "")[:200] for e in errs]
print(json.dumps(out, indent=1, default=str))
json.dump(out, open(f"/app/memory/experiments/rcc8_results_{run}.json", "w"), indent=1, default=str)
