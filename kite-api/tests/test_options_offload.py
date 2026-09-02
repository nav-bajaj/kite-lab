"""Phase 6 archive offload — Drive upload + verified local prune."""
import hashlib
from datetime import date
from pathlib import Path

import pytest

from app.workers.options.offload import _md5_local, offload_archives


def make_archive(archive_dir: Path, d: str, body: bytes = b"tickdata") -> Path:
    archive_dir.mkdir(parents=True, exist_ok=True)
    p = archive_dir / f"{d}.tar.gz"
    p.write_bytes(body)
    return p


class FakeDrive:
    """Minimal googleapiclient Drive v3 stand-in.

    Records uploads by name; ``corrupt`` forces an md5 mismatch on upload so
    the caller's verify-before-delete path can be exercised.
    """

    def __init__(self, existing=None, corrupt=False, fail_on=None):
        self.store = dict(existing or {})   # name -> {"md5Checksum", "size"}
        self.corrupt = corrupt
        self.fail_on = fail_on or set()
        self.uploads = []
        self.folders = {}
        self._next_id = 0

    # -- googleapiclient surface -------------------------------------------
    def files(self):
        return self

    def list(self, q=None, fields=None, pageSize=None, pageToken=None):
        self._last_q = q
        return self

    def create(self, body=None, media_body=None, fields=None):
        self._pending_create = (body, media_body)
        return self

    def execute(self):
        if hasattr(self, "_pending_create"):
            body, media = self._pending_create
            del self._pending_create
            if body.get("mimeType") == "application/vnd.google-apps.folder":
                self._next_id += 1
                fid = f"folder-{self._next_id}"
                self.folders[body["name"]] = fid
                return {"id": fid}
            name = body["name"]
            if name in self.fail_on:
                raise RuntimeError("drive 503")
            data = Path(media._path).read_bytes() if hasattr(media, "_path") else b""
            md5 = hashlib.md5(data, usedforsecurity=False).hexdigest()
            if self.corrupt:
                md5 = "0" * 32
            self.uploads.append(name)
            self.store[name] = {"md5Checksum": md5, "size": str(len(data))}
            return {"id": f"file-{name}", "name": name, "size": str(len(data)),
                    "md5Checksum": md5}

        q = self._last_q or ""
        if "application/vnd.google-apps.folder" in q:
            return {"files": []}          # always create folders fresh
        return {"files": [dict(name=n, id=f"file-{n}", **m)
                          for n, m in self.store.items()]}


@pytest.fixture(autouse=True)
def _stub_media(monkeypatch):
    """MediaFileUpload without the google client library."""
    class _Media:
        def __init__(self, path, mimetype=None, resumable=False):
            self._path = path

    import app.workers.options.offload as mod
    monkeypatch.setattr(
        mod, "_upload",
        lambda svc, path, folder_id: svc.files().create(
            body={"name": path.name, "parents": [folder_id]},
            media_body=_Media(str(path)),
            fields="id, name, size, md5Checksum",
        ).execute(),
    )


class TestOffload:
    def test_aged_archives_uploaded_and_pruned_recent_kept(self, tmp_path):
        arch = tmp_path / "ticks_archive"
        old1 = make_archive(arch, "2026-08-20", b"a" * 100)
        old2 = make_archive(arch, "2026-08-21", b"b" * 100)
        keep_edge = make_archive(arch, "2026-08-27")   # exactly keep days old
        keep = make_archive(arch, "2026-08-28")

        drive = FakeDrive()
        stats = offload_archives(arch, 5, date(2026, 9, 1), service=drive)

        assert stats["uploaded"] == 2 and stats["pruned"] == 2 and stats["failed"] == 0
        assert not old1.exists() and not old2.exists()
        assert keep_edge.exists() and keep.exists()
        assert sorted(drive.uploads) == ["2026-08-20.tar.gz", "2026-08-21.tar.gz"]

    def test_md5_mismatch_keeps_local_copy(self, tmp_path):
        arch = tmp_path / "ticks_archive"
        p = make_archive(arch, "2026-08-20")

        stats = offload_archives(arch, 5, date(2026, 9, 1), service=FakeDrive(corrupt=True))

        assert stats["uploaded"] == 1 and stats["pruned"] == 0 and stats["failed"] == 1
        assert p.exists(), "a corrupt upload must never delete the only good copy"

    def test_already_in_drive_is_pruned_not_reuploaded(self, tmp_path):
        """The crash-between-upload-and-delete case."""
        arch = tmp_path / "ticks_archive"
        p = make_archive(arch, "2026-08-20", b"c" * 50)
        drive = FakeDrive(existing={"2026-08-20.tar.gz": {"md5Checksum": _md5_local(p)}})

        stats = offload_archives(arch, 5, date(2026, 9, 1), service=drive)

        assert stats["pruned"] == 1 and stats["uploaded"] == 0
        assert drive.uploads == []
        assert not p.exists()

    def test_name_collision_different_content_keeps_both(self, tmp_path):
        arch = tmp_path / "ticks_archive"
        p = make_archive(arch, "2026-08-20", b"local")
        drive = FakeDrive(existing={"2026-08-20.tar.gz": {"md5Checksum": "deadbeef"}})

        stats = offload_archives(arch, 5, date(2026, 9, 1), service=drive)

        assert stats["failed"] == 1 and stats["pruned"] == 0
        assert p.exists() and drive.uploads == []

    def test_upload_error_is_isolated_to_one_file(self, tmp_path):
        arch = tmp_path / "ticks_archive"
        bad = make_archive(arch, "2026-08-20")
        good = make_archive(arch, "2026-08-21")
        drive = FakeDrive(fail_on={"2026-08-20.tar.gz"})

        stats = offload_archives(arch, 5, date(2026, 9, 1), service=drive)

        assert stats["failed"] == 1 and stats["pruned"] == 1
        assert bad.exists() and not good.exists()

    def test_max_files_bounds_one_run(self, tmp_path):
        arch = tmp_path / "ticks_archive"
        for d in ["2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20"]:
            make_archive(arch, d)

        drive = FakeDrive()
        stats = offload_archives(arch, 5, date(2026, 9, 1), service=drive, max_files=2)

        assert stats["pruned"] == 2
        assert len(list(arch.iterdir())) == 2
        # oldest first, so the backlog drains in order
        assert drive.uploads == ["2026-08-17.tar.gz", "2026-08-18.tar.gz"]

    def test_partial_files_are_never_offloaded(self, tmp_path):
        arch = tmp_path / "ticks_archive"
        arch.mkdir(parents=True)
        partial = arch / "2026-08-20.tar.gz.partial"
        partial.write_bytes(b"half")

        stats = offload_archives(arch, 5, date(2026, 9, 1), service=FakeDrive())

        assert stats == {"uploaded": 0, "pruned": 0, "skipped": 0, "failed": 0, "freed_mb": 0.0}
        assert partial.exists()

    def test_no_credentials_is_a_no_op_not_an_error(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GDRIVE_REFRESH_TOKEN_JSON", raising=False)
        arch = tmp_path / "ticks_archive"
        p = make_archive(arch, "2026-08-20")

        stats = offload_archives(arch, 5, date(2026, 9, 1))

        assert stats["skipped"] == 1 and stats["failed"] == 0
        assert p.exists()

    def test_missing_archive_dir_is_harmless(self, tmp_path):
        stats = offload_archives(tmp_path / "nope", 5, date(2026, 9, 1), service=FakeDrive())
        assert stats["uploaded"] == 0 and stats["failed"] == 0
