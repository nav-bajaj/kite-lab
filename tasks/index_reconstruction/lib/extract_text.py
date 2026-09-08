"""Extract text from the downloaded press-release PDFs.

Fails loudly on an empty extraction. ind_prs23082021.pdf is a 29-page scan
with no text layer: pdftotext returned 29 bytes and the parser simply saw no
sections, which silently dropped an entire semi-annual review from three
indices. An empty dump is now reported rather than written and forgotten.
"""
from __future__ import annotations

import glob, os, shutil, subprocess, sys

# A real press release always yields at least a few hundred characters even
# when it is one short page; the scanned one yielded 29 bytes from a 2.5 MB
# file. Flag on absolute size AND on a hopeless text-to-PDF ratio, so a large
# scan is caught even if it happens to carry a header line of real text.
MIN_BYTES = 500
MIN_RATIO = 0.001


def _pdftotext() -> str:
    """Absolute path to poppler's pdftotext, resolved once.

    Resolving the binary rather than relying on a PATH lookup at call time
    keeps which executable runs deterministic.
    """
    exe = shutil.which("pdftotext")
    if exe is None:
        raise RuntimeError("pdftotext not found - install poppler")
    return exe


def main() -> int:
    os.makedirs("data/pr_text", exist_ok=True)
    empty = []
    for pdf in sorted(glob.glob("data/press_releases/*.pdf")):
        base = os.path.basename(pdf)[:-4]
        out = f"data/pr_text/{base}.txt"
        subprocess.run([_pdftotext(), "-layout", pdf, out], check=True)
        txt_size, pdf_size = os.path.getsize(out), os.path.getsize(pdf)
        if txt_size < MIN_BYTES or txt_size / max(pdf_size, 1) < MIN_RATIO:
            empty.append(f"{base} (text {txt_size}B from PDF {pdf_size}B)")
    print(f"extracted {len(glob.glob('data/pr_text/*.txt'))} files")
    if empty:
        print(f"\nNO TEXT LAYER ({len(empty)}) - these are scans and must be "
              f"read by eye; record what they contain in lib/scanned_releases.py:")
        for b in empty:
            print("   ", b)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
