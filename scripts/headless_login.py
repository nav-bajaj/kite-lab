"""
Headless Zerodha login using requests + pyotp.

Automates the browser-based OAuth flow by:
1. POST /api/login with user_id + password → request_id
2. POST /api/twofa with request_id + TOTP code (generated via pyotp) → session cookies
3. Follow kite.login_url() with authenticated session → extract request_token
4. Exchange request_token for access_token via KiteConnect SDK

Required env vars: KITE_USER_ID, KITE_PASSWORD, TOTP_SECRET, KITE_API_KEY, KITE_API_SECRET
"""
import os
import sys
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# Zerodha internal endpoints (undocumented, used by web app)
LOGIN_URL = "https://kite.zerodha.com/api/login"
TWOFA_URL = "https://kite.zerodha.com/api/twofa"


def json_serial(obj):
    """JSON serializer for datetime objects."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def headless_login():
    """
    Perform automated Zerodha login and save access token.

    Returns:
        dict with access_token and user_name on success
    Raises:
        SystemExit on failure
    """
    # Load credentials
    api_key = os.getenv("API_KEY") or os.getenv("KITE_API_KEY")
    api_secret = os.getenv("API_SECRET") or os.getenv("KITE_API_SECRET")
    user_id = os.getenv("KITE_USER_ID")
    password = os.getenv("KITE_PASSWORD")
    totp_secret = os.getenv("TOTP_SECRET")

    missing = []
    if not api_key:
        missing.append("KITE_API_KEY")
    if not api_secret:
        missing.append("KITE_API_SECRET")
    if not user_id:
        missing.append("KITE_USER_ID")
    if not password:
        missing.append("KITE_PASSWORD")
    if not totp_secret:
        missing.append("TOTP_SECRET")

    if missing:
        print(f"Headless login requires: {', '.join(missing)}")
        sys.exit(1)

    try:
        import pyotp
    except ImportError:
        print("pyotp is required for headless login: pip install pyotp")
        sys.exit(1)

    from kiteconnect import KiteConnect
    import urllib.parse

    session = requests.Session()

    # Step 1: POST credentials to get request_id
    print("Step 1: Authenticating with credentials...")
    resp = session.post(LOGIN_URL, data={
        "user_id": user_id,
        "password": password,
    })

    if resp.status_code != 200:
        print(f"Login failed (HTTP {resp.status_code}): {resp.text}")
        sys.exit(1)

    login_data = resp.json()
    if login_data.get("status") != "success":
        print(f"Login failed: {login_data.get('message', 'Unknown error')}")
        sys.exit(1)

    request_id = login_data["data"]["request_id"]
    print(f"  Got request_id: {request_id[:8]}...")

    # Step 2: POST TOTP for two-factor auth
    print("Step 2: Submitting TOTP...")
    totp = pyotp.TOTP(totp_secret)
    twofa_value = totp.now()

    resp = session.post(TWOFA_URL, data={
        "user_id": user_id,
        "request_id": request_id,
        "twofa_value": twofa_value,
        "twofa_type": "totp",
    })

    if resp.status_code != 200:
        print(f"TOTP verification failed (HTTP {resp.status_code}): {resp.text}")
        sys.exit(1)

    twofa_data = resp.json()
    if twofa_data.get("status") != "success":
        print(f"TOTP failed: {twofa_data.get('message', 'Unknown error')}")
        sys.exit(1)

    print("  Two-factor authentication successful")

    # Step 3: Hit the KiteConnect login URL with authenticated session
    # Zerodha may redirect through intermediate pages before reaching redirect_uri
    print("Step 3: Extracting request_token...")
    kite = KiteConnect(api_key=api_key)
    login_url = kite.login_url()

    redirect_uri = os.getenv("REDIRECT_URI", "http://127.0.0.1")

    # Follow the redirect chain manually, stopping when we hit our redirect_uri
    # or find request_token in the URL
    request_token = None
    url = login_url
    max_redirects = 5

    for i in range(max_redirects):
        resp = session.get(url, allow_redirects=False)

        if resp.status_code not in (301, 302, 303, 307, 308):
            # Not a redirect — check if the page itself contains useful info
            print(f"  Step 3.{i+1}: Got HTTP {resp.status_code} at {url[:80]}")
            break

        url = resp.headers.get("Location", "")
        if not url:
            print(f"  Step 3.{i+1}: Redirect with no Location header")
            break

        print(f"  Step 3.{i+1}: Following redirect to {url[:80]}...")

        # Check if this redirect URL contains request_token
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        token = qs.get("request_token", [None])[0]
        if token:
            request_token = token
            break

        # If the redirect points to our redirect_uri (localhost), don't follow it
        if url.startswith(redirect_uri) or url.startswith("http://127.0.0.1") or url.startswith("http://localhost"):
            break

    if not request_token:
        print(f"Could not extract request_token from redirect chain")
        print(f"Last URL: {url}")
        sys.exit(1)

    print(f"  Got request_token: {request_token[:8]}...")

    # Step 4: Exchange request_token for access_token
    print("Step 4: Exchanging for access_token...")
    data = kite.generate_session(request_token, api_secret=api_secret)
    access_token = data["access_token"]

    # Save token with restricted permissions
    token_path = "access_token.txt"
    with open(token_path, "w") as f:
        f.write(access_token)
    os.chmod(token_path, 0o600)

    # Save full session JSON
    session_path = "session.json"
    with open(session_path, "w") as f:
        json.dump(data, f, indent=2, default=json_serial)
    os.chmod(session_path, 0o600)

    user_name = data.get("user_name", "")
    print(f"\nHeadless login successful! User: {user_name}")
    print(f"Access token saved to {token_path}")

    _upsert_token_to_db(access_token, api_key, user_name)

    return {"access_token": access_token, "user_name": user_name}


def _upsert_token_to_db(access_token, api_key, user_name):
    """Mirror the token into Postgres (kite_session) so services that can't
    read this container's volume — the options worker — get the day's token.
    Best-effort: the file above stays the primary store; a DB failure must
    never fail the login itself."""
    if not os.getenv("DATABASE_URL"):
        return
    try:
        from app.services.token_store import upsert_token
    except ImportError:
        # Local runs from the repo root don't have kite-api/app on the path;
        # in the Docker container PYTHONPATH=/app makes it importable.
        print("token DB mirror skipped: app package not importable")
        return
    try:
        upsert_token(access_token, api_key=api_key, user_name=user_name, login_source="headless_login")
        print("Access token mirrored to Postgres (kite_session)")
    except Exception as e:
        print(f"WARNING: token DB mirror failed (login still OK): {e}")


if __name__ == "__main__":
    headless_login()
