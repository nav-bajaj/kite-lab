"""
Cache-Control header helpers for client-read endpoints.

Applied via FastAPI route dependencies. Three default buckets:

    cache_daily()      — once-a-day refresh data (portfolio, metrics,
                         trades, monthly returns, rebalance history)
    cache_rebalance()  — rebalance-day surfaces (status, preview, orders)
    cache_live()       — real-time-ish data (positions, quotes,
                         market-status)

The default policy is ``private`` (browser-only; no shared CDN cache).
Even though all users see the same per-universe data today, a per-user
data point could land here later — keeping the cache private is the
safer default.

``stale-while-revalidate`` lets the browser serve a stale response
immediately while it refetches in the background — better perceived
performance during the SWR window without violating the max-age
freshness guarantee.
"""

from fastapi import Response


def _make_cache_dep(max_age: int, swr: int = 86400):
    def _dep(response: Response) -> None:
        response.headers["Cache-Control"] = (
            f"private, max-age={max_age}, stale-while-revalidate={swr}"
        )

    return _dep


# Daily-refresh data: portfolio holdings, metrics, equity curve, trades,
# monthly returns, rebalance history. The daily pipeline refreshes these
# once per day; 1h max-age + 24h SWR gives fast subsequent navigations
# without ever serving truly stale data after the next pipeline run.
cache_daily = _make_cache_dep(max_age=3600, swr=86400)


# Rebalance-day surfaces. The status, preview, and orders endpoints flip
# state on Thursday/Friday; users may refresh repeatedly during that
# window. Shorter max-age keeps responses near-real-time.
cache_rebalance = _make_cache_dep(max_age=300, swr=3600)


# Live data — positions / quotes / market-status. Refreshes frequently
# during market hours. 60s max-age batches repeat fetches from the same
# page without making the data feel stale.
cache_live = _make_cache_dep(max_age=60, swr=300)
