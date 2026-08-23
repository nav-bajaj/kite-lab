# Corporate-action adjustments — root cause and fix

Opened 2026-08-23 after three research studies found unadjusted
corporate actions in `nse500_data_merged` (36 cliffs across 33 symbols;
inventory below). Blocks: clean backtests, the dip-feed launch numbers,
and eventually live-ledger reconciliation.

## Root cause (three layers, all confirmed in code)

1. **Kite serves adjusted history; our store is append-only.**
   `scripts/history_utils.py` fetches with a 15-day overlap and
   `keep="last"` (fresh rows win). After a split/bonus, Kite re-bases
   the entire series; our refetch re-bases only the last ~15 days.
   Result: a cliff at the overlap boundary (not the ex-date), which can
   oscillate across runs as the window slides — ECLERX's four
   alternating ±50/±95% cliffs in Feb-Mar 2026 are this signature.
2. **The manual repair layer has no feed.** `apply_corporate_actions.py`
   applies only events hand-entered in `data/corporate_actions.json` —
   which contains exactly one entry ever (VEDL demerger 2026-04-30).
   Every bonus/split nobody hand-entered slipped through: ANGELONE
   (-90%, likely 1:10 split, 2026-01), LICI, IRB, TRENT/ANANDRATHI/
   ZFCVINDIA (all 2026-05-29), etc.
3. **The merged panel inherits and fossilizes the damage.**
   `sync_insights_panels.py` appends live → merged with an explicit
   "assumes no new splits since the last merge" comment. Pre-2020
   cliffs (ZYDUSLIFE 2010, MOTHERSON 2013, ADANIENT 2015 demerger, …)
   came in with the original deep-history backfill.

## Fix design

**Detection (daily guard):** `reconcile_price_integrity.py` scans the
last N sessions of every live CSV for adjacent-close ratios outside
±28%, classifies against known CA ratios (bonus 1:1 → 0.5, 1:2 → 0.667,
splits 1/2 1/5 1/10, and inverses for flip-flops). Report-only by
default; `--heal` deletes flagged live CSVs — safe either way, because a
full refetch reproduces a REAL crash identically and cures a CA cliff
(Kite's full history is adjusted). Healed symbols are queued for merged
re-base. Wiring into `run_daily_pipeline.py` (between fetch and
apply_corporate_actions) is a founder call — it deletes files on the
Railway volume, so it ships only after sign-off.

**Repair (one-time backfill), two paths:**
- *Path A (preferred):* full-depth Kite refetch per affected symbol via
  `refetch_history.py --from 2009-01-01`, then rebuild the merged file
  from the refetched series outright. Depends on Kite serving deep
  history (probe with `--probe-depth RELIANCE` when a token is live —
  default_configs starts at 2020-01-01 by choice, not by API limit).
- *Path B (fallback, offline):* `repair_merged.py` — replace merged's
  live-era rows with the (clean) live file, re-base all pre-seam rows by
  the median overlap ratio (prices ×r, volume ×1/r), then snap remaining
  pre-seam cliffs to the nearest known CA ratio. Demergers can't be
  snapped (arbitrary ratios) — those need Path A or a manual factor in
  corporate_actions.json.

**Ordering note:** the live dir must be healed before merged repair
(merged repair trusts live as the truth for 2020+).

## Runbook

1. `scan_cliffs.py` → `inventory.csv` (offline, done — see RESULTS).
2. Founder sign-off on guard wiring + heal of flagged live CSVs.
3. Next trading morning (token live): probe Kite depth; run Path A for
   the affected list (locally AND on the Railway volume — the pipeline
   runs there; local dirs are synced but distinct).
4. Re-run `scan_cliffs.py` → expect zero CA-signature cliffs; keep real
   crashes (YESBANK 2020-03-06 etc.) — they are data, not bugs.
5. Re-run the dip-feed headline numbers without the exclusion list
   (tasks/dip_vs_breakout_calls) — the numbers quoted anywhere must
   come from the healed panel.
6. Promote the guard into `scripts/` + pipeline wiring; add the
   freshness-panel flag.

## Files

- `ca_lib.py` — pure detection/classification functions (tested).
- `test_ca_lib.py` — pytest for the pure functions.
- `scan_cliffs.py` — offline inventory of both price dirs.
- `reconcile_price_integrity.py` — daily guard (report / --heal).
- `repair_merged.py` — Path B offline repair (dry-run / --apply).
- `refetch_history.py` — Path A deep refetch (needs Kite token).
- `inventory.csv` — current damage inventory.
