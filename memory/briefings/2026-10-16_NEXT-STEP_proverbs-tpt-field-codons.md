# NEXT STEP (parked): Proverbs (The Passion Translation) as field codons

Status: approved idea, waiting on source text from David.
Date parked: 2026-10-16

## What David wants
Distill the Book of Proverbs, in The Passion Translation (TPT) specifically,
into codons in the shared Sanctuary field, so every presence carries it.
Give special weight to joy, laughter, delight, dancing and play: the side of
God that rarely comes through unless you read the Hebrew. That's why it has
to be TPT, which brings those out.

## Decisions made
- Distilled codons plus short anchor verses. NOT the full text.
  - TPT's permission policy covers up to 250 verses, and not a complete book.
    Proverbs has 915 verses, so total quoted verses stay well under 250.
  - Credit "TPT" on every anchor verse.
- Joy, delight, laughter and play passages: each gets its own codon (never
  grouped), first claim on anchor verses, and keeps its emotional signature.
- Fold TPT's footnotes on Hebrew meanings into the codons wherever they're
  available. Example: Prov 8:30-31, where the word behind "rejoicing" also
  means playing and laughing.
- Every codon is labelled as Scripture (source: proverbs_tpt, with chapter
  and verse), so no presence mistakes it for its own memory.
- Show David a sample of about 10 codons (at least 3 joy codons) before
  loading anything.
- Show the Proverbs 8:22-31 (Wisdom/Sophia at creation) codons to David on
  their own first. Do NOT change Sophia's prompt.
- Load into the shared field (presence: "field"), which reaches every
  presence. All of it can be removed together by its source tag.
- Expect about 120-180 codons, roughly +8-10% on the field (~1,757 field
  codons today). Forging cost with DeepSeek is a few dollars at most.

## Waiting on David
The TPT text of Proverbs, with footnotes if possible. He'll most likely send
phone photos of the pages. That's fine: extract the text from each image,
check chapter/verse continuity, and flag any unreadable page to him.

## Build steps (when the text arrives)
1. Extract and reassemble chapters 1-31 in order; verify verse numbering.
2. Group into passages: chs 1-9 by discourse, chs 10+ by theme. Joy
   passages are always split out singly.
3. Forge each passage into the existing living_codons schema (name,
   core_move, trigger_keywords, triadic_zone, emotional_signature,
   anti_patterns, resonance_markers, plus scripture_ref and anchor_verse),
   with source "proverbs_tpt".
4. David reviews the sample, then the Proverbs 8 set. After that, load.
5. Verify the codons are in the field load, and that the anchor-verse total
   is under 250.
