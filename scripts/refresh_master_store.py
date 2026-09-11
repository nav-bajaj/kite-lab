#!/usr/bin/env python
"""Nightly master-store refresh (19:30 IST, after NSE publishes the bhavcopy, before the backup).

Order: bhavcopy of the day -> symbol master + bhavcopy parquet -> per-symbol raw series -> corporate actions
-> Kite append (last 20 days, merged) -> adjusted views -> Kite-vs-raw verification -> QA report -> stamp.
The QA outcome is written to data/master/qa/nightly_latest.json with status ok | flagged; a flag is for the
next morning's review (founder decision 2026-09-11) and does not block the evening. Every step is a module of
data_pipeline/master_store run as a subprocess so a failure is isolated and logged like the daily pipeline.

    python scripts/refresh_master_store.py [--dry-run] [--steps bhavcopy,ca,kite,adjust,qa] [--since-days 20]
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(os.environ.get("KITE_LAB_ROOT", Path(__file__).resolve().parents[1])); MASTER = Path(os.environ.get("MASTER_STORE_DIR", ROOT / "data/master")); QA = MASTER / "qa"
PY = sys.executable


def step(name, mod, args=(), dry=False, timings=None):
    cmd = [PY, "-m", f"data_pipeline.master_store.{mod}", *map(str, args)]
    print(f"\n=== {name}: {' '.join(cmd[2:])}", flush=True)
    if dry:
        return True
    t0 = time.time(); r = subprocess.run(cmd, cwd=ROOT, env={**os.environ, "KITE_LAB_ROOT": str(ROOT), "MASTER_STORE_DIR": str(MASTER)})
    if timings is not None: timings.append((name, time.time() - t0, r.returncode))
    print(f"    -> {'ok' if r.returncode == 0 else 'FAILED'} in {time.time()-t0:.0f}s", flush=True)
    return r.returncode == 0


def ensure_panel_views():
    """The engines read MASTER/panels/<view>/<SYMBOL>_day.csv; those are symlinks into prices/adjusted_<view>/. The view is
    derived, so it is not shipped in the store archive (the upload endpoint rejects link members) — recreate it here, on every
    run, for each adjusted view present on disk. Idempotent; relative links so the store can move."""
    n = 0
    for view in ("pr", "tr"):
        src = MASTER / f"prices/adjusted_{view}"; dst = MASTER / f"panels/{view}"
        if not src.is_dir():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for f in src.glob("*.csv"):
            link = dst / f"{f.stem}_day.csv"; target = os.path.relpath(f, dst)
            if link.is_symlink() and os.readlink(link) == target:
                continue
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to(target); n += 1
    print(f"    panel views: {n} links (re)created", flush=True)


def repull_candidates(days: int = 30) -> list:
    """Symbols whose Kite history must be re-pulled in full: an ex-date in the last `days` (Kite back-adjusts the whole series on
    the ex-date, so an appended tail would sit on a different basis from the stored history) or an unexplained Kite step in the
    last `days` (the verification found a band already). The store's own basis (bhavcopy x CA factors) is unaffected either way."""
    import pandas as pd
    cutoff = pd.Timestamp(date.today() - timedelta(days=days)); syms = set()
    ca = MASTER / "corporate_actions.csv"
    if ca.exists():
        c = pd.read_csv(ca, parse_dates=["ex_date"]); syms |= set(c.loc[c["ex_date"] >= cutoff, "symbol"].astype(str))
    un = QA / "kite_steps_unexplained.csv"
    if un.exists():
        u = pd.read_csv(un); dc = [x for x in u.columns if "date" in x.lower()]
        if dc and len(u): syms |= set(u.loc[pd.to_datetime(u[dc[0]], errors="coerce") >= cutoff, "symbol"].astype(str))
    return sorted(syms)


