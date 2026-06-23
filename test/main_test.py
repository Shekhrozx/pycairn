from __future__ import annotations

import json

import pytest

from pycairn import Artifact, Cairn
from pycairn import utils


@pytest.fixture
def manifest_path(tmp_path):
    return tmp_path / "runs" / "manifest.json"


def _read(path):
    return json.loads(path.read_text())


# --------------------------------------------------------------------------- #
# Construction / persistence
# --------------------------------------------------------------------------- #
def test_init_creates_manifest_file_and_parents(manifest_path):
    c = Cairn(pipeline="etl", run_id="run-1", path=manifest_path)
    assert manifest_path.exists()
    assert manifest_path.parent.is_dir()

    data = _read(manifest_path)
    assert data["pipeline"] == "etl"
    assert data["run_id"] == "run-1"
    assert data["status"] == utils.Status.running
    assert data["steps"] == []
    assert c.manifest.run_id == "run-1"


def test_init_accepts_str_path(tmp_path):
    p = tmp_path / "m.json"
    Cairn(pipeline="etl", run_id="r", path=str(p))
    assert p.exists()


def test_init_loads_existing_manifest(manifest_path):
    first = Cairn(pipeline="etl", run_id="run-1", path=manifest_path)
    with first.step("load") as step:
        step.add_artifact(Artifact(path="data.csv"))

    # Re-open: should load the existing manifest, not overwrite it.
    second = Cairn(pipeline="ignored", run_id="ignored", path=manifest_path)
    assert second.manifest.run_id == "run-1"
    assert second.manifest.pipeline == "etl"
    assert second.manifest.find_step("load") is not None


def test_save_is_atomic_no_tmp_left_behind(manifest_path):
    Cairn(pipeline="etl", run_id="r", path=manifest_path)
    tmp = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    assert not tmp.exists()


def test_manifest_file_is_indented(manifest_path):
    Cairn(pipeline="etl", run_id="r", path=manifest_path)
    assert "\n  " in manifest_path.read_text()


# --------------------------------------------------------------------------- #
# step() success path
# --------------------------------------------------------------------------- #
def test_step_success_marks_step_and_run_done(manifest_path):
    c = Cairn(pipeline="etl", run_id="r", path=manifest_path)
    with c.step("load", inputs=["raw.csv"], params={"sep": ","}) as step:
        step.add_artifact(Artifact(path="clean.csv"))

    s = c.manifest.find_step("load")
    assert s.status == utils.Status.success
    assert s.inputs == ["raw.csv"]
    assert s.params == {"sep": ","}
    assert s.started_at is not None
    assert s.ended_at is not None
    assert s.duration_s is not None
    assert [a.path for a in s.outputs] == ["clean.csv"]

    # single step done -> whole run success
    assert c.manifest.status == utils.Status.success


def test_step_success_persisted_to_disk(manifest_path):
    c = Cairn(pipeline="etl", run_id="r", path=manifest_path)
    with c.step("load"):
        pass

    data = _read(manifest_path)
    assert data["status"] == utils.Status.success
    assert data["steps"][0]["name"] == "load"
    assert data["steps"][0]["status"] == utils.Status.success


def test_multiple_steps_run_success(manifest_path):
    c = Cairn(pipeline="etl", run_id="r", path=manifest_path)
    with c.step("load"):
        pass
    # after first step the run is briefly "success"; a new step reopens work
    with c.step("transform"):
        pass

    assert {s.name for s in c.manifest.steps} == {"load", "transform"}
    assert c.manifest.status == utils.Status.success


def test_yield_returns_the_step_object(manifest_path):
    c = Cairn(pipeline="etl", run_id="r", path=manifest_path)
    with c.step("load") as step:
        assert step is c.manifest.find_step("load")


# --------------------------------------------------------------------------- #
# step() failure path
# --------------------------------------------------------------------------- #
def test_step_failure_records_error_and_reraises(manifest_path):
    c = Cairn(pipeline="etl", run_id="r", path=manifest_path)

    with pytest.raises(ValueError, match="boom"):
        with c.step("load"):
            raise ValueError("boom")

    s = c.manifest.find_step("load")
    assert s.status == utils.Status.failed
    assert "boom" in s.error
    assert "ValueError" in s.error
    assert s.ended_at is not None
    assert s.duration_s is not None
    assert c.manifest.status == utils.Status.failed


def test_step_failure_persisted_to_disk(manifest_path):
    c = Cairn(pipeline="etl", run_id="r", path=manifest_path)
    with pytest.raises(RuntimeError):
        with c.step("load"):
            raise RuntimeError("kaboom")

    data = _read(manifest_path)
    assert data["status"] == utils.Status.failed
    assert data["steps"][0]["status"] == utils.Status.failed
    assert "kaboom" in data["steps"][0]["error"]


def test_failed_step_keeps_run_failed_even_if_others_succeed(manifest_path):
    c = Cairn(pipeline="etl", run_id="r", path=manifest_path)
    with pytest.raises(ValueError):
        with c.step("load"):
            raise ValueError("x")

    # A subsequent successful step should NOT flip the run back to success,
    # because the failed step is not in SUCCESS_STATUSES.
    with c.step("recover"):
        pass

    assert c.manifest.find_step("recover").status == utils.Status.success
    assert c.manifest.status == utils.Status.failed


# --------------------------------------------------------------------------- #
# Re-running / resuming steps
# --------------------------------------------------------------------------- #
def test_rerun_same_step_reuses_step_object(manifest_path):
    c = Cairn(pipeline="etl", run_id="r", path=manifest_path)
    with c.step("load") as s1:
        pass
    with c.step("load") as s2:
        pass

    assert s1 is s2
    assert len([s for s in c.manifest.steps if s.name == "load"]) == 1


def test_resume_after_failure(manifest_path):
    c = Cairn(pipeline="etl", run_id="r", path=manifest_path)
    with pytest.raises(ValueError):
        with c.step("load"):
            raise ValueError("first try")

    # reopen from disk and retry the same step successfully
    c2 = Cairn(pipeline="etl", run_id="r", path=manifest_path)
    with c2.step("load") as step:
        step.add_artifact(Artifact(path="ok.csv"))

    s = c2.manifest.find_step("load")
    assert s.status == utils.Status.success
    assert s.error is not None  # error from the previous attempt is retained
    assert c2.manifest.status == utils.Status.success


# --------------------------------------------------------------------------- #
# output_of
# --------------------------------------------------------------------------- #
def test_output_of_returns_artifacts(manifest_path):
    c = Cairn(pipeline="etl", run_id="r", path=manifest_path)
    with c.step("load") as step:
        step.add_artifact(Artifact(path="a.csv"))
        step.add_artifact(Artifact(path="b.csv"))

    outputs = c.output_of("load")
    assert [a.path for a in outputs] == ["a.csv", "b.csv"]


def test_output_of_unknown_step_is_empty(manifest_path):
    c = Cairn(pipeline="etl", run_id="r", path=manifest_path)
    assert c.output_of("nope") == []


def test_output_of_can_chain_steps(manifest_path):
    c = Cairn(pipeline="etl", run_id="r", path=manifest_path)
    with c.step("load") as step:
        step.add_artifact(Artifact(path="raw.parquet", type="parquet"))

    produced = c.output_of("load")
    with c.step("train", inputs=[a.path for a in produced]) as step:
        step.metrics["acc"] = 0.9

    assert c.manifest.find_step("train").inputs == ["raw.parquet"]
    assert c.manifest.find_step("train").metrics == {"acc": 0.9}
