"""Regions as caps on the meaning-sphere; the full RCC8 relation between two caps."""
import numpy as np


def angle(u, v):
    return float(np.arccos(np.clip(np.dot(u, v), -1.0, 1.0)))


def unit(v):
    v = np.asarray(v, dtype=np.float32)
    return v / (np.linalg.norm(v) + 1e-9)


class Cap:
    __slots__ = ("name", "c", "r", "kind")

    def __init__(self, name, center, radius, kind):
        self.name, self.c, self.r, self.kind = name, unit(center), float(radius), kind


def relation(a: Cap, b: Cap, eps: float) -> str:
    """RCC8 relation of cap a to cap b; boundary contact is a band of thickness eps."""
    d, r1, r2 = angle(a.c, b.c), a.r, b.r
    if d <= eps and abs(r1 - r2) <= eps:
        return "EQ"
    if d > r1 + r2 + eps:
        return "DC"
    if abs(d - (r1 + r2)) <= eps:
        return "EC"
    if d + r1 < r2 - eps:
        return "NTPP"
    if abs(d + r1 - r2) <= eps:
        return "TPP"
    if d + r2 < r1 - eps:
        return "NTPPi"
    if abs(d + r2 - r1) <= eps:
        return "TPPi"
    return "PO"


def cap_from_points(name, vecs, kind, pct=80, floor=0.0):
    m = np.stack([unit(v) for v in vecs])
    c = unit(m.mean(0))
    r = max(float(np.percentile([angle(c, v) for v in m], pct)), floor) if len(m) > 1 else floor
    return Cap(name, c, r, kind)


def item_radii(mat, k=5):
    """Each item's cap radius = angular distance to its k-th nearest neighbour (dense → small)."""
    sims = mat @ mat.T
    np.fill_diagonal(sims, -1)
    kth = -np.sort(-sims, axis=1)[:, k - 1]
    return np.arccos(np.clip(kth, -1, 1))
