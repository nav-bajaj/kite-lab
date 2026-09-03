"""
Shared endpoint inventories for the authz suites.

A PLAIN module on purpose: it sets no environment variables and imports no
app code. The inventories used to live in a test module and get imported
across suites, which silently broke things — two test modules each did
`os.environ.setdefault("CLERK_ISSUER", ...)` with different values, so
whichever imported first won and the other suite's tokens failed with
"Token issuer not recognized". Keeping the data here removes the
cross-module import that caused it.

Every endpoint the API exposes should appear in exactly one of these
lists. Adding a route without adding it here means it ships ungated by
any test.
"""

_U = "?universe=l6_v2"

# Admin / mutation endpoints. A client-role token must get 403.
ADMIN_ENDPOINTS: list[tuple[str, str]] = [
    # jobs.py
    ("GET", "/api/jobs"),
    ("POST", "/api/jobs"),
    ("GET", "/api/jobs/nonexistent-job"),
    ("GET", "/api/jobs/nonexistent-job/logs"),
    ("POST", "/api/jobs/nonexistent-job/cancel"),
    # schedule.py
    ("GET", "/api/schedule"),
    ("POST", "/api/schedule"),
    ("DELETE", "/api/schedule/nonexistent"),
    ("POST", "/api/schedule/nonexistent/run"),
    ("GET", "/api/schedule/defaults"),
    # sync.py
    ("POST", "/api/sync"),
    ("POST", "/api/sync/all"),
    # positions.py (mutations only)
    ("POST", "/api/positions/sync"),
    ("POST", "/api/positions/sync-from-csv"),
    # system.py
    ("POST", "/api/system/headless-login"),
    # insights.py
    ("POST", "/api/insights/cache/clear"),
    # freshness.py
    ("GET", "/api/freshness"),
    # options_worker.py
    ("GET", "/api/options/worker-status"),
    ("GET", "/api/options/live-analytics"),
    # waitlist.py — readout, export and list management (email_channel)
    ("GET", "/api/waitlist"),
    ("GET", "/api/waitlist/export.csv"),
    ("DELETE", "/api/waitlist?email=a@b.co"),
    ("POST", "/api/waitlist/promote"),
    ("POST", "/api/waitlist/send-welcome?email=a@b.co"),
]

# Client-read endpoints. A client-role token must get a non-401/403.
CLIENT_READ_ENDPOINTS: list[tuple[str, str]] = [
    # portfolio.py
    ("GET", f"/api/portfolio{_U}"),
    ("GET", f"/api/portfolio/holdings{_U}"),
    ("GET", f"/api/portfolio/allocation{_U}"),
    # metrics.py
    ("GET", f"/api/metrics{_U}"),
    ("GET", f"/api/metrics/equity-curve{_U}"),
    ("GET", f"/api/metrics/monthly-returns{_U}"),
    # trades.py
    ("GET", f"/api/trades{_U}"),
    ("GET", f"/api/trades/summary{_U}"),
    ("GET", f"/api/trades/recent{_U}"),
    ("GET", f"/api/trades/export{_U}"),
    # rebalance.py
    ("GET", f"/api/rebalance/summary{_U}"),
    ("GET", f"/api/rebalance/preview{_U}"),
    ("GET", f"/api/rebalance/orders{_U}"),
    ("GET", f"/api/rebalance/orders/export{_U}"),
    ("GET", f"/api/rebalance/history{_U}"),
    ("GET", f"/api/rebalance/upcoming{_U}"),
    # positions.py reads
    ("GET", f"/api/positions{_U}"),
    ("GET", f"/api/positions/holdings{_U}"),
    ("GET", f"/api/positions/quotes{_U}"),
    # auth_routes.py
    ("GET", "/api/auth/me"),
    ("GET", "/api/auth/verify"),
]

# Always-unauthenticated endpoints. No token needed; must return non-401/403.
PUBLIC_ENDPOINTS: list[tuple[str, str]] = [
    ("GET", "/api/health"),
    ("GET", "/api/positions/market-status"),
    ("GET", "/api/system/status"),
    ("GET", "/api/system/token"),
    ("GET", "/api/system/database"),
    ("GET", "/api/system/sync"),
    ("GET", "/api/system/login-url"),
    # waitlist.py — the signup form is public by design (R-027), and the
    # consent endpoints carry a token as their only credential. Mail
    # clients call unsubscribe unauthenticated for RFC 8058 one-click.
    ("POST", "/api/waitlist"),
    ("POST", "/api/waitlist/unsubscribe"),
    ("GET", "/api/waitlist/unsubscribe"),
    ("GET", "/api/waitlist/confirm"),
]
