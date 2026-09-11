"""Master-store package (P1, 2026-09-11): the market_data_spine library moved under data_pipeline so the production image
carries it. Paths resolve from KITE_LAB_ROOT (default: the repo root this file sits in); the store is <root>/data/master."""
from __future__ import annotations
import os
from pathlib import Path

ROOT = os.environ.get("KITE_LAB_ROOT", str(Path(__file__).resolve().parents[2]))
MASTER = f"{ROOT}/data/master"
