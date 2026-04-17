"""
Quotes service for fetching live prices from Zerodha API.

Provides caching to avoid rate limiting and handle token expiry gracefully.
"""
from datetime import datetime
from typing import Dict, List, Optional
import threading
import logging

from cachetools import TTLCache

from app.config import get_settings
from app.schemas.positions import LiveQuote

logger = logging.getLogger(__name__)

# Thread-safe cache with 2-second TTL for quotes
_quotes_cache: TTLCache = TTLCache(maxsize=100, ttl=2)
_cache_lock = threading.Lock()

# KiteConnect client singleton (rebuilt when token changes)
_kite_client = None
_kite_token = None
_kite_lock = threading.Lock()


class TokenExpiredError(Exception):
    """Zerodha access token has expired."""
    pass


class QuotesFetchError(Exception):
    """Failed to fetch quotes from Zerodha API."""
    pass


def get_kite_client():
    """
    Get or create KiteConnect client instance.

    Re-reads access token from disk each call. If the token has changed
    (e.g. user re-logged in), rebuilds the client with the new token.

    Returns:
        KiteConnect instance with current access token set

    Raises:
        TokenExpiredError: If access token is missing
    """
    global _kite_client, _kite_token

    with _kite_lock:
        settings = get_settings()

        if not settings.kite_api_key:
            raise QuotesFetchError("KITE_API_KEY not configured")

        # Always re-read token from disk — it may have been refreshed via login
        access_token = _read_access_token(settings)
        if not access_token:
            _kite_client = None
            _kite_token = None
            raise TokenExpiredError("Access token not found. Please login first.")

        # Reuse cached client only if token hasn't changed
        if _kite_client is not None and _kite_token == access_token:
            return _kite_client

        try:
            from kiteconnect import KiteConnect
        except ImportError:
            raise QuotesFetchError("kiteconnect package not installed")

        kite = KiteConnect(api_key=settings.kite_api_key)
        kite.set_access_token(access_token)

        _kite_client = kite
        _kite_token = access_token
        return _kite_client


def _read_access_token(settings) -> Optional[str]:
    """Read access token from file."""
    # Try multiple locations
    token_paths = [
        settings.data_dir / "access_token.txt",
        settings.data_dir.parent / "access_token.txt",  # In case of different layout
    ]

    for token_path in token_paths:
        if token_path.exists():
            try:
                token = token_path.read_text().strip()
                if token:
                    logger.info(f"Loaded access token from {token_path}")
                    return token
            except Exception as e:
                logger.warning(f"Failed to read token from {token_path}: {e}")

    return None


def reset_kite_client():
    """Reset the KiteConnect client (used when token expires)."""
    global _kite_client, _kite_token
    with _kite_lock:
        _kite_client = None
        _kite_token = None


def get_live_quotes(symbols: List[str]) -> Dict[str, LiveQuote]:
    """
    Fetch live quotes from Zerodha API.

    Args:
        symbols: List of trading symbols (e.g., ["INFY", "TCS"])

    Returns:
        Dict mapping symbol to LiveQuote

    Raises:
        TokenExpiredError: If access token has expired
        QuotesFetchError: If API call fails
    """
    if not symbols:
        return {}

    kite = get_kite_client()

    # Build instrument list (NSE: prefix required for Zerodha)
    instruments = [f"NSE:{symbol}" for symbol in symbols]

    try:
        # Zerodha quote() returns full quote data
        quotes_data = kite.quote(instruments)

        result = {}
        for instrument, data in quotes_data.items():
            symbol = instrument.replace("NSE:", "")
            ohlc = data.get("ohlc", {})

            # Calculate change values
            ltp = data.get("last_price", 0)
            prev_close = ohlc.get("close", ltp)  # Fallback to LTP if no close
            change = ltp - prev_close if prev_close else 0
            change_pct = (change / prev_close * 100) if prev_close else 0

            result[symbol] = LiveQuote(
                symbol=symbol,
                instrument_token=data.get("instrument_token"),
                ltp=ltp,
                open=ohlc.get("open", 0),
                high=ohlc.get("high", 0),
                low=ohlc.get("low", 0),
                close=prev_close,
                change=change,
                change_pct=change_pct,
                volume=data.get("volume", 0),
                last_trade_time=data.get("last_trade_time")
            )

        return result

    except Exception as e:
        error_msg = str(e).lower()
        # Check for token expiry
        if "token" in error_msg and ("invalid" in error_msg or "expired" in error_msg):
            reset_kite_client()
            raise TokenExpiredError("Access token has expired. Please login again.")

        logger.error(f"Failed to fetch quotes: {e}")
        raise QuotesFetchError(f"Failed to fetch quotes: {e}")


def get_cached_quotes(symbols: List[str], universe: str) -> Dict[str, LiveQuote]:
    """
    Get quotes with caching to avoid rate limiting.

    Args:
        symbols: List of trading symbols
        universe: Universe ID for cache key

    Returns:
        Dict mapping symbol to LiveQuote
    """
    if not symbols:
        return {}

    cache_key = f"{universe}:{','.join(sorted(symbols))}"

    with _cache_lock:
        if cache_key in _quotes_cache:
            logger.debug(f"Cache hit for {universe}")
            return _quotes_cache[cache_key]

    # Cache miss - fetch from API
    quotes = get_live_quotes(symbols)

    with _cache_lock:
        _quotes_cache[cache_key] = quotes

    return quotes


def get_ltp_only(symbols: List[str]) -> Dict[str, float]:
    """
    Get only LTP (Last Traded Price) for symbols.

    Uses kite.ltp() which is faster than kite.quote() for just prices.

    Args:
        symbols: List of trading symbols

    Returns:
        Dict mapping symbol to LTP
    """
    if not symbols:
        return {}

    kite = get_kite_client()
    instruments = [f"NSE:{symbol}" for symbol in symbols]

    try:
        ltp_data = kite.ltp(instruments)

        result = {}
        for instrument, data in ltp_data.items():
            symbol = instrument.replace("NSE:", "")
            result[symbol] = data.get("last_price", 0)

        return result

    except Exception as e:
        error_msg = str(e).lower()
        if "token" in error_msg and ("invalid" in error_msg or "expired" in error_msg):
            reset_kite_client()
            raise TokenExpiredError("Access token has expired. Please login again.")

        raise QuotesFetchError(f"Failed to fetch LTP: {e}")
