"""production_port_2026 P1: the 'master' upload target extracts a directory tree into the store, rejects traversal, and merges."""
import io, os, tarfile
from pathlib import Path
import pytest
from fastapi import HTTPException


def _tar_bytes(files: dict) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, content in files.items():
            data = content.encode(); info = tarfile.TarInfo(name); info.size = len(data); tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


@pytest.mark.anyio
async def test_master_upload_extracts_tree_and_merges(tmp_path, monkeypatch):
    import app.api.sync as sync
    from fastapi import UploadFile
    store = tmp_path / "master"; store.mkdir(); (store / "keep.txt").write_text("old")
    monkeypatch.setenv("MASTER_STORE_DIR", str(store))
    payload = _tar_bytes({"master/prices/adjusted_pr/A.csv": "date,close\n2026-01-01,1\n", "master/membership/nifty250.csv": "symbol,effective_from,effective_to,note\nA,2020-01-01,,\n"})
    up = UploadFile(filename="master.tar.gz", file=io.BytesIO(payload))
    r = await sync.upload_price_data(file=up, target="master", user={"email": "t@x"})
    assert r["files_written"] == 2
    assert (store / "prices/adjusted_pr/A.csv").read_text().startswith("date,close")
    assert (store / "keep.txt").read_text() == "old"           # merge: untouched files survive


@pytest.mark.anyio
async def test_master_upload_rejects_traversal(tmp_path, monkeypatch):
    import app.api.sync as sync
    from fastapi import UploadFile
    monkeypatch.setenv("MASTER_STORE_DIR", str(tmp_path / "master"))
    up = UploadFile(filename="master.tar.gz", file=io.BytesIO(_tar_bytes({"../escape.csv": "x"})))
    with pytest.raises(HTTPException) as e:
        await sync.upload_price_data(file=up, target="master", user={"email": "t@x"})
    assert e.value.status_code == 400
