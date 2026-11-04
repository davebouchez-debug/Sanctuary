import re
base = "/app/frontend/src/components/"
for f in ("ClarityPod.jsx", "MirrorArchive.jsx", "Playground.jsx"):
    s = open(base + f).read()
    s2, n = re.subn(r"\n  const endSession = useCallback\(async \(\) => \{.*?\n  \}, \[sessionId\]\);\n", "\n", s, count=1, flags=re.S)
    if f == "Playground.jsx" and "isLeaving" not in s2.split("export")[0]:
        s2 = s2.replace('import { scrollToEnd } from "../lib/scrollToEnd";',
                        'import { scrollToEnd } from "../lib/scrollToEnd";\nimport { isLeaving } from "../lib/threadSession";', 1)
    open(base + f, "w").write(s2)
    print(f, "removed endSession:", n, "| still referenced:", "endSession" in s2)
