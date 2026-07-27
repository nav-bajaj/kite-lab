"""
System Service - Health checks, token status, and sync information.
"""
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import text

from app.models.database import get_session_local
from app.models.models import EquityCurve, Job
from app.config import settings


class TokenStatus(BaseModel):
    """Kite API token status."""
    valid: bool
    expires_at: Optional[datetime] = None
    message: str


class DatabaseStatus(BaseModel):
    """Database connection status."""
    connected: bool
    latency_ms: Optional[float] = None
    message: str


class SyncStatus(BaseModel):
    """Data sync status."""
    last_sync: Optional[datetime] = None
    last_data_date: Optional[date] = None
    message: str


class SystemStatus(BaseModel):
    """Full system status."""
    api_health: bool
    database: DatabaseStatus
    token: TokenStatus
    sync: SyncStatus
    version: str = "1.0.1"
    environment: str = "production"


class SystemService:
    """Service for checking system health and status."""

    @staticmethod
    def get_status() -> SystemStatus:
        """
        Get comprehensive system status.

        Returns health of API, database, token, and sync status.
        """
        return SystemStatus(
            api_health=True,  # If we're here, API is up
            database=SystemService.check_database(),
            token=SystemService.check_token_status(),
            sync=SystemService.get_last_sync(),
            version="1.0.1",
            environment="production" if not settings.debug else "development"
        )

    @staticmethod
    def check_database() -> DatabaseStatus:
        """
        Check database connection health.

        Returns connection status and latency.
        """
        SessionLocal = get_session_local()

        try:
            db = SessionLocal()
            start = datetime.utcnow()

            # Simple query to test connection
            db.execute(text("SELECT 1"))

            latency = (datetime.utcnow() - start).total_seconds() * 1000

            db.close()

            return DatabaseStatus(
                connected=True,
                latency_ms=round(latency, 2),
                message="Connected"
            )

        except Exception as e:
            return DatabaseStatus(
                connected=False,
                latency_ms=None,
                message=f"Connection failed: {str(e)}"
            )

    @staticmethod
    def check_token_status() -> TokenStatus:
        """
        Check Kite API access token status.

        Reads access_token.txt and checks validity.
        Token expires daily at 6 AM IST.
        """
        token_path = settings.data_dir / "access_token.txt"

        if not token_path.exists():
            return TokenStatus(
                valid=False,
                expires_at=None,
                message="Token file not found"
            )

        try:
            # Read token and check modification time
            mtime = datetime.fromtimestamp(token_path.stat().st_mtime)
            token_content = token_path.read_text().strip()

            if not token_content:
                return TokenStatus(
                    valid=False,
                    expires_at=None,
                    message="Token file is empty"
                )

            # Token expires at 6 AM IST next day
            # For simplicity, check if token was created today
            today = datetime.now().date()
            token_date = mtime.date()

            if token_date < today:
                return TokenStatus(
                    valid=False,
                    expires_at=None,
                    message=f"Token expired (created {token_date})"
                )

            # Calculate expiry (6 AM IST next day)
            expires_at = datetime.combine(
                token_date + timedelta(days=1),
                datetime.strptime("06:00", "%H:%M").time()
            )

            return TokenStatus(
                valid=True,
                expires_at=expires_at,
                message="Token valid"
            )

        except Exception as e:
            return TokenStatus(
                valid=False,
                expires_at=None,
                message=f"Error reading token: {str(e)}"
            )

    @staticmethod
    def get_last_sync() -> SyncStatus:
        """
        Get last data sync timestamp.

        Checks latest equity curve date and last sync job.
        """
        SessionLocal = get_session_local()

        try:
            db = SessionLocal()

            # Get latest data date from equity curve
            latest_equity = db.query(EquityCurve).order_by(
                EquityCurve.date.desc()
            ).first()

            # Get last successful sync job
            last_sync_job = db.query(Job).filter(
                Job.command.in_(["daily_pipeline", "fetch_prices"]),
                Job.status == "completed"
            ).order_by(Job.ended_at.desc()).first()

            db.close()

            last_data_date = latest_equity.date if latest_equity else None
            last_sync = last_sync_job.ended_at if last_sync_job else None

            message = "No sync history"
            if last_data_date:
                days_old = (date.today() - last_data_date).days
                if days_old == 0:
                    message = "Data is current"
                elif days_old == 1:
                    message = "Data is 1 day old"
                else:
                    message = f"Data is {days_old} days old"

            return SyncStatus(
                last_sync=last_sync,
                last_data_date=last_data_date,
                message=message
            )

        except Exception as e:
            return SyncStatus(
                last_sync=None,
                last_data_date=None,
                message=f"Error checking sync: {str(e)}"
            )

    @staticmethod
    def get_login_url() -> str:
        """
        Get Kite login URL for OAuth.

        Returns URL user should open in browser.
        """
        api_key = settings.kite_api_key

        if not api_key:
            return ""

        return f"https://kite.zerodha.com/connect/login?api_key={api_key}&v=3"

    @staticmethod
    def headless_login() -> "TokenStatus":
        """
        Perform automated Zerodha login using requests + pyotp.

        Returns TokenStatus after login attempt.
        """
        import requests as req_lib

        try:
            import pyotp
        except ImportError:
            return TokenStatus(
                valid=False,
                message="pyotp not installed. Run: pip install pyotp"
            )

        from kiteconnect import KiteConnect
        import urllib.parse
        import logging

        logger = logging.getLogger(__name__)

        user_id = settings.kite_user_id
        password = settings.kite_password
        totp_secret = settings.totp_secret
        api_key = settings.kite_api_key
        api_secret = settings.kite_api_secret

        missing = []
        if not user_id:
            missing.append("KITE_USER_ID")
        if not password:
            missing.append("KITE_PASSWORD")
        if not totp_secret:
            missing.append("TOTP_SECRET")
        if not api_key:
            missing.append("KITE_API_KEY")
        if not api_secret:
            missing.append("KITE_API_SECRET")

        if missing:
            return TokenStatus(
                valid=False,
                message=f"Missing env vars: {', '.join(missing)}"
            )

        try:
            session = req_lib.Session()

            # Step 1: POST credentials
            resp = session.post("https://kite.zerodha.com/api/login", data={
                "user_id": user_id,
                "password": password,
            })
            if resp.status_code != 200:
                return TokenStatus(valid=False, message=f"Login failed (HTTP {resp.status_code})")

            login_data = resp.json()
            if login_data.get("status") != "success":
                return TokenStatus(valid=False, message=f"Login failed: {login_data.get('message', 'Unknown')}")

            request_id = login_data["data"]["request_id"]

            # Step 2: POST TOTP
            totp = pyotp.TOTP(totp_secret)
            resp = session.post("https://kite.zerodha.com/api/twofa", data={
                "user_id": user_id,
                "request_id": request_id,
                "twofa_value": totp.now(),
                "twofa_type": "totp",
            })
            if resp.status_code != 200:
                return TokenStatus(valid=False, message=f"TOTP failed (HTTP {resp.status_code})")

            twofa_data = resp.json()
            if twofa_data.get("status") != "success":
                return TokenStatus(valid=False, message=f"TOTP failed: {twofa_data.get('message', 'Unknown')}")

            # Step 3: Extract request_token by following redirect chain
            kite = KiteConnect(api_key=api_key)
            url = kite.login_url()
            request_token = None

            for _ in range(5):
                resp = session.get(url, allow_redirects=False)
                if resp.status_code not in (301, 302, 303, 307, 308):
                    break

                url = resp.headers.get("Location", "")
                if not url:
                    break

                parsed = urllib.parse.urlparse(url)
                qs = urllib.parse.parse_qs(parsed.query)
                token = qs.get("request_token", [None])[0]
                if token:
                    request_token = token
                    break

                # Stop before hitting localhost redirect_uri
                if any(url.startswith(p) for p in ("http://127.0.0.1", "http://localhost")):
                    break

            if not request_token:
                return TokenStatus(valid=False, message="No request_token in redirect chain")

            # Step 4: Exchange for access_token (reuse existing method)
            result = SystemService.exchange_request_token(request_token)
            logger.info(f"Headless login successful for user: {result.get('user_name', '')}")

            return SystemService.check_token_status()

        except Exception as e:
            logger.error(f"Headless login failed: {e}")
            return TokenStatus(valid=False, message=f"Headless login error: {str(e)}")

    @staticmethod
    def exchange_request_token(request_token: str) -> dict:
        """
        Exchange a Zerodha request_token for an access_token.

        Saves the access token to disk and returns session data.
        """
        from kiteconnect import KiteConnect
        import json

        api_key = settings.kite_api_key
        api_secret = settings.kite_api_secret

        missing = []
        if not api_key:
            missing.append("KITE_API_KEY")
        if not api_secret:
            missing.append("KITE_API_SECRET")
        if missing:
            raise ValueError(f"{', '.join(missing)} not configured in environment")

        kite = KiteConnect(api_key=api_key)
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]

        # Save token and session
        token_path = settings.data_dir / "access_token.txt"
        token_path.write_text(access_token)

        session_path = settings.data_dir / "session.json"

        def _json_serial(obj):
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        session_path.write_text(json.dumps(data, indent=2, default=_json_serial))

        # Mirror to Postgres for services on other Railway volumes (options
        # worker). Best-effort — a DB hiccup must not fail the login.
        try:
            from app.services.token_store import upsert_token

            upsert_token(access_token, user_name=data.get("user_name", ""), login_source="oauth_exchange")
        except Exception:
            logging.getLogger(__name__).warning("kite_session mirror failed (login still OK)", exc_info=True)

        return {"access_token": access_token, "user_name": data.get("user_name", "")}
