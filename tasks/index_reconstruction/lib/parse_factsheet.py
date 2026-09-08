"""Read constituent symbols out of an NSE index factsheet PDF.

The March 2022 factsheets in indices_dataMar2022/ are an INDEPENDENT
checkpoint: they were published by NSE at a date in the middle of the
reconstruction, so matching them is a real test of the replay rather than a
restatement of the same source. They also list symbols directly, so no name
resolution is needed.

Layout is a table whose first column is the symbol; the security name column
wraps, which produces continuation lines that carry no symbol.
"""
from __future__ import annotations

import re
import shutil
import subprocess

SYM = re.compile(r"^\s?([A-Z0-9][A-Z0-9&.\-]{1,17})\s{2,}\S")
SKIP = {"Symbol", "SYMBOL"}


def _pdftotext() -> str:
    """Absolute path to poppler's pdftotext, resolved once.

    Resolving the binary rather than relying on a PATH lookup at call time
    keeps which executable runs deterministic.
    """
    exe = shutil.which("pdftotext")
    if exe is None:
        raise RuntimeError("pdftotext not found - install poppler")
    return exe


def symbols(pdf_path: str) -> list[str]:
    txt = subprocess.run([_pdftotext(), "-layout", pdf_path, "-"],
                         capture_output=True, text=True, check=True).stdout
    out, seen = [], set()
    for ln in txt.splitlines():
        m = SYM.match(ln)
        if not m:
            continue
        s = m.group(1)
        if s in SKIP or s in seen:
            continue
        # a trailing '.' only ever appears in wrapped prose, not in symbols
        if s.endswith("."):
            continue
        seen.add(s)
        out.append(s)
    return out
