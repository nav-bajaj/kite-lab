import http.server, socketserver, webbrowser, urllib.parse, threading, time
from kiteconnect import KiteConnect
from dotenv import load_dotenv
import os, json, sys

load_dotenv()
API_KEY     = os.getenv("API_KEY")
API_SECRET  = os.getenv("API_SECRET")
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
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == urllib.parse.urlparse(REDIRECT_URI).path:
            qs = urllib.parse.parse_qs(parsed.query)
            request_token = qs.get("request_token", [None])[0]
            if not request_token:
                self.send_response(400); self.end_headers()
                self.wfile.write(b"Missing request_token.")
                return

            # Exchange request_token -> access_token
            try:
                data = kite.generate_session(request_token, api_secret=API_SECRET)
                access_token = data["access_token"]
                # Persist
                with open("access_token.txt", "w") as f:
                    f.write(access_token)
                # Optional: keep full session json if you want
                with open("session.json", "w") as f:
                    json.dump(data, f, indent=2, default=json_serial)

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
    host = url.hostname or "localhost"
    port = url.port or 8000
    global httpd
    with ReusableTCPServer((host, port), Handler) as srv:
        httpd = srv
        print(f"Listening on {host}:{port} for redirect ...")
        srv.serve_forever()


t = threading.Thread(target=serve, daemon=True)
t.start()

# Keep process alive for a few minutes while you log in, but exit once token is saved
if not shutdown_event.wait(timeout=600):
    print("Timed out waiting for login.")
else:
    print("Login complete, shutting down server.")
    if httpd:
        httpd.shutdown()
