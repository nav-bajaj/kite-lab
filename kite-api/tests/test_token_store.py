"""kite_session token store + worker token-read precedence."""
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.services import token_store


@pytest.fixture()
def db_url(tmp_path):
    return f"sqlite:///{tmp_path}/store.db"


class TestTokenStore:
    def test_read_before_any_write_returns_none(self, db_url):
        assert token_store.read_token(database_url=db_url) is None

    def test_upsert_creates_then_overwrites_single_row(self, db_url):
        token_store.upsert_token("tok-one", api_key="key-a", user_name="Nav", login_source="test", database_url=db_url)
        row = token_store.read_token(database_url=db_url)
        assert row["access_token"] == "tok-one"
        assert row["api_key"] == "key-a"
        assert row["login_source"] == "test"

        token_store.upsert_token("tok-two", api_key="key-b", user_name="Nav", login_source="test2", database_url=db_url)
        row = token_store.read_token(database_url=db_url)
        assert row["access_token"] == "tok-two"
        assert row["api_key"] == "key-b"
        assert row["id"] == 1

        from sqlalchemy import create_engine, text

        engine = create_engine(db_url)
        with engine.connect() as conn:
            count = conn.execute(text("select count(*) from kite_session")).scalar()
        engine.dispose()
        assert count == 1

    def test_read_bad_url_returns_none_not_raise(self):
        assert token_store.read_token(database_url="postgresql://nohost.invalid/db") is None


class TestWorkerTokenPrecedence:
    def _patch_env(self, monkeypatch, tmp_path, db_url):
        from app import config as app_config

        class FakeSettings:
            kite_api_key = "k"
            data_dir = tmp_path
            database_url = db_url

        monkeypatch.setattr(app_config, "get_settings", lambda: FakeSettings())
        import app.workers.options.worker as worker_mod

        orig_read = token_store.read_token
        monkeypatch.setattr(
            "app.services.token_store.read_token",
            lambda database_url=None: orig_read(database_url=db_url),
        )
        return worker_mod

    def test_db_only_pairs_stored_api_key(self, monkeypatch, tmp_path, db_url):
        worker_mod = self._patch_env(monkeypatch, tmp_path, db_url)
        token_store.upsert_token("db-token", api_key="db-app-key", database_url=db_url)
        assert worker_mod._read_credentials() == ("db-app-key", "db-token")

    def test_db_row_without_api_key_falls_back_to_env_key(self, monkeypatch, tmp_path, db_url):
        worker_mod = self._patch_env(monkeypatch, tmp_path, db_url)
        token_store.upsert_token("db-token", database_url=db_url)  # api_key empty
        assert worker_mod._read_credentials() == ("k", "db-token")

    def test_file_only_pairs_env_key(self, monkeypatch, tmp_path, db_url):
        worker_mod = self._patch_env(monkeypatch, tmp_path, db_url)
        (tmp_path / "access_token.txt").write_text("file-token\n")
        assert worker_mod._read_credentials() == ("k", "file-token")

    def test_fresher_source_wins(self, monkeypatch, tmp_path, db_url):
        worker_mod = self._patch_env(monkeypatch, tmp_path, db_url)
        (tmp_path / "access_token.txt").write_text("file-token")
        time.sleep(0.05)
        token_store.upsert_token("db-token", api_key="db-app-key", database_url=db_url)
        assert worker_mod._read_credentials() == ("db-app-key", "db-token")

    def test_neither_raises(self, monkeypatch, tmp_path, db_url):
        worker_mod = self._patch_env(monkeypatch, tmp_path, db_url)
        with pytest.raises(FileNotFoundError):
            worker_mod._read_credentials()
