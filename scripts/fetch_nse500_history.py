import datetime as dt

from history_utils import (
    default_configs,
    download_batches,
    init_kite_client,
    load_symbols,
)


UNIVERSE_CSV = "data/static/nse500_universe.csv"


def main():
    kite = init_kite_client()
    symbols = load_symbols(UNIVERSE_CSV)
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
