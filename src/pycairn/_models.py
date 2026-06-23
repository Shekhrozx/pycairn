from __future__ import annotations

from datetime import datetime
from typing import Any
from pathlib import Path
from pydantic import BaseModel, Field

from pycairn import utils


class Artifact(BaseModel):
    path: str
    type: str | None = None          # "parquet", "model", "csv"...
    bytes: int | None = None
    sha256: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)  # rows, schema, etc.

    @classmethod
    def from_path(cls, path: str | Path, type: str | None = None, **meta: Any) -> "Artifact":
        """
        Create an Artifact instance from a file path.

        Args:
            path (str | Path): The file path.
            type (str | None): The type of the artifact (e.g., "parquet", "model", "csv").
            **meta (Any): Additional metadata.

        Returns:
            Artifact: The created Artifact instance.
        """

        p = Path(path)
        info: dict[str, Any] = {"path": str(p)}
        if p.exists() and p.is_file():
            info |= {"bytes": p.stat().st_size, "sha256": utils.sha256(p)}
        return cls(**info, type=type, meta=meta)


class Step(BaseModel):
    name: str
    status: utils.Status = utils.Status.pending          # pending|running|success|failed|skipped
    started_at: str | None = None
    ended_at: str | None = None
    duration_s: float | None = None
    inputs: list[str] = Field(default_factory=list)
    outputs: list[Artifact] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

    def add_artifact(self, artifact: Artifact) -> None:
        """
        Add an artifact to the step's outputs.

        Args:
            artifact (Artifact): The artifact to add.
        """
        if not isinstance(artifact, Artifact):
            raise TypeError(f"Expected Artifact, got {type(artifact).__name__}")

        if artifact in self.inputs:
            raise ValueError(f"Artifact with path '{artifact.path}' is already listed as an input.")

        self.outputs.append(artifact)
        return None

    def running(self, inputs: list[str] | None = None, params: dict | None = None) -> None:
        """
        Mark the step as running and record the start time.

        Args:
            inputs (list[str] | None): The input paths for the step.
            params (dict | None): The parameters for the step.
        """
        self.status = utils.Status.running
        self.started_at = utils.now_iso()
        self.inputs = inputs or []
        self.params = params or {}
        return None

    def failed(self, error: str) -> None:
        """
        Mark the step as failed and record the error message.

        Args:
            error (str): The error message.
        """
        self.status = utils.Status.failed
        self.error = error
        return None

    def success(self) -> None:
        """Mark the step as successful."""
        self.status = utils.Status.success
        return None

    def skipped(self) -> None:
        """Mark the step as skipped."""
        self.status = utils.Status.skipped
        return None

    def end(self, start: datetime) -> None:
        """
        Record the end time and calculate the duration of the step.

        Args:
            start (datetime): The start time of the step.
        """
        self.ended_at = utils.now_iso()
        self.duration_s = (utils.now() - start).total_seconds()
        return None


class Manifest(BaseModel):
    run_id: str
    pipeline: str
    created_at: str = Field(default_factory=utils.now_iso)
    status: utils.Status = utils.Status.running          # running|success|failed
    steps: list[Step] = Field(default_factory=list)

    def find_step(self, name: str) -> Step | None:
        """
        Find a step by name.

        Args:
            name (str): The name of the step.

        Returns:
            Step | None: The found step or None if not found.
        """
        return next((s for s in self.steps if s.name == name), None)

    def get_or_create_step(self, name: str) -> Step:
        """
        Get an existing step by name or create a new one if it doesn't exist.

        Args:
            name (str): The name of the step.

        Returns:
            Step: The found or newly created step.
        """
        step = self.find_step(name)
        if step is None:
            step = Step(name=name)
            self.steps.append(step)
        return step

    def output_of(self, step_name: str) -> list[Artifact]:
        """
        Get the outputs of a specific step by name.

        Args:
            step_name (str): The name of the step.

        Returns:
            list[Artifact]: A list of artifacts produced by the step.
        """
        step = self.find_step(step_name)
        return step.outputs if step else []

    def failed(self) -> None:
        """Mark the manifest status as failed."""
        self.status = utils.Status.failed
        return None

    def success(self) -> None:
        """Mark the manifest status as success."""
        self.status = utils.Status.success
        return None

    def is_all_done(self) -> bool:
        """Check if all steps are done (either success or skipped)."""
        return all(s.status in utils.SUCCESS_STATUSES for s in self.steps)