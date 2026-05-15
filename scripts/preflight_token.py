"""Fail-fast Kite access-token preflight for the daily pipeline.

The token issued by login_and_save_token.py expires daily at 06:00 IST.
Running the full pipeline with an expired token used to fail deep inside
fetch_nse500_history.py with a cryptic kiteconnect error after several
seconds (or worse, partially through the fetch loop). This preflight
catches that condition in <1 second, before any other step runs.

Run standalone:
  python scripts/preflight_token.py

Exit codes:
  0  - token valid (profile() succeeded)
  1  - missing token file or .env credentials
  2  - token rejected by Kite API (likely expired)
  3  - network / other transient error
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    # Import lazily so this script is fast to start.
    try:
        from kiteconnect import KiteConnect
        from kiteconnect.exceptions import TokenException
    except ImportError as exc:
        print(f"[preflight] kiteconnect not installed: {exc}", file=sys.stderr)
        return 1

    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from history_utils import load_credentials
    except Exception as exc:
        print(f"[preflight] could not import load_credentials: {exc}", file=sys.stderr)
        return 1

    try:
        api_key, access_token = load_credentials()
    except RuntimeError as exc:
        print(f"[preflight] {exc}", file=sys.stderr)
        print("[preflight] Run scripts/login_and_save_token.py "
              "(or re-invoke the pipeline with --with-login).", file=sys.stderr)
        return 1

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    try:
        profile = kite.profile()
    except TokenException as exc:
        print(f"[preflight] Token rejected by Kite API: {exc}", file=sys.stderr)
        print("[preflight] Token has likely expired (daily 06:00 IST).",
              file=sys.stderr)
        print("[preflight] Re-invoke the pipeline with --with-login.",
              file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[preflight] Unexpected error calling kite.profile(): {exc}",
              file=sys.stderr)
        return 3

    user = profile.get("user_name") or profile.get("user_id") or "unknown"
    print(f"[preflight] Token OK (user: {user})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