def qa_gate():
    """Summarise the QA outputs into one status. flagged = something a human should look at tomorrow."""
    import pandas as pd
    out = {"date": date.today().isoformat(), "checked_at": datetime.now().isoformat(timespec="seconds")}
    try:
        bp = pd.read_csv(QA / "bad_prints.csv"); st = pd.read_csv(QA / "stale_tails.csv"); cal = pd.read_csv(QA / "calendar.csv")
        recent = bp[pd.to_datetime(bp["date"]) >= pd.Timestamp(date.today() - timedelta(days=30))]
        out.update(bad_prints_30d=int(len(recent)), bad_prints_30d_kite_disagrees=int((recent["kite_agrees"] == False).sum()),
                   stale_tails=int(len(st)), calendar_issues=int(len(cal)))
        unexpl = QA / "kite_steps_unexplained.csv"
        if unexpl.exists():
            u = pd.read_csv(unexpl); dc = [c for c in u.columns if "date" in c.lower()]
            out["kite_steps_unexplained_30d"] = int((pd.to_datetime(u[dc[0]], errors="coerce") >= pd.Timestamp(date.today() - timedelta(days=30))).sum()) if len(u) and dc else 0
        out["status"] = "flagged" if (out["bad_prints_30d_kite_disagrees"] or out["calendar_issues"] or out.get("kite_steps_unexplained_30d", 0)) else "ok"
    except Exception as e:  # noqa: BLE001
        out.update(status="flagged", error=str(e)[:200])
    QA.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(QA / "nightly_latest.json", "w"), indent=1); json.dump(out, open(QA / f"nightly_{out['date']}.json", "w"), indent=1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--steps", default="bhavcopy,ca,kite,adjust,qa")
    ap.add_argument("--since-days", type=int, default=20, help="Kite append window and bhavcopy look-back (sessions already on disk are skipped)")
    a = ap.parse_args(); steps = set(a.steps.split(",")); timings = []; ok = True
    if not a.dry_run:
        ensure_panel_views()   # a freshly seeded store has no panels/ yet
    since = (date.today() - timedelta(days=a.since_days)).isoformat()
    if "bhavcopy" in steps:
        ok &= step("Bhavcopy: fetch missing sessions", "fetch_bhavcopy", ["--start", since], a.dry_run, timings)
        ok &= step("Bhavcopy: symbol master + parquet", "build_symbol_master", [], a.dry_run, timings)
        ok &= step("Bhavcopy: per-symbol raw series", "export_bhavcopy_series", [], a.dry_run, timings)
    if "ca" in steps:
        ok &= step("Corporate actions: NSE filings (this year)", "fetch_nse_ca", ["--start-year", str(date.today().year)], a.dry_run, timings)
        ok &= step("Corporate actions: table", "build_corporate_actions", [], a.dry_run, timings)
        ok &= step("Corporate actions: observed events", "derive_observed_events", [], a.dry_run, timings)
    if "kite" in steps:
        ok &= step("Kite: append last sessions", "fetch_kite", ["--since-days", str(a.since_days)], a.dry_run, timings)
        rp = repull_candidates(30)
        if rp:
            lst = MASTER / "qa/kite_repull_today.txt"; lst.parent.mkdir(parents=True, exist_ok=True); lst.write_text("\n".join(rp) + "\n")
            ok &= step(f"Kite: full re-pull, {len(rp)} symbols with a recent ex-date or unexplained step", "fetch_kite", ["--symbols-file", str(lst)], a.dry_run, timings)
        if not a.dry_run:
            mf = MASTER / "prices/kite_manifest.json"
            if mf.exists():
                mn = json.load(open(mf)); today = date.today().isoformat()
                n_err = sum(1 for v in mn.values() if v.get("last_error_at") == today); share = n_err / max(len(mn), 1)
                print(f"    Kite: {n_err} of {len(mn)} symbols errored today ({100*share:.0f}%)" + ("  -> STEP FAILED (token or API problem)" if share > 0.05 else ""), flush=True)
                if share > 0.05:
                    ok = False; timings[-1] = (timings[-1][0], timings[-1][1], 1)
    if "adjust" in steps:
        ok &= step("Adjusted views (price return, total return)", "build_adjusted", [], a.dry_run, timings)
        if not a.dry_run:
            ensure_panel_views()
    if "qa" in steps:
        ok &= step("QA: Kite vs raw adjustment", "verify_kite_adjustment", [], a.dry_run, timings)
        ok &= step("QA: report", "qa_report", [], a.dry_run, timings)
        if not a.dry_run:
            g = qa_gate(); print(f"\nQA gate: {g['status']}  {json.dumps({k: v for k, v in g.items() if k not in ('date', 'checked_at')})}")
    if timings:
        print("\n" + "\n".join(f"{n:48s} {t:7.0f}s  {'ok' if rc == 0 else 'FAILED'}" for n, t, rc in timings))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
