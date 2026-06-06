# data/published/

The stable, one-way export from kite-lab to downstream content
consumers. Currently the only consumer is `~/finance-content-os` (the
editorial engine), but this directory is consumer-agnostic — anything
that wants to know "what marketworks said on what date" reads from
here.

## Contract

Every file in `signals/` is a JSON document conforming to
`schema/signal.schema.json`. Filenames are
`{YYYY-MM-DD}_{source-slug}.json` so they sort lexicographically by
date.

`MANIFEST.json` lists every signal in the directory, sorted descending
by `published_at`. Consumers should prefer the manifest over directory
scans.

## Sources currently published

| Source slug | Producer | Cadence |
|---|---|---|
| `postclose_note` | Insight engine's `note_assembler.assemble("postclose", reading)` | One per trading day |
| `premarket_note` | Insight engine's `note_assembler.assemble("premarket", reading)` | One per trading day |
| `weekly_note` | Insight engine's `note_assembler.assemble("weekly", reading)` | One per week (Sunday) |
| `{portfolio_id}_rebalance` | Portfolio runners (TL25, OM25, L6, COMBO) | On rebalance events |

## How to publish

```
python scripts/publish_signal.py from-daily-note --date 2026-05-31 --mode postclose
python scripts/publish_signal.py from-rebalance --portfolio tl25_v3 --changes-csv path/to/changes_2026-05-30.csv
```

Both subcommands write to `signals/` and update `MANIFEST.json`. Output
is validated against the local schema copy before write.

## Why files are committed to git

Published signals are the audit trail of what we claimed publicly on
what date. They are small, versioned, and useful in their own right —
not just a build artifact. Do not `.gitignore` this directory.

## Schema source of truth

`schema/signal.schema.json` is a copy from
`~/finance-content-os/schemas/signal.schema.json`. On schema change,
update the content repo first, then copy here. The publisher
hash-checks both files at startup and refuses to run if they diverge.
