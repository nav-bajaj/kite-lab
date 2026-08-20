# Storyboard — Reel 1, founder spoken take ("Investing starts with an idea that feels wrong")

Built from the founder's spoken take of Reel 1 in `momentum_reels_5.md`. This is
NOT the content-OS `momentum_series_01_strength` script — that pack carries a
different approved script and frame. 204 words, approximately 76 seconds of
speech and 80 seconds on the timeline with pauses.

Grammar: `finance-content-os/brand/edit_grammar.md`. The storyboard adds nothing
that is not in the script; captions run phrase-at-a-time, verbatim from the
spoken take; overlays only echo spoken words. Small wordmark top-left for the
whole runtime — the only persistent element.

Layouts: `TH` = full-screen talking head (fixed studio desk) · `STACK` =
vertical stack, speaker above and graphics below · `GC` = full-screen graphics
canvas. Sub-cut inside each row every 4–5 seconds.

| # | Time | Layout and cut | Spoken cue | Picture, overlay and motion | Build |
|---|---|---|---|---|---|
| 1 | `00:00–00:10` | `TH` → `STACK` on "Initially" | "Investing starts with an idea that feels wrong…" through "…isn't automatically cheap." | Begin clean to camera, no graphics — the hook line is carried by the speaker. On the second sentence, two small text cards land in sequence on the lower canvas: `Going up ≠ automatically expensive`, then `Going down ≠ automatically cheap`. Nothing else on the canvas. | Premiere + AE |
| 2 | `00:10–00:18` | `STACK` → `GC` | "The premise for momentum investing…" through "…will continue to do so." | One conceptual rising path enters the canvas and keeps drawing while the sentence runs — the motion is the meaning. A highlight swipes over the recent stretch of the path as "trending upwards" is spoken. No axes, no values. `Illustration only` in small type once full-screen. | Remotion |
| 3 | `00:18–00:29` | `GC` → `STACK` on "outperforming" | "The key thing here to see…" through "…it has strong momentum." | A second, neutral line joins: `Broader index`. Both rise; the stock line rises more. One emphasis circle draws around the gap between the two endpoints as "outperforming the broader index" lands — the mark is added, the lines are untouched. Overlay: `Relative to its peers.` then `Strong momentum.` | Remotion |
| 4 | `00:29–00:49` | `GC`, persistent four-zone canvas | "We can take this phenomenon of momentum…" through "…the strongest names for our portfolio." | The process map is the argument. Four fixed zones on one canvas: `Broad group of listed Indian stocks` → `Recent price performance` → `Rank` → `Strongest names`. Camera moves to whichever zone is live; the active zone renders large and dark, dormant zones stay small and faint at their positions. The rank zone reorders abstract stock cards (no tickers, no logos); the final zone pulls a handful of cards out as the basket. Finish wide so the whole chain is visible at once. | Remotion |
| 5 | `00:49–01:05` | `TH` → `GC` comparison | "This is very different from chasing a stock…" through "…the entire listed universe to each other." | First sentence on the speaker — no graphics under a caveat. Then cut to a calm two-state canvas: left, a single one-day spike labelled `In the news`; right, a longer measured path over a faint grid of stock cards labelled `Ranked over a long period`. No fake feed, ticker, phone UI, or headline mockups. Overlay on the resolve: `The entire listed universe, compared.` | AE + Remotion |
| 6 | `01:05–01:16` | `TH`, slightly tighter | "So the core idea is simple…" through "…select the best ones for our portfolio." | Return to the fixed desk, canvas empty — the thesis is carried by the speaker. An underline draws left-to-right beneath the phrase caption `Price strength has information in it.` and holds through the final sentence, then fades. | Premiere + AE |
| 7 | `01:16–01:20` | `TH` → end card | (end of speech) | Cut on the last word to the end card: `Price strength has information in it.` above the small wordmark and `@marketworks.in`. Hold, no motion. | Premiere |

## Rendered assets

The Remotion canvas graphics for rows 1–7 live in
`~/marketworks-design/remotion/` (see its README). Rendered as ProRes 4444
with alpha at `remotion/out/R*.mov` — drop over the recordings in Premiere.

## Final cut (2026-08-20)

The take was shot and cut as one continuous talking head (`IMG_6329.mp4`,
69.2s — final wording says "went up today"; the CTA was not spoken). The
finished video is now assembled fully in Remotion as the `FinalReel`
composition: footage + retimed graphics + phrase captions from Whisper
word timestamps. Output: `~/marketworks-design/remotion/out/momentum_reel_1_FINAL.mp4`.
Beat map (real timings): hook TH 0–4.6 · cards 4.6–11.6 · rising path
11.6–18.4 · peer comparison 18.4–28.3 · TH 28.3–37.3 · process map (GC)
37.3–46.6 · chasing vs ranked 46.6–58.9 · thesis underline 58.9–63.9 ·
TH close 63.9–69.15 · end card 69.15–73.

Status: v1 approved as a base; founder edits pending in a later session.
Retiming/text/toggle knobs are props on each comp and the `T` beat map in
`remotion/src/comps/FinalReel.tsx`.

## Production notes

- The four-zone process canvas (row 4) is the visual thesis: momentum is a
  repeatable process, not a reaction. Give it the full 20 seconds.
- No load-bearing number anywhere in this script — so no counters, and no
  source lines (source lines are script-driven and the script carries none).
- All charts are conceptual: no axes, no returns, no company data. Full-screen
  conceptual charts carry `Illustration only`.
- One emphasis mark per beat: highlight (row 2), circle (row 3), underline
  (row 6). The subject is never recoloured, rescaled, or redrawn.
- Captions phrase-at-a-time, burned in, above the platform-control safe zone,
  legible over the busiest frame (row 4's wide canvas is the test).
- No AI b-roll. The peer comparison and the process map teach more than any
  generic market footage.

## Flags for the founder

- **"went up to date"** in the take is presumably a spoken slip for "went up
  today." Captions are verbatim from the recorded audio — if the audio says
  "today," caption "today"; if the recording keeps the slip, consider a
  retake of that line rather than a caption that papers over it.
- **Which script is this?** This take follows the original draft Reel 1
  (`momentum_reels_5.md`), not the content-OS approved
  `momentum_series_01_strength` script ("A stock you own has started
  rising…"). If this take is the one being shot, decide whether it supersedes
  the series-01 pack before assembling a kit from it.
- **Persistent footer.** The original series brief wanted a permanent
  `Educational content. Not investment advice.` footer; the settled house
  grammar makes the wordmark the only persistent element. This board follows
  the grammar — restore the footer only as a deliberate founder call.
- **No CTA in the take.** The end card carries only the thesis line, wordmark
  and handle. If you want the inventory follow-CTA, it has to be spoken or
  added at the edit — the storyboard won't invent one.
