import argparse
import subprocess
import sys


STEPS = [
    ("Refresh NSE 500 data", [sys.executable, "scripts/fetch_nse500_history.py"]),
    ("Update Nifty 100 benchmark", [sys.executable, "scripts/compute_benchmark.py"]),
    ("Build momentum rankings", [sys.executable, "scripts/build_momentum_signals.py"]),
]


def run_command(name, command, dry_run=False):
    print(f"\n>>> {name}")
    print("Command:", " ".join(command))
    if dry_run:
        print("[dry-run] skipped")
        return True
    result = subprocess.run(command)
    if result.returncode != 0:
        print(f"Step '{name}' failed with code {result.returncode}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Run the daily momentum data pipeline")
    parser.add_argument("--with-login", action="store_true", help="Run login script before data updates")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    args = parser.parse_args()

    if args.with_login:
        login_cmd = [sys.executable, "scripts/login_and_save_token.py"]
        if not run_command("Login to Kite", login_cmd, dry_run=args.dry_run):
            sys.exit(1)

    for name, cmd in STEPS:
        if not run_command(name, cmd, dry_run=args.dry_run):
            sys.exit(1)

    print("\nDaily pipeline completed successfully")


if __name__ == "__main__":
    main()
