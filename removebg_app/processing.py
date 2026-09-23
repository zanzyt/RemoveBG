import os
import queue
import shutil
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps
from rembg import new_session, remove

from .config import DONE_DIR, ERROR_DIR, MODELS, OUTPUT_DIR


EventCallback = Callable[..., None]
LogCallback = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class ProcessingJob:
    item_id: str
    source_path: Path
    source_key: str
    model_key: str
    move_after: bool = False


def unique_path(folder: Path, filename: str) -> Path:
    path = folder / filename
    if not path.exists():
        return path

    for index in range(1, 100_000):
        candidate = folder / f"{path.stem}_{index}{path.suffix}"
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"Could not create a unique filename for {filename}")


class ImageProcessor:
    """Owns the background worker and keeps loaded rembg sessions cached."""

    def __init__(self, emit: EventCallback, log: LogCallback) -> None:
        self._emit = emit
        self._log = log
        self._jobs: queue.Queue[ProcessingJob | None] = queue.Queue()
        self._accepting_jobs = True
        self._sessions: dict[str, object] = {}
        self._thread = threading.Thread(
            target=self._worker_loop,
            name="removebg-worker",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def submit(self, job: ProcessingJob) -> None:
        if not self._accepting_jobs:
            raise RuntimeError("The image processor is shutting down")
        self._jobs.put(job)

    def close(self, wait_seconds: float = 0.35) -> None:
        self._accepting_jobs = False
        # Cancel jobs that have not started. The active job is allowed a short
        # grace period; the daemon thread remains a final safety net on exit.
        while True:
            try:
                pending = self._jobs.get_nowait()
            except queue.Empty:
                break
            else:
                self._jobs.task_done()
                if pending is None:
                    break
        self._jobs.put_nowait(None)
        if self._thread.is_alive():
            self._thread.join(timeout=wait_seconds)

    def _worker_loop(self) -> None:
        while True:
            try:
                job = self._jobs.get(timeout=0.3)
            except queue.Empty:
                continue

            if job is None:
                self._jobs.task_done()
                break

            try:
                self._run_job(job)
            except Exception as error:
                self._handle_error(job, error)
            finally:
                self._jobs.task_done()

    def _run_job(self, job: ProcessingJob) -> None:
        spec = MODELS[job.model_key]
        session = self._sessions.get(spec.model_name)

        if session is None:
            self._emit("model_loading", job.item_id, spec.key)
            self._log(f"Loading the {spec.title} model ({spec.model_name})…")
            session = new_session(spec.model_name)
            self._sessions[spec.model_name] = session
            self._emit("model_ready", job.item_id, spec.key)
            self._log(f"The {spec.title} model is ready.")

        self._emit("processing", job.item_id, spec.key)
        output_path = self._remove_background(job.source_path, session)

        if job.move_after:
            try:
                destination = unique_path(DONE_DIR, job.source_path.name)
                shutil.move(str(job.source_path), str(destination))
            except Exception:
                # Keep the filesystem transaction consistent: a job is either
                # archived with a final PNG, or routed through the error path.
                try:
                    output_path.unlink(missing_ok=True)
                except OSError:
                    pass
                raise

        self._emit("success", job.item_id, str(output_path), job.source_key)
        self._log(f"Completed: {job.source_path.name} → {output_path.name}")

    @staticmethod
    def _remove_background(source_path: Path, session: object) -> Path:
        output_path = unique_path(OUTPUT_DIR, f"{source_path.stem}.png")
        temp_path = OUTPUT_DIR / f".{uuid.uuid4().hex}.tmp.png"

        try:
            with Image.open(source_path) as source:
                source.load()
                image = ImageOps.exif_transpose(source)
                if image.mode not in ("RGB", "RGBA"):
                    image = image.convert("RGB")

                result = remove(image, session=session)
                result.save(temp_path, format="PNG")

            os.replace(temp_path, output_path)
            return output_path
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    def _handle_error(self, job: ProcessingJob, error: Exception) -> None:
        if job.move_after and job.source_path.exists():
            try:
                destination = unique_path(ERROR_DIR, job.source_path.name)
                shutil.move(str(job.source_path), str(destination))
            except OSError:
                pass

        detail = f"{type(error).__name__}: {error}"
        self._emit("error", job.item_id, detail, job.source_key, job.model_key)
        self._log(f"Error processing {job.source_path.name}: {detail}")
