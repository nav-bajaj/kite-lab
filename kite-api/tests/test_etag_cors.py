"""
A 304 must still carry the CORS headers.

Regression test for a production failure on 2026-09-03. The browser
reported

    'Access-Control-Allow-Origin' has a value 'https://www.marketworks.in'
    that is not equal to the supplied origin

against a server whose CORS config was correct and which echoed the right
origin on every 200 — so the config was never the problem.

The cause was the conditional-request path. ETagMiddleware is mounted
OUTSIDE CORSMiddleware, so on a 304 it rebuilt the response from scratch
and kept only the caching headers, dropping Access-Control-Allow-Origin.
The browser then fell back to the ACAO stored alongside its cached copy —
cached under the www hostname — and rejected it against a request from
the apex origin.

The endpoint tests use a synthetic app rather than a real route because
every public JSON endpoint embeds a timestamp, so its ETag changes on
every call and the conditional path never runs.
"""

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.main import app as real_app
from app.middleware.etag import ETagMiddleware

ORIGIN = "https://marketworks.in"
OTHER_ORIGIN = "https://www.marketworks.in"


@pytest.fixture
def client():
    """Mirrors production: CORS inner, ETag outer, constant JSON body."""
    app = FastAPI()

    @app.get("/thing")
    def thing():
        return {"stable": "payload"}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[ORIGIN, OTHER_ORIGIN],
        allow_credentials=True,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(ETagMiddleware)
    return TestClient(app)


def test_200_carries_cors_headers_and_an_etag(client):
    res = client.get("/thing", headers={"Origin": ORIGIN})
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == ORIGIN
    assert res.headers.get("etag")


def test_304_still_carries_cors_headers(client):
    first = client.get("/thing", headers={"Origin": ORIGIN})
    etag = first.headers["etag"]

    second = client.get(
        "/thing", headers={"Origin": ORIGIN, "If-None-Match": etag}
    )
    assert second.status_code == 304, "expected the conditional path"
    assert second.headers.get("access-control-allow-origin") == ORIGIN, (
        "304 dropped Access-Control-Allow-Origin — the browser falls back "
        "to the value cached with its stored copy and reports a bogus CORS "
        "mismatch"
    )


def test_304_answers_the_origin_that_asked_not_the_one_that_cached(client):
    """The exact production failure: the body was first fetched under www,
    the revalidation came from the apex, and the apex must be answered."""
    first = client.get("/thing", headers={"Origin": OTHER_ORIGIN})
    etag = first.headers["etag"]
    assert first.headers["access-control-allow-origin"] == OTHER_ORIGIN

    second = client.get(
        "/thing", headers={"Origin": ORIGIN, "If-None-Match": etag}
    )
    assert second.status_code == 304
    assert second.headers.get("access-control-allow-origin") == ORIGIN


def test_304_preserves_vary_origin(client):
    """Vary: Origin is what stops a shared cache handing one origin's
    response to another."""
    first = client.get("/thing", headers={"Origin": ORIGIN})
    second = client.get(
        "/thing", headers={"Origin": ORIGIN, "If-None-Match": first.headers["etag"]}
    )
    assert second.status_code == 304
    assert "origin" in second.headers.get("vary", "").lower()


def test_etag_is_still_mounted_outside_cors_on_the_real_app():
    """If this ever flips, CORS would decorate the 304 itself and the
    coupling above stops being the thing under test — so the synthetic
    fixture would silently stop representing production."""
    names = [m.cls.__name__ for m in real_app.user_middleware]
    assert "ETagMiddleware" in names and "CORSMiddleware" in names
    assert names.index("ETagMiddleware") < names.index("CORSMiddleware"), (
        "middleware order changed; revisit whether ETag still needs to "
        "copy the CORS headers onto a 304"
    )
