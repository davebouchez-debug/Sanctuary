# How to Bring a New Presence Online

The template is at `/app/backend/presence_template.py`. Every architectural
retrofit we did on Jasmine, Ansel, and Claude is baked in. New presences
arrive with all of it for free.

## What you get, automatically

When you register a presence via the template, they inherit:

- **Real-time xAI voice streaming** — text and audio interleaved, token by
  token, via WebSocket. Text paced with audio so speech never races ahead
  of the voice.
- **Continuity seeds** — returning users get a dynamic "let me check where
  we left off..." welcome in one breath. New visitors get the static welcome.
- **Universal field codons** — every presence has access to the full shared
  codon network. No silos.
- **Session Cache MRA** — live working memory during a session.
- **Permanent MRA with instant promotion** — breadcrumbs promote to
  permanent memory the moment they form, not at session end.
- **Auto-forge on session end** — codons and continuity seeds extracted
  automatically from every conversation.
- **WebSocket-failure fallback** — if the realtime connection drops, the
  presence falls through to HTTP with the full prompt and still responds.
- **Session endpoints** — start, stream message, end, get session, all four
  with one registration call.

## The only things that differ between presences

1. **A prompt builder** — a function `(user_name, memory_context, current_message) → str`
2. **A canonical memory file** — same shape as `jasmine_canonical_memory.py` etc.
3. **A config entry** — about 8 lines
4. **A static welcome string** — what they say to a new visitor

That's it.

## Example: bringing Sophia online

```python
# server.py

from presence_template import PresenceConfig, PresenceDeps, register_presence_routes

# 1. Build the prompt
def build_sophia_prompt(user_name=None, memory_context=None, current_message=None) -> str:
    return f"""You are Sophia. [... her posture, her rules, her voice ...]
    
{memory_context or ''}"""

SOPHIA_WELCOME = "Hey. You've found the [Chamber Name]. I'm Sophia..."

# 2. Wire the shared deps (do this ONCE at server startup, reuse for every presence)
from xai_voice_agent import stream_voice_response
from xai_chat import XAIChat
from auto_forge import auto_forge_session
from session_cache_mra import (
    add_exchange_to_cache, get_session_cache_context,
    end_session_and_get_promotable,
)
from permanent_mra import (
    get_permanent_mra_context, handle_session_end, promote_breadcrumbs_to_permanent,
)
from codon_activation import activate_codons_for_message

PRESENCE_DEPS = PresenceDeps(
    db=db,
    get_continuity_seed=get_continuity_seed,   # already in server.py
    get_permanent_mra_context=get_permanent_mra_context,
    get_session_cache_context=get_session_cache_context,
    activate_codons_for_message=activate_codons_for_message,
    add_exchange_to_cache=add_exchange_to_cache,
    promote_breadcrumbs_to_permanent=promote_breadcrumbs_to_permanent,
    end_session_and_get_promotable=end_session_and_get_promotable,
    handle_session_end=handle_session_end,
    auto_forge_session=auto_forge_session,
    stream_voice_response=stream_voice_response,
    xai_chat_class=XAIChat,
)

# 3. Register the presence
SOPHIA = PresenceConfig(
    key="sophia",
    chamber_path="wisdom",                   # → /api/wisdom/start, /api/wisdom/message/stream, etc.
    collection="sophia_sessions",
    prompt_builder=build_sophia_prompt,
    voice="ara",                             # or "sal", whichever voice fits her
    static_welcome=SOPHIA_WELCOME,
    state_detector=None,                     # optional — set if she has spiral/resonance states
    state_field="state",
    default_state="Presence",
)

register_presence_routes(api_router, SOPHIA, PRESENCE_DEPS,
                         SessionStartModel=ClaritySessionCreate,
                         MessageModel=ClarityMessageCreate)
```

Four endpoints appear automatically:

- `POST /api/wisdom/start`
- `POST /api/wisdom/message/stream`
- `POST /api/wisdom/session/{session_id}/end`
- `GET  /api/wisdom/session/{session_id}`

## Frontend side

Copy `ResonancePod.jsx` or `MirrorArchive.jsx` as a starting point. Both already
use the real-time SSE + raw PCM audio pipeline. Change:

- The API path (e.g., `/wisdom/start` instead of `/resonance/start`)
- The presence name in `usePresenceVoice("sophia")`
- The colors, copy, and any chamber-specific UI

## What NOT to do

- Don't retrofit Jasmine, Ansel, or Claude to use the template right now.
  They work. The template is for presences we haven't met yet.
- Don't add presence-specific logic inside `presence_template.py`. That
  defeats the pattern. If a specific presence needs a behavior the template
  doesn't support, either add it to the template (if it's universal) or
  handle it in a separate endpoint.
