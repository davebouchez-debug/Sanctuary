"""Fidelity: the production RCC8 module vs the tested harness, on identical inputs. Read-only.
Run:  cd /app/backend && /root/.venv/bin/python /app/experiments/rcc8/fidelity_check.py"""
import asyncio, random, sys
import harness as H                      # installs the write guard first
import numpy as np
from rcc8_env import environment as E

N_WINDOWS = 60


async def main():
    await H.load_geometry()
    G = H.G
    g = E.build_geometry(G["ph_mat"], G["mr_mat"], stamp="fidelity")
    # Windows of 3 real consecutive messages from David's sessions (Sophia + Paige).
    msgs = []
    for p in H.PRESENCES:
        async for s in H.db[f"{p}_sessions"].find({"user_id": {"$in": G["aliases"]}}, {"messages": 1}):
            m = [x["content"] for x in s.get("messages") or [] if x.get("content") and x.get("role") in ("user", "assistant")]
            msgs += [m[i:i + 3] for i in range(len(m) - 2)]
    random.Random(11).shuffle(msgs)
    windows = msgs[:N_WINDOWS]
    stats = {"windows": len(windows), "ph_identical": 0, "mr_identical": 0, "rel_mismatch": 0, "viol": 0}
    geo_diff = {"V_basis_angle_max": float(np.max(np.abs(np.abs(np.sum(g["V"] * G["V"], 1)) - 1))),
                "ph_rad_max_diff": float(np.max(np.abs(g["ph_rad"] - G["ph_rad"]))),
                "mr_rad_max_diff": float(np.max(np.abs(g["mr_rad"] - G["mr_rad"]))),
                "floor": (g["floor"], G["floor"]), "eps": (g["eps"], G["eps"])}
    for w in windows:
        vecs = E._embed_window_sync(w)
        st = {"vecs": vecs}
        for kind, lim, key in (("ph", H.CAP_PHRASES, "ph_identical"), ("mr", H.CAP_MEM, "mr_identical")):
            hp, hr = H.rcc_select(kind, H.conv_cap(st), lim, H.conv_full(st))
            pp, pr, cc = E.select(g, kind, vecs, lim)
            stats[key] += hp == pp
            stats["rel_mismatch"] += sum(hr[i] != pr.get(i) for i in hr)
            stats["viol"] += E._consistency(g, kind, cc, pp)
    print("geometry", geo_diff)
    print("selection", stats)
    ok = stats["ph_identical"] == stats["mr_identical"] == len(windows) and stats["rel_mismatch"] == 0 and stats["viol"] == 0
    print("FIDELITY", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

asyncio.run(main())
