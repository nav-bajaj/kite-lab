# Tasks

Ordered per `PLAN.md`. 👤 marks a founder decision.

## Prerequisites — owned by `tasks/adjusted_price_series/` 🔗

Not duplicated here. That task covers freezing the pre-flip panel, the
price-data contract, sealing the three leaks (15-day refetch, the CSV-delete
recovery path, and a volume reset silently re-fetching six years as
total-return), narrowing `apply_corporate_actions.py` so it does not
double-adjust, and the enforcement that makes it stick.

- [ ] 🔗 Blocked on its Phase 2 (seal the leaks) before phase 3 below is
      meaningful — a master file built on a leaking panel inherits the leak
- [ ] Contribute this branch's evidence to it: five observed restatements, and
      fresh-vs-stored Kite comparisons showing 510-591 of 668 days already
      differ, which suggests the flip is not purely prospective

## Phase 1 — master historical data file 🤖

- [ ] One file, all-ever members across the four indices, raw prices, source
      tagged
- [ ] Stitch rule for the 41 GDF-sourced series, per D-1
- [ ] Coverage report by index and date; the 16 symbols no feed carries stay
      listed as known gaps
- [ ] Becomes the single input to backtests; nothing reads the loose
      directories afterwards

## Phase 2 — portfolios on the dated universe 🤖

- [ ] Re-run OM25 v3, TL25 v3, L6 v2, COMBO over the reconstructed membership
      and master price file
- [ ] Attribute every difference against today's published numbers to a cause:
      universe, price source, or corporate action. An unattributed difference
      is a bug, not a result
- [ ] 👤 Decide whether to restate the published track record or run forward
      from the lock dates (D-3 open item)

## Phase 3 — the immutable ledger 🤖

- [ ] Append-only ledger from each strategy's lock date (D-4): L6 and COMBO
      2026-05-14, OM25 and TL25 2026-06-06. Start dates already established —
      no re-derivation, no downloads
- [ ] Per rebalance: holdings, weights, prices used, input hash
- [ ] 👤 OM25 and TL25 have no stored run between their 2026-06-06 lock and
      2026-07-10. Decide whether those five weeks are reconstructed and marked
      as such, or the ledger simply begins at the first contemporaneous run
- [ ] Published performance derives from the ledger, never from a re-run (D-5)
- [ ] Wire `lib/audit_immutability.py --strict` into the daily pipeline so a
      restatement fails loudly instead of being found months later

## Phase 4 — standing membership procedure 🤖👤

- [ ] Membership refresh: NSE publishes replacements weeks ahead of the
      effective date. Poll the press-release archive, parse, stage the diff for
      review, apply on the effective date
- [ ] Watch for the failure modes that already bit: renames logged under the
      exit name, revocations, scanned PDFs with no text layer, Nifty 100
      changes announced only as Nifty Next 50
- [ ] Runbook in `docs/` and a scheduled check that the universe files agree
      with NSE's current published constituents
- [ ] Corporate-action intake stays with `adjusted_price_series`; this covers
      membership only

## Done

- [x] Ledger start dates established empirically (`lib/audit_immutability.py`)
- [x] Data-source decision (D-1) and adjustment model (D-2, D-3) recorded
- [x] Full branch findings written up (`CONTEXT.md`)
