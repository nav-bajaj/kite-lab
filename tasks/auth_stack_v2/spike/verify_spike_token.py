"""
S0.5 spike verifier — proves a REAL access token from the scratch
project passes the exact verification rules the spec suite pins
(ES256 only, kid resolved in the live JWKS, pinned issuer,
aud=authenticated, role from app_metadata only). NOT production code —
the production implementation lands in kite-api/app/auth.py at B1.3.

Run: python tasks/auth_stack_v2/spike/verify_spike_token.py
"""

import json
import pathlib
import sys

import httpx
from jose import jwt

PROJECT_REF = "jhvkfokskanbaiipvcqu"
ISSUER = f"https://{PROJECT_REF}.supabase.co/auth/v1"
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"
TOKEN_FILE = pathlib.Path(__file__).parent / ".captured_token"


def extract_app_role(payload: dict) -> str:
    """SI-1: app_metadata.role only; default client."""
    role = (payload.get("app_metadata") or {}).get("role")
    return role if role in ("admin", "client") else "client"


def main() -> int:
    if not TOKEN_FILE.exists():
        print("no .captured_token — run serve_spike.py and sign in first")
        return 1
    token = TOKEN_FILE.read_text().strip()

    header = jwt.get_unverified_header(token)
    print(f"header: alg={header.get('alg')} kid={header.get('kid')}")
    if header.get("alg") != "ES256":
        print("FAIL SI-2: token not ES256 — signing-key migration not active?")
        return 1

    jwks = httpx.get(JWKS_URL, timeout=5.0).json()
    key = next(
        (k for k in jwks["keys"] if k["kid"] == header.get("kid")), None
    )
    if key is None:
        print("FAIL SI-2: token kid not present in live JWKS")
        return 1

    payload = jwt.decode(
        token, key, algorithms=["ES256"], issuer=ISSUER,
        audience="authenticated",
    )

    print("verified OK against live JWKS")
    print(f"  sub:            {payload['sub']}")
    print(f"  email:          {payload.get('email')}")
    print(f"  iss:            {payload['iss']}")
    print(f"  aud:            {payload.get('aud')}")
    print(f"  native role:    {payload.get('role')} (PostgREST — ignored)")
    print(f"  app_metadata:   {json.dumps(payload.get('app_metadata'))}")
    print(f"  user_metadata:  {json.dumps(payload.get('user_metadata'))}")
    print(f"  -> app role:    {extract_app_role(payload)}")
    if "app_metadata" not in payload:
        print("NOTE: app_metadata claim ABSENT — custom access token hook")
        print("      is required after all; update PLAN/TASKS S0.4.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
