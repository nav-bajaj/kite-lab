"""Local health endpoint for the options worker.

Plain http.server in a daemon thread — the worker must not depend on the
web app's FastAPI stack. Bound for Railway's internal healthcheck and local
curl only; this service never exposes public APIs (handover doc section 4).
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def start_health_server(worker, port: int, host: str = "127.0.0.1") -> HTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (http.server API)
            if self.path not in ("/health", "/"):
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps(worker.health_snapshot()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # healthchecks would spam the log
            pass

    server = HTTPServer((host, port), Handler)
    thread = threading.Thread(target=server.serve_forever, name="health", daemon=True)
    thread.start()
    return server
