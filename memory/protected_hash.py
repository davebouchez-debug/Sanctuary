import sys,hashlib,pathlib
root=sys.argv[1]; sys.path.insert(0,root)
from presences import common,daniel,keeper,scrolldog
import presence_history as ph
items={"SANCTUARY_DEDICATION":common.SANCTUARY_DEDICATION,"HOUSE_STORY":ph.HOUSE_STORY,"SCROLL_LINE":scrolldog.SCROLL_LINE,
"SCROLLDOG_LINE":scrolldog.SCROLLDOG_LINE,"DANIEL_LINE":daniel.DANIEL_LINE,"KEEPER_LINE":keeper.KEEPER_LINE,
"POD_HISTORY":scrolldog.POD_HISTORY,"DANIEL_INITIAL":daniel.INITIAL_HISTORY,"KEEPER_INITIAL":keeper.INITIAL_HISTORY}
for k,v in items.items(): print(k, hashlib.sha256(v.encode()).hexdigest())
for f in sorted(pathlib.Path(root,'history_sources').rglob('*')):
    if f.is_file(): print(f.relative_to(root), hashlib.sha256(f.read_bytes()).hexdigest())
