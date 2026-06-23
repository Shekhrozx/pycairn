from __future__ import annotations

import os
import traceback
from pathlib import Path
from contextlib import contextmanager

from pycairn import Artifact, Manifest, utils


class Cairn:
    def __init__(self, pipeline: str, run_id: str, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.manifest = Manifest.model_validate_json(self.path.read_text())
        else:
            self.manifest = Manifest(run_id=run_id, pipeline=pipeline)
        self._save()

    def _save(self) -> None:
        # atomic write: tmp -> fsync -> rename
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(self.manifest.model_dump_json(indent=2))
        os.replace(tmp, self.path)

    @contextmanager
    def step(self, name: str, inputs: list[str] | None = None, params: dict | None = None):
        step = self.manifest.get_or_create_step(name)

        step.running(inputs=inputs, params=params)
        self._save()

        start = utils.now()
        try:
            yield step                       # caller fills outputs/metrics
            step.success()
        except Exception:
            step.failed(traceback.format_exc())
            self.manifest.failed()
            self._save()
            raise
        finally:
            step.end(start)
            self._save()

        # mark whole run done if last step succeeded and nothing failed
        if self.manifest.is_all_done():
            self.manifest.success()
            self._save()

    def output_of(self, step_name: str) -> list[Artifact]:
        return self.manifest.output_of(step_name)