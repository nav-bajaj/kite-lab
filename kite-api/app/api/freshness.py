"""Admin data-freshness API — surfaces the per-source staleness report.

This is operational intelligence (which inputs are current, which have frozen),
not client-facing content, so it sits behind `require_admin` alongside the
other engine/ops routes. The founder hits GET /api/freshness to answer "is
anything stale?" — the response lists every data source with a
fresh/stale/critical/missing verdict and, for the stock panel, the worst
laggard symbols.

Mounted at `/api/freshness` from main.py.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import require_admin
from app.services.freshness_service import get_freshness_report

router = APIRouter(prefix="/api/freshness", tags=["freshness"])

# Short cache — the underlying files change at most once per EOD pipeline run,
# but ops wants a near-live read when investigating, so 60s keeps repeated
# dashboard polls cheap without masking a just-fixed source for long.
CACHE_TTL_SECONDS = 60


@router.get("")
async def freshness_endpoint(
    response: Response,
    user: dict = Depends(require_admin),
) -> dict:
    """Full per-source freshness report.

    Returns `generated_for_reference_date`, an `overall_status` (worst tier
    across all sources), and a `sources` list of per-source verdicts. Admin
    only — this exposes internal data-plumbing state.
    """
    response.headers["Cache-Control"] = f"private, max-age={CACHE_TTL_SECONDS}"
    try:
        return get_freshness_report()
    except Exception as exc:
        # The service is built to never raise, but keep a defensive shape so a
        # monitoring caller gets a clear 500 rather than a truncated body.
        raise HTTPException(status_code=500, detail=f"freshness report failed: {exc}")
