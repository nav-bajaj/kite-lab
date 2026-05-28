"""Generate a Daily Quant Note bundle (text + image) for manual broadcast.

This is the Phase 1 admin workflow. An operator runs this script after
market close (or pre-market, or on Sunday for the weekly digest), gets
back a PNG + text file, reviews them, then copy-pastes into WhatsApp Web
to broadcast.

Usage:
    python scripts/generate_quant_note.py postclose
    python scripts/generate_quant_note.py premarket --no-preview
    python scripts/generate_quant_note.py weekly --date 2026-05-08
    python scripts/generate_quant_note.py postclose --out /tmp/note

By default writes to `tasks/insight_engine/runs/daily/` and opens the
PNG in the system default viewer for review.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Make `import app.*` work when run directly from repo root
REPO_ROOT = Path(__file__).resolve().parents[1]
KITE_API = REPO_ROOT / "kite-api"
if str(KITE_API) not in sys.path:
    sys.path.insert(0, str(KITE_API))

import pandas as pd  # noqa: E402

from app.insights.notes.note_assembler import VALID_MODES, assemble  # noqa: E402
from app.insights.reading import get_market_reading  # noqa: E402


DEFAULT_OUT = REPO_ROOT / "tasks" / "insight_engine" / "runs" / "daily"


def _open_preview(path: Path) -> None:
    """Open the image in the system default viewer (cross-platform best effort).

    Admin-only CLI; operator opens their own output file. Partial executable
    paths and shell=True (on Windows only) are deliberate for cross-platform
    support — not security-sensitive.
    """
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)  # noqa: S603, S607
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", str(path)], check=False)  # noqa: S603, S607
        elif sys.platform == "win32":
            subprocess.run(["start", str(path)], shell=True, check=False)  # noqa: S602, S607
    except Exception as exc:
        print(f"  (could not open preview: {exc})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=VALID_MODES,
                        help="Which template to render")
    parser.add_argument("--date", default=None,
                        help="As-of date (YYYY-MM-DD). Default: most recent data.")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help=f"Output directory (default: {DEFAULT_OUT})")
    parser.add_argument("--no-preview", action="store_true",
                        help="Skip opening the image preview")
    args = parser.parse_args()

    asof = pd.Timestamp(args.date) if args.date else None

    print(f"[generate_quant_note] mode={args.mode}  as-of={asof or 'latest'}")
    print("[generate_quant_note] building MarketReading (~2-3s cold)...")
    reading = get_market_reading(asof)

    print(f"[generate_quant_note] composing {args.mode} bundle...")
    bundle = assemble(args.mode, reading)

    out_dir = Path(args.out)
    text_path, image_path = bundle.save_to(out_dir)
    print(f"\n  Saved:")
    print(f"    text:  {text_path}")
    print(f"    image: {image_path}  ({image_path.stat().st_size//1024} KB)")
    print(f"\n  Headline: {bundle.headline}")
    print(f"  Regime:   {bundle.regime}")
    print(f"  Stress:   {bundle.stress_score:.0f}/100")

    print(f"\n{'─'*70}")
    print(f"PREVIEW (text):")
    print(f"{'─'*70}\n")
    print(bundle.text)
    print(f"\n{'─'*70}\n")

    if not args.no_preview:
        _open_preview(image_path)
        print(f"  Preview opened. Review image + text, then broadcast via WhatsApp Web.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
