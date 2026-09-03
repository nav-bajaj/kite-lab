"""
ETag / conditional-request middleware.

For JSON GET responses, compute a weak ETag over the body and honour
``If-None-Match``: when the client already holds the current version we
reply ``304 Not Modified`` with no body, saving the payload transfer. This
pairs with the ``stale-while-revalidate`` Cache-Control policy — the
browser revalidates in the background and usually gets a tiny 304 back.

Scope is deliberately narrow (only ``application/json`` GET 200s) so it
never buffers or interferes with SSE streams (``text/event-stream``), file
downloads, or error responses.
"""

import hashlib

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Headers worth preserving on a 304 (RFC 7232 §4.1: send the headers you'd
# have sent on a 200 that affect caching).
_PRESERVE_ON_304 = ("cache-control", "vary", "etag")

# CORS headers MUST survive too. This middleware is mounted outside
# CORSMiddleware, so by the time we rebuild the response the CORS headers
# are already on it and rebuilding silently drops them. A 304 without
# Access-Control-Allow-Origin is rejected by the browser, and worse, the
# browser then falls back to the ACAO stored with its cached copy — so a
# response cached under www.marketworks.in gets replayed against a request
# from the apex domain and fails as an origin mismatch. That presents as a
# CORS misconfiguration on a server that is configured correctly.
_CORS_PREFIX = "access-control-"


class ETagMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.method != "GET" or response.status_code != 200:
            return response

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])
        etag = 'W/"%s"' % hashlib.sha1(body).hexdigest()

        if request.headers.get("if-none-match") == etag:
            not_modified = Response(status_code=304)
            for header in _PRESERVE_ON_304:
                if header in response.headers:
                    not_modified.headers[header] = response.headers[header]
            for key, value in response.headers.items():
                if key.lower().startswith(_CORS_PREFIX):
                    not_modified.headers[key] = value
            not_modified.headers["etag"] = etag
            return not_modified

        rebuilt = Response(
            content=body,
            status_code=200,
            media_type=content_type,
        )
        for key, value in response.headers.items():
            # Content-Length is recomputed by Response from the body.
            if key.lower() == "content-length":
                continue
            rebuilt.headers[key] = value
        rebuilt.headers["etag"] = etag
        return rebuilt
