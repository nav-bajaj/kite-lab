from pathlib import Path
import pandas as pd


def validate_prices(path: Path, frequency: str = "day", max_gap_days: int = 3):
    errors = []
    warnings = []
    if not path.exists():
        errors.append(f"{path} missing")
        return {"errors": errors, "warnings": warnings}

    df = pd.read_csv(path, parse_dates=["date"])
    if df.empty:
        warnings.append("empty file")
        return {"errors": errors, "warnings": warnings}

    if (df["close"] <= 0).any():
        errors.append("non-positive close values detected")

    df = df.sort_values("date")
    if frequency == "day":
        deltas = df["date"].diff().dt.days.dropna()
    else:
        deltas = df["date"].diff().dt.components["hours"].dropna()
    if (deltas > max_gap_days).any():
        warnings.append("gaps larger than expected")

    if df["close"].pct_change().abs().gt(1).any():
        warnings.append("large single-day moves >100% detected")

    return {"errors": errors, "warnings": warnings}
