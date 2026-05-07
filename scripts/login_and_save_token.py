import http.server, socketserver, webbrowser, urllib.parse, threading, time, socket, argparse
from kiteconnect import KiteConnect
from dotenv import load_dotenv
import os, json, sys

load_dotenv()

# Parse arguments first - headless mode skips browser entirely
parser = argparse.ArgumentParser(description="Login to Zerodha and save access token")
parser.add_argument("--headless", action="store_true",
                    help="Use automated login (requires KITE_USER_ID, KITE_PASSWORD, TOTP_SECRET)")
_args = parser.parse_args()

if _args.headless:
    # Delegate to headless login script
    from importlib.util import spec_from_file_location, module_from_spec
    script_dir = os.path.dirname(os.path.abspath(__file__))
    spec = spec_from_file_location("headless_login", os.path.join(script_dir, "headless_login.py"))
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.headless_login()
    sys.exit(0)

API_KEY     = os.getenv("API_KEY") or os.getenv("KITE_API_KEY")
API_SECRET  = os.getenv("API_SECRET") or os.getenv("KITE_API_SECRET")
REDIRECT_URI= os.getenv("REDIRECT_URI")

if not (API_KEY and API_SECRET and REDIRECT_URI):
    print("Missing .env values. Set API_KEY, API_SECRET, REDIRECT_URI")
    sys.exit(1)

# Helper function to serialize datetime objects in JSON
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

kite = KiteConnect(api_key=API_KEY)
login_url = kite.login_url()  # official method from the Python SDK
print("\nOpen this URL to login:\n", login_url, "\n")

# auto-open in browser
try:
    webbrowser.open(login_url)
except Exception:
    pass

# simple HTTP handler to capture request_token from redirect
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to print request logs
        print(f"[HTTP] {args[0]}")

    def do_GET(self):
        print(f"[DEBUG] Received request: {self.path}")
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        # Accept any path that has request_token (more robust than exact path matching)
        # This handles both /callback and /api/system/callback
        request_token = qs.get("request_token", [None])[0]
        if request_token:

            # Exchange request_token -> access_token
            try:
                data = kite.generate_session(request_token, api_secret=API_SECRET)
                access_token = data["access_token"]
                # Persist with restricted file permissions (owner read/write only)
                token_path = "access_token.txt"
                with open(token_path, "w") as f:
                    f.write(access_token)
                os.chmod(token_path, 0o600)
                # Optional: keep full session json if you want
                session_path = "session.json"
                with open(session_path, "w") as f:
                    json.dump(data, f, indent=2, default=json_serial)
                os.chmod(session_path, 0o600)

                msg = f"Success! access_token saved to access_token.txt"
                print(msg)
                self.send_response(200); self.end_headers()
                self.wfile.write(msg.encode())
                shutdown_event.set()
            except Exception as e:
                print("Token exchange failed:", e)
                self.send_response(500); self.end_headers()
                self.wfile.write(b"Token exchange failed. Check console.")

        else:
            self.send_response(404); self.end_headers()

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

shutdown_event = threading.Event()
httpd = None


def serve():
    url = urllib.parse.urlparse(REDIRECT_URI)
    port = url.port or 8000
    # Bind to 127.0.0.1 explicitly (not "localhost") to avoid DNS resolution issues
    host = "127.0.0.1"
    global httpd
    try:
        with ReusableTCPServer((host, port), Handler) as srv:
            httpd = srv
            print(f"Listening on {host}:{port} for redirect ...")
            print(f"Will accept any request with request_token parameter")
            srv.serve_forever()
    except OSError as e:
        print(f"ERROR: Could not start server on {host}:{port} - {e}")
        print("Check if another process is using this port: lsof -i :8000")
        shutdown_event.set()


t = threading.Thread(target=serve, daemon=True)
t.start()

# Give the server a moment to start
time.sleep(0.5)

# Verify server is actually listening
def check_server():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', urllib.parse.urlparse(REDIRECT_URI).port or 8000))
        sock.close()
        return result == 0
    except:
        return False

if check_server():
    print("Server verified: accepting connections on 127.0.0.1:8000")
else:
    print("WARNING: Server may not be accepting connections. Check for port conflicts.")

# Keep process alive for a few minutes while you log in, but exit once token is saved
if not shutdown_event.wait(timeout=600):
    print("Timed out waiting for login.")
else:
    print("Login complete, shutting down server.")
    if httpd:
        httpd.shutdown()
