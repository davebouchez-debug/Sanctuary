"""RCC8 — relations, converses, composition table, path-consistency, conceptual neighbourhood.
Pure mathematics; knows nothing about Sanctuary."""
from itertools import product

R8 = ("DC", "EC", "PO", "EQ", "TPP", "NTPP", "TPPi", "NTPPi")
U = frozenset(R8)
CONV = {"DC": "DC", "EC": "EC", "PO": "PO", "EQ": "EQ",
        "TPP": "TPPi", "NTPP": "NTPPi", "TPPi": "TPP", "NTPPi": "NTPP"}

_S = lambda s: frozenset(s.split())
# Standard RCC8 composition table (Randell, Cui & Cohn 1992): COMP[R(a,b)][R(b,c)] -> possible R(a,c).
COMP = {
    "DC":   {"DC": U, "EC": _S("DC EC PO TPP NTPP"), "PO": _S("DC EC PO TPP NTPP"), "TPP": _S("DC EC PO TPP NTPP"),
             "NTPP": _S("DC EC PO TPP NTPP"), "TPPi": _S("DC"), "NTPPi": _S("DC"), "EQ": _S("DC")},
    "EC":   {"DC": _S("DC EC PO TPPi NTPPi"), "EC": _S("DC EC PO TPP TPPi EQ"), "PO": _S("DC EC PO TPP NTPP"),
             "TPP": _S("EC PO TPP NTPP"), "NTPP": _S("PO TPP NTPP"), "TPPi": _S("DC EC"), "NTPPi": _S("DC"), "EQ": _S("EC")},
    "PO":   {"DC": _S("DC EC PO TPPi NTPPi"), "EC": _S("DC EC PO TPPi NTPPi"), "PO": U, "TPP": _S("PO TPP NTPP"),
             "NTPP": _S("PO TPP NTPP"), "TPPi": _S("DC EC PO TPPi NTPPi"), "NTPPi": _S("DC EC PO TPPi NTPPi"), "EQ": _S("PO")},
    "TPP":  {"DC": _S("DC"), "EC": _S("DC EC"), "PO": _S("DC EC PO TPP NTPP"), "TPP": _S("TPP NTPP"), "NTPP": _S("NTPP"),
             "TPPi": _S("DC EC PO TPP TPPi EQ"), "NTPPi": _S("DC EC PO TPPi NTPPi"), "EQ": _S("TPP")},
    "NTPP": {"DC": _S("DC"), "EC": _S("DC"), "PO": _S("DC EC PO TPP NTPP"), "TPP": _S("NTPP"), "NTPP": _S("NTPP"),
             "TPPi": _S("DC EC PO TPP NTPP"), "NTPPi": U, "EQ": _S("NTPP")},
    "TPPi": {"DC": _S("DC EC PO TPPi NTPPi"), "EC": _S("EC PO TPPi NTPPi"), "PO": _S("PO TPPi NTPPi"),
             "TPP": _S("PO TPP TPPi EQ"), "NTPP": _S("PO TPP NTPP"), "TPPi": _S("TPPi NTPPi"), "NTPPi": _S("NTPPi"), "EQ": _S("TPPi")},
    "NTPPi": {"DC": _S("DC EC PO TPPi NTPPi"), "EC": _S("PO TPPi NTPPi"), "PO": _S("PO TPPi NTPPi"),
              "TPP": _S("PO TPPi NTPPi"), "NTPP": _S("PO TPP NTPP TPPi NTPPi EQ"), "TPPi": _S("NTPPi"),
              "NTPPi": _S("NTPPi"), "EQ": _S("NTPPi")},
    "EQ":   {r: frozenset([r]) for r in R8},
}

# Conceptual neighbourhood: which relations can follow directly under continuous change.
NEIGH = {"DC": {"EC"}, "EC": {"DC", "PO"}, "PO": {"EC", "TPP", "TPPi", "EQ"},
         "TPP": {"PO", "NTPP", "EQ"}, "NTPP": {"TPP", "EQ"}, "TPPi": {"PO", "NTPPi", "EQ"},
         "NTPPi": {"TPPi", "EQ"}, "EQ": {"PO", "TPP", "NTPP", "TPPi", "NTPPi"}}


def table_self_check():
    """Converse law: conv(a∘b) == conv(b)∘conv(a). Catches transcription errors in COMP."""
    bad = []
    for a, b in product(R8, R8):
        lhs = frozenset(CONV[r] for r in COMP[a][b])
        rhs = COMP[CONV[b]][CONV[a]]
        if lhs != rhs:
            bad.append((a, b, sorted(lhs), sorted(rhs)))
    return bad


def path_consistency_violations(names, rel):
    """rel[(i,j)] is a single base relation for every ordered pair. Returns triples where
    R(i,k) is not among the relations R(i,j)∘R(j,k) allows."""
    out = []
    for i, j, k in product(names, names, names):
        if len({i, j, k}) < 3:
            continue
        if rel[(i, k)] not in COMP[rel[(i, j)]][rel[(j, k)]]:
            out.append((i, j, k, rel[(i, j)], rel[(j, k)], rel[(i, k)]))
    return out


def is_neighbour_step(a, b):
    return a == b or b in NEIGH[a]
