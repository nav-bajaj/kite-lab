"""
Lightweight control plane for running existing CLI workflows via HTTP.
Usage:
    python ui/server.py --host 0.0.0.0 --port 8001

Endpoints:
    GET  /                 -> dashboard HTML
    GET  /api/commands     -> list available command shortcuts
    POST /api/jobs         -> start a job: {"command": "fetch_nse500", "args": ["--dry-run"]}
    GET  /api/jobs         -> list jobs and statuses
    GET  /api/jobs/<id>    -> job detail
    GET  /api/logs/<id>    -> fetch log contents
"""

import argparse
import json
import os
import threading
import uuid
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "ui" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


COMMANDS = {
    "login": {
        "label": "Login to Kite",
        "cmd": [sys.executable, "scripts/login_and_save_token.py"],
        "description": "Launch browser login and save access_token.txt",
        "args": [],
    },
    "cache_instruments": {
        "label": "Cache Instruments",
        "cmd": [sys.executable, "scripts/cache_instruments.py"],
        "description": "Fetch instruments and write data/instruments_full.csv",
        "args": [],
    },
    "fetch_nse500": {
        "label": "Fetch NSE 500",
        "cmd": [sys.executable, "scripts/fetch_nse500_history.py"],
        "description": "Download daily + hourly history for NSE 500",
        "args": [],
    },
    "compute_benchmark": {
        "label": "Compute Benchmark",
        "cmd": [sys.executable, "scripts/compute_benchmark.py"],
        "description": "Update data/benchmarks/nifty100.csv",
        "args": [],
    },
    "build_signals": {
        "label": "Build Signals (L6 default)",
        "cmd": [sys.executable, "scripts/build_momentum_signals.py"],
        "description": "Generate momentum rankings",
        "args": [
            {"flag": "--prices-dir", "placeholder": "nse500_data", "help": "Directory of *_day.csv price files"},
            {"flag": "--output", "placeholder": "data/momentum/top25_signals.csv", "help": "Where to write rankings CSV"},
            {"flag": "--skip-days", "placeholder": "21", "help": "Skip window before measuring momentum"},
            {"flag": "--lookbacks", "placeholder": "6", "help": "Momentum lookbacks (months), space-separated"},
            {"flag": "--top-n", "placeholder": "25", "help": "Number of names to keep per rebalance"},
            {"flag": "--vol-floor", "placeholder": "0.0005", "help": "Lower bound for realized vol"},
            {"flag": "--universe-file", "placeholder": "", "help": "Optional CSV with Symbol column to filter universe"},
        ],
    },
    "backtest": {
        "label": "Run Backtest",
        "cmd": [sys.executable, "scripts/backtest_momentum.py"],
        "description": "Simulate weekly portfolio",
        "args": [
            {"flag": "--prices-dir", "placeholder": "nse500_data", "help": "Directory with price CSVs"},
            {"flag": "--signals", "placeholder": "data/momentum/top25_signals.csv", "help": "Signals CSV to trade"},
            {"flag": "--benchmark", "placeholder": "data/benchmarks/nifty100.csv", "help": "Benchmark series CSV"},
            {"flag": "--output-dir", "placeholder": "data/backtests", "help": "Folder for equity/trade/metrics outputs"},
            {"flag": "--top-n", "placeholder": "25", "help": "Portfolio size"},
            {"flag": "--exit-buffer", "placeholder": "0", "help": "Hysteresis band (exit when rank > top_n + buffer)"},
            {"flag": "--pnl-hold-threshold", "placeholder": "", "help": "Defer exit while unrealized PnL above threshold"},
            {"flag": "--scenario", "placeholder": "baseline|cooldown|vol_trigger", "help": "Exposure scheme"},
        ],
    },
    "daily_pipeline": {
        "label": "Run Daily Pipeline",
        "cmd": [sys.executable, "scripts/run_daily_pipeline.py"],
        "description": "Run fetch + benchmark + signals (optionally login)",
        "args": [
            {"flag": "--with-login", "placeholder": "", "help": "Include login step before pipeline (flag only)"},
            {"flag": "--dry-run", "placeholder": "", "help": "Print commands without executing (flag only)"},
        ],
    },
    "report_backtests": {
        "label": "Build Backtest Report",
        "cmd": [sys.executable, "scripts/report_backtests.py"],
        "description": "Generate HTML comparison report",
        "args": [
            {"flag": "--runs", "placeholder": "data/backtests/run1 data/backtests/run2", "help": "Space-separated run folders"},
            {"flag": "--output", "placeholder": "data/backtests/report.html", "help": "Output HTML path"},
        ],
    },
    "l6_grid": {
        "label": "L6 Grid Search",
        "cmd": [sys.executable, "scripts/run_l6_grid.py"],
        "description": "Deterministic grid over skip/vol-floor/topN/exit-buffer",
        "args": [
            {"flag": "--skip-days", "placeholder": "21 10 0", "help": "Skip windows to test (space-separated)"},
            {"flag": "--vol-floor", "placeholder": "0.0005 0.001", "help": "Vol floors to test (space-separated)"},
            {"flag": "--top-n", "placeholder": "25 20", "help": "Top-N values to test (space-separated)"},
            {"flag": "--exit-buffer", "placeholder": "0 5", "help": "Exit buffer values to test"},
            {"flag": "--scenarios", "placeholder": "baseline cooldown", "help": "Scenarios to run (space-separated)"},
            {"flag": "--limit", "placeholder": "", "help": "Optional cap on number of runs"},
        ],
    },
    "l6_monte_carlo": {
        "label": "L6 Monte Carlo",
        "cmd": [sys.executable, "scripts/run_l6_monte_carlo.py"],
        "description": "Randomized baseline/hysteresis/PnL-hold sweeps",
        "args": [
            {"flag": "--runs", "placeholder": "20", "help": "Number of MC runs"},
            {"flag": "--sample-size", "placeholder": "250", "help": "Universe sample size"},
            {"flag": "--topn-min", "placeholder": "20", "help": "Min top-N"},
            {"flag": "--topn-max", "placeholder": "30", "help": "Max top-N"},
            {"flag": "--skip-days", "placeholder": "0 10 21", "help": "Skip windows (space-separated)"},
            {"flag": "--exit-buffers", "placeholder": "0 5 10", "help": "Exit buffer options"},
            {"flag": "--pnl-hold", "placeholder": "0.05 0.1", "help": "PnL-hold thresholds"},
            {"flag": "--vol-floor", "placeholder": "0.0005 0.001", "help": "Vol floors"},
            {"flag": "--output-root", "placeholder": "experiments", "help": "Root folder for experiments"},
        ],
    },
}


