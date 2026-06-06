# src/marketing-content/

Build-time data source for `/library` and `/library/[slug]`. Synced
from `~/finance-content-os/published/` by that repo's
`scripts/publish.py`.

Do NOT hand-edit. The canonical source of truth for any file here is
`~/finance-content-os/published/`. To add or update a piece:

1. In finance-content-os, run the v2 pipeline through to `reviewed`
   status.
2. `python scripts/publish.py --slug <pack-slug>` — writes BOTH the
   canonical record AND syncs the deployable copy into this directory
   + `public/marketing-content/assets/<slug>/`.
3. Commit both repos.

Files synced into this directory:
- `manifest.json` — index for `/library`
- `pieces/<slug>.json` — one per published piece, consumed by
  `/library/[slug]`

Assets (PNGs / MP4s) live separately in `public/marketing-content/assets/`
so Next.js serves them at `/marketing-content/assets/<slug>/<file>`.

See `tasks/content_bridge/PLAN.md` in the kite-lab repo for the full
architecture and rationale.
