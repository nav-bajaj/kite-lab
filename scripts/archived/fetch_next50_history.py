import datetime as dt

from history_utils import (
    default_configs,
    download_batches,
    init_kite_client,
    load_symbols,
)


def main():
    kite = init_kite_client()
    symbols = load_symbols("ind_niftynext50list.csv")
    if not symbols:
        print("No symbols found in ind_niftynext50list.csv")
        return
    today = dt.date.today()

    configs = default_configs(
        today=today,
        daily_dir="next50_data",
        hourly_dir="next50_data_hourly",
    )
    failures = download_batches(kite, symbols, configs)
    if failures:
        print("\nSummary of failures:")
        for interval, symbols_with_error in failures.items():
            print(f"{interval}: {', '.join(symbols_with_error)}")


if __name__ == "__main__":
    main()
