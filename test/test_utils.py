from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pycairn import utils


def test_now_returns_utc_datetime():
    ts = utils.now()
    assert isinstance(ts, datetime)
    assert ts.tzinfo == timezone.utc


def test_now_iso_is_parseable_and_utc():
    iso = utils.now_iso()
    assert isinstance(iso, str)
    parsed = datetime.fromisoformat(iso)
    assert parsed.utcoffset() == timezone.utc.utcoffset(None)


def test_sha256_matches_hashlib(tmp_path):
    import hashlib

    f = tmp_path / "data.bin"
    payload = b"hello pycairn" * 1000
    f.write_bytes(payload)

    assert utils.sha256(f) == hashlib.sha256(payload).hexdigest()


def test_sha256_empty_file(tmp_path):
    import hashlib

    f = tmp_path / "empty.bin"
    f.write_bytes(b"")
    assert utils.sha256(f) == hashlib.sha256(b"").hexdigest()


def test_sha256_respects_chunking(tmp_path):
    """Small chunk size must produce the same digest as a single read."""
    import hashlib

    f = tmp_path / "big.bin"
    payload = b"x" * 5000
    f.write_bytes(payload)

    assert utils.sha256(f, chunk=16) == hashlib.sha256(payload).hexdigest()


def test_sha256_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        utils.sha256(tmp_path / "nope.bin")


def test_status_values():
    assert utils.Status.pending == "pending"
    assert utils.Status.running == "running"
    assert utils.Status.success == "success"
    assert utils.Status.failed == "failed"
    assert utils.Status.skipped == "skipped"


def test_success_statuses_contents():
    assert utils.Status.success in utils.SUCCESS_STATUSES
    assert utils.Status.skipped in utils.SUCCESS_STATUSES
    assert utils.Status.failed not in utils.SUCCESS_STATUSES
    assert utils.Status.pending not in utils.SUCCESS_STATUSES
    assert utils.Status.running not in utils.SUCCESS_STATUSES
