from __future__ import annotations

from datetime import timedelta

import pytest

from pycairn import Artifact, Manifest, Step
from pycairn import utils


# --------------------------------------------------------------------------- #
# Artifact
# --------------------------------------------------------------------------- #
def test_artifact_defaults():
    a = Artifact(path="out.csv")
    assert a.path == "out.csv"
    assert a.type is None
    assert a.bytes is None
    assert a.sha256 is None
    assert a.meta == {}


def test_artifact_from_path_existing_file(tmp_path):
    import hashlib

    f = tmp_path / "model.bin"
    payload = b"weights"
    f.write_bytes(payload)

    a = Artifact.from_path(f, type="model", rows=10)
    assert a.path == str(f)
    assert a.type == "model"
    assert a.bytes == len(payload)
    assert a.sha256 == hashlib.sha256(payload).hexdigest()
    assert a.meta == {"rows": 10}


def test_artifact_from_path_missing_file(tmp_path):
    missing = tmp_path / "ghost.csv"
    a = Artifact.from_path(missing, type="csv")
    assert a.path == str(missing)
    assert a.type == "csv"
    assert a.bytes is None
    assert a.sha256 is None
    assert a.meta == {}


def test_artifact_from_path_directory_not_treated_as_file(tmp_path):
    a = Artifact.from_path(tmp_path)
    assert a.bytes is None
    assert a.sha256 is None


def test_artifact_from_path_accepts_str(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("hi")
    a = Artifact.from_path(str(f))
    assert a.bytes == 2


# --------------------------------------------------------------------------- #
# Step
# --------------------------------------------------------------------------- #
def test_step_defaults():
    s = Step(name="train")
    assert s.name == "train"
    assert s.status == utils.Status.pending
    assert s.started_at is None
    assert s.ended_at is None
    assert s.duration_s is None
    assert s.inputs == []
    assert s.outputs == []
    assert s.metrics == {}
    assert s.params == {}
    assert s.error is None


def test_step_running_sets_state():
    s = Step(name="load")
    s.running(inputs=["a.csv"], params={"lr": 0.1})
    assert s.status == utils.Status.running
    assert s.started_at is not None
    assert s.inputs == ["a.csv"]
    assert s.params == {"lr": 0.1}


def test_step_running_defaults_none_args():
    s = Step(name="load")
    s.running()
    assert s.inputs == []
    assert s.params == {}


def test_step_success_and_failed_and_skipped():
    s = Step(name="x")
    s.success()
    assert s.status == utils.Status.success

    s.failed("boom")
    assert s.status == utils.Status.failed
    assert s.error == "boom"

    s.skipped()
    assert s.status == utils.Status.skipped


def test_step_end_records_duration():
    s = Step(name="x")
    start = utils.now() - timedelta(seconds=2)
    s.end(start)
    assert s.ended_at is not None
    assert s.duration_s is not None
    assert s.duration_s >= 2


def test_step_add_artifact_appends():
    s = Step(name="x")
    art = Artifact(path="out.parquet")
    s.add_artifact(art)
    assert s.outputs == [art]


def test_step_add_artifact_type_check():
    s = Step(name="x")
    with pytest.raises(TypeError):
        s.add_artifact("not-an-artifact")  # type: ignore[arg-type]


def test_step_add_artifact_multiple():
    s = Step(name="x")
    s.add_artifact(Artifact(path="a"))
    s.add_artifact(Artifact(path="b"))
    assert [a.path for a in s.outputs] == ["a", "b"]


# --------------------------------------------------------------------------- #
# Manifest
# --------------------------------------------------------------------------- #
def test_manifest_defaults():
    m = Manifest(run_id="r1", pipeline="p1")
    assert m.run_id == "r1"
    assert m.pipeline == "p1"
    assert m.created_at is not None
    assert m.status == utils.Status.running
    assert m.steps == []


def test_manifest_find_step():
    m = Manifest(run_id="r", pipeline="p")
    assert m.find_step("missing") is None
    s = m.get_or_create_step("train")
    assert m.find_step("train") is s


def test_manifest_get_or_create_is_idempotent():
    m = Manifest(run_id="r", pipeline="p")
    first = m.get_or_create_step("train")
    second = m.get_or_create_step("train")
    assert first is second
    assert len(m.steps) == 1


def test_manifest_output_of_missing_returns_empty():
    m = Manifest(run_id="r", pipeline="p")
    assert m.output_of("nope") == []


def test_manifest_output_of_returns_step_outputs():
    m = Manifest(run_id="r", pipeline="p")
    s = m.get_or_create_step("train")
    art = Artifact(path="model.bin")
    s.add_artifact(art)
    assert m.output_of("train") == [art]


def test_manifest_failed_and_success():
    m = Manifest(run_id="r", pipeline="p")
    m.failed()
    assert m.status == utils.Status.failed
    m.success()
    assert m.status == utils.Status.success


def test_is_all_done_empty_is_true():
    """all() over an empty list is vacuously true."""
    m = Manifest(run_id="r", pipeline="p")
    assert m.is_all_done() is True


def test_is_all_done_with_success_and_skipped():
    m = Manifest(run_id="r", pipeline="p")
    m.get_or_create_step("a").success()
    m.get_or_create_step("b").skipped()
    assert m.is_all_done() is True


def test_is_all_done_false_with_running_or_failed():
    m = Manifest(run_id="r", pipeline="p")
    m.get_or_create_step("a").success()
    running = m.get_or_create_step("b")
    running.running()
    assert m.is_all_done() is False

    running.failed("x")
    assert m.is_all_done() is False


def test_manifest_json_roundtrip():
    m = Manifest(run_id="r", pipeline="p")
    s = m.get_or_create_step("train")
    s.add_artifact(Artifact(path="model.bin", type="model", bytes=10))
    s.success()

    loaded = Manifest.model_validate_json(m.model_dump_json())
    assert loaded.run_id == "r"
    assert loaded.pipeline == "p"
    assert loaded.find_step("train").outputs[0].path == "model.bin"
    assert loaded.find_step("train").status == utils.Status.success
