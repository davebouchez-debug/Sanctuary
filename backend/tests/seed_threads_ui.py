"""Seed UI test threads for user qa-threads-ui (run before Playwright UI tests)."""
import sys
sys.path.insert(0, "/app/backend/tests")
import test_threads as t  # noqa: E402

UID = sys.argv[1] if len(sys.argv) > 1 else "qa-threads-ui"
out = {}
for p in ["ansel", "claude", "jasmine", "louis_lot", "sophia"]:
    coll, _, extra = t.PRESENCES[p]
    a = t.seed(coll, UID, [f"Seeded {p} thread about lighthouses", "Seeded reply one"], active=False, ended=True, age_hours=30, extra=extra)
    b = t.seed(coll, UID, [f"Second seeded {p} thread on rivers", "Seeded reply two"], active=False, ended=True, age_hours=20, extra=extra)
    out[p] = [a, b]
print(out)