class Job:
    def __init__(self, command_key, args):
        self.id = uuid.uuid4().hex[:8]
        self.command_key = command_key
        self.args = args or []
        self.status = "queued"
        self.started_at = None
        self.ended_at = None
        self.log_path = LOG_DIR / f"{self.id}.log"
        self.thread = threading.Thread(target=self._run, daemon=True)

    def to_dict(self):
        return {
            "id": self.id,
            "command": self.command_key,
            "label": COMMANDS.get(self.command_key, {}).get("label", self.command_key),
            "status": self.status,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "log_path": str(self.log_path),
            "args": self.args,
        }

    def start(self):
        self.thread.start()

    def _run(self):
        self.status = "running"
        self.started_at = datetime.utcnow().isoformat()
        cmd = list(COMMANDS[self.command_key]["cmd"]) + self.args
        with self.log_path.open("w") as logf:
            logf.write(f"Command: {' '.join(cmd)}\n")
            logf.write(f"Started at: {self.started_at} UTC\n\n")
            logf.flush()
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                for line in proc.stdout:
                    logf.write(line)
                    logf.flush()
                proc.wait()
                self.status = "completed" if proc.returncode == 0 else f"failed ({proc.returncode})"
            except Exception as exc:
                self.status = f"error ({exc})"
                logf.write(f"\nException: {exc}\n")
            finally:
                self.ended_at = datetime.utcnow().isoformat()
                logf.write(f"\nEnded at: {self.ended_at} UTC\n")
                logf.write(f"Status: {self.status}\n")
                logf.flush()


JOBS = {}


def json_response(handler, payload, status=HTTPStatus.OK):
    data = json.dumps(payload).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def read_body(handler):
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw)
    except Exception:
        return {}


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Serve dashboard.html for root, otherwise default to ui folder.
        parsed = urllib.parse.urlparse(path)
        if parsed.path == "/":
            return str(ROOT / "ui" / "dashboard.html")
        return super().translate_path(path)

    def log_message(self, format, *args):
        # Reduce console spam; could extend to file logging if needed.
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/api/commands":
            commands = []
            for key, meta in COMMANDS.items():
                commands.append({
                    "key": key,
                    "label": meta["label"],
                    "description": meta["description"],
                    "cmd": " ".join(str(c) for c in meta["cmd"]),
                    "args": meta.get("args", []),
                })
            return json_response(self, {"commands": commands})

        if path == "/api/jobs":
            return json_response(self, {"jobs": [job.to_dict() for job in JOBS.values()]})

        if path.startswith("/api/jobs/"):
            job_id = path.split("/")[-1]
            job = JOBS.get(job_id)
            if not job:
                return json_response(self, {"error": "not found"}, status=HTTPStatus.NOT_FOUND)
            return json_response(self, job.to_dict())

        if path.startswith("/api/logs/"):
            job_id = path.split("/")[-1]
            job = JOBS.get(job_id)
            if not job or not job.log_path.exists():
                return json_response(self, {"error": "not found"}, status=HTTPStatus.NOT_FOUND)
            content = job.log_path.read_text()
            payload = {"id": job_id, "content": content}
            return json_response(self, payload)

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/jobs":
            payload = read_body(self)
            command_key = payload.get("command")
            args = payload.get("args") or []
            if command_key not in COMMANDS:
                return json_response(self, {"error": "unknown command"}, status=HTTPStatus.BAD_REQUEST)
            job = Job(command_key, args)
            JOBS[job.id] = job
            job.start()
            return json_response(self, {"job": job.to_dict()}, status=HTTPStatus.ACCEPTED)

        return json_response(self, {"error": "unsupported"}, status=HTTPStatus.NOT_FOUND)


def main():
    parser = argparse.ArgumentParser(description="UI control-plane server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()

    os.chdir(ROOT)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Serving dashboard on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
