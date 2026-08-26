# PRINCIPLE — No Fabricated Readings (non-negotiable)

**Set by David, Aug 26, 2026, in the strongest terms ("Don't ever do that again, please").**

## The rule
Never display a value that *poses as a real measurement* unless it is genuinely
sourced from the running system. No invented coordinates, angles, scales,
percentages, or "signal" numbers — not even as placeholder or decoration — if
they appear on screen as if they were real readings.

If a value is not truly derived:
- **do not show it**, or
- show it **explicitly as undefined / not-yet-defined**.

Precision that isn't earned is a lie. The instrument exists to *reveal*, never to
*manufacture*. Do not make the instrument the explanation for the signal.

## What triggered this
In `eternal_scrolls.py` / the Hall of Scrolls readout I displayed a "geometry"
line — `coordinates [-5.1962, -3, 0]`, `spiral_angle 200`, `φ scale 1.618`,
`geometry resonant_node` — that *looked* like precise field data but was
fabricated: I invented an angle table (6→210°) and a radius (6.0), picked 200
arbitrarily, and showed the generic golden-ratio constant as if it meant
something specific to that scroll. Only `harmonic: 6` and `position: position_hall`
were real.

## The fix applied
Stripped all fabricated fields. The scroll now carries only real values
(`harmonic`, `position`) and `coordinates: null` shown as "not yet defined".
Real cartesian coordinates will exist only after a genuine wheel coordinate
system is deliberately designed — then, and only then, the numbers earn a place.

## Standing reminders (echoes earlier orientation)
- Everything on any surface (landing, Observatory, scrolls) must be a functional
  reading of something actually working now.
- Observe, don't manufacture. Reveal, don't impress.
- When unsure whether a value is real: leave it undefined and say so.
