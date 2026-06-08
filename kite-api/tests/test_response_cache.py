"""Tests for the in-process response cache and the ETag/304 middleware."""

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from app.middleware.etag import ETagMiddleware
from app.services.response_cache import cached_response, clear_response_cache


# ---------------------------------------------------------------------------
# response_cache
# ---------------------------------------------------------------------------


def test_cached_response_computes_once():
    clear_response_cache()
    calls = {"n": 0}

    def produce():
        calls["n"] += 1
        return {"value": calls["n"]}

    first = cached_response(("k", "nse500"), produce)
    second = cached_response(("k", "nse500"), produce)

    assert first == {"value": 1}
    assert second == {"value": 1}  # served from cache, producer not re-run
    assert calls["n"] == 1


def test_cached_response_separate_keys():
    clear_response_cache()

    a = cached_response(("k", "nse500"), lambda: {"u": "nse500"})
    b = cached_response(("k", "nifty250"), lambda: {"u": "nifty250"})

    assert a["u"] == "nse500"
    assert b["u"] == "nifty250"


def test_error_envelopes_are_not_cached():
    clear_response_cache()
    calls = {"n": 0}

    def produce():
        calls["n"] += 1
        return {"error": "boom"}

    cached_response(("k", "x"), produce)
    cached_response(("k", "x"), produce)

    assert calls["n"] == 2  # error result recomputed, never pinned


def test_clear_response_cache():
    clear_response_cache()
    calls = {"n": 0}

    def produce():
        calls["n"] += 1
        return {"value": calls["n"]}

    cached_response(("k", "x"), produce)
    clear_response_cache()
    cached_response(("k", "x"), produce)

    assert calls["n"] == 2


# ---------------------------------------------------------------------------
# ETag / 304 middleware
# ---------------------------------------------------------------------------


def _etag_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(ETagMiddleware)

    @app.get("/stable")
    def stable():
        return {"value": 42}

    @app.get("/text")
    def text():
        return PlainTextResponse("hello")

    return app


def test_etag_present_on_json_get():
    client = TestClient(_etag_app())
    r = client.get("/stable")
    assert r.status_code == 200
    assert r.headers.get("etag")
    assert r.json() == {"value": 42}


def test_matching_if_none_match_returns_304():
    client = TestClient(_etag_app())
    etag = client.get("/stable").headers["etag"]

    r = client.get("/stable", headers={"If-None-Match": etag})
    assert r.status_code == 304
    assert r.content == b""


def test_nonmatching_if_none_match_returns_200():
    client = TestClient(_etag_app())
    r = client.get("/stable", headers={"If-None-Match": 'W/"deadbeef"'})
    assert r.status_code == 200
    assert r.json() == {"value": 42}


def test_non_json_responses_are_untouched():
    client = TestClient(_etag_app())
    r = client.get("/text")
    assert r.status_code == 200
    assert "etag" not in {k.lower() for k in r.headers}
    assert r.text == "hello"
