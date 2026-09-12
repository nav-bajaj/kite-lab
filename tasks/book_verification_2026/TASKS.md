# Tasks — book verification 2026

Owners: 🤖 agents write and run; 👤 founder reads RESULTS.md and rules on anything that turns
out to be a rule question rather than a bug.

## V1 — book behaviour test list and suite 🤖 [prod]
- [ ] `TESTS_BOOKS.md`: numbered behavioural tests, one per rule in MECHANICS.md (selection,
      rebalance, exits, sizing and cash, sector cap, regime, look-ahead, outputs).
- [ ] `tests/test_books_*.py`: the list implemented; runs against a fresh local run of both
      books from 2010 plus synthetic-panel engine cases; every test names the rule it checks.
- [ ] First run recorded in RESULTS.md with every failure explained.

## V2 — dataset integrity test list and suite 🤖 [data]
- [ ] `TESTS_DATA.md`: integrity tests for `data/master` as the books read it, distinct from
      the 13 fortnightly checks (which are operational and Kite-facing).
- [ ] `tests/test_data_*.py`: implemented against the local store; a test that needs Kite or
      the network is marked and skipped by default.
- [ ] First run recorded in RESULTS.md.

## V3 — close-out 🤖👤
- [ ] Failures triaged: bug (fix on `index_reconstruction`, rerun suite) vs rule question
      (to the founder) vs data issue (to the store's repair list).
- [ ] The two suites wired into the repo's normal `pytest tests/` run (or documented as the
      pre-deploy gate in `tasks/production_port_2026/TASKS.md`).
- [ ] Only after both suites pass: deploy the pending rule change (stop_reentry_block=1 is
      already live; the Railway rerun and full DB re-sync of both books remain) and rerun.
