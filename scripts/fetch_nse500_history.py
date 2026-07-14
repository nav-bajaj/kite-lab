import datetime as dt

from history_utils import (
    default_configs,
    download_batches,
    init_kite_client,
    load_symbols,
)


UNIVERSE_CSV = "data/static/nse500_universe.csv"
MEMBERSHIP_CSV = "data/static/nse500_membership.csv"


def fetch_symbols():
    """ALL-EVER members when the membership file exists, else the snapshot.

    Removed-but-grandfathered holdings need daily prices until the engine
    sells them, and the recomputed history needs ex-members priced forever —
    so the fetch set must never shrink to current members only.
    """
    from pathlib import Path
    if Path(MEMBERSHIP_CSV).exists():
        # sibling import: this script runs as scripts/fetch_nse500_history.py
        # with scripts/ as sys.path[0] (same style as history_utils above)
        from universe_membership import load_membership, all_ever_members
        syms = sorted(all_ever_members(load_membership(Path(MEMBERSHIP_CSV))))
        print(f"Fetching {len(syms)} all-ever members from {MEMBERSHIP_CSV}")
        return syms
    return load_symbols(UNIVERSE_CSV)


def main():
    kite = init_kite_client()
    symbols = fetch_symbols()
    if not symbols:
        print(f"No symbols found in {UNIVERSE_CSV}")
        return

    today = dt.date.today()
    configs = default_configs(
        today=today,
        daily_dir="nse500_data",
        hourly_dir="nse500_data_hourly",
    )

    failures = download_batches(kite, symbols, configs)
    if failures:
        print("\nSummary of failures:")
        for interval, symbols_with_error in failures.items():
            print(f"{interval}: {', '.join(symbols_with_error)}")


if __name__ == "__main__":
    main()
