import time
from dataclasses import dataclass
from pathlib import Path

from .config import INPUT_DIR, SUPPORTED_EXTENSIONS


@dataclass(slots=True)
class _ObservedFile:
    signature: tuple[int, int]
    unchanged_since: float


class InputFolderWatcher:
    """Detect files that have stopped changing in the monitored input folder."""

    def __init__(self, folder: Path = INPUT_DIR, stability_seconds: float = 1.0) -> None:
        self.folder = folder
        self.stability_seconds = stability_seconds
        self._observed: dict[str, _ObservedFile] = {}

    def scan(self, ignored: set[str] | None = None) -> list[Path]:
        ignored = ignored or set()
        now = time.monotonic()
        present: set[str] = set()
        ready: list[Path] = []

        try:
            files = (
                path
                for path in self.folder.iterdir()
                if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
            )
            for path in files:
                try:
                    key = str(path.resolve())
                    present.add(key)
                    if key in ignored:
                        continue

                    stat = path.stat()
                    signature = (stat.st_size, stat.st_mtime_ns)
                    observed = self._observed.get(key)
                    if observed is None or observed.signature != signature:
                        self._observed[key] = _ObservedFile(signature, now)
                        continue

                    if now - observed.unchanged_since >= self.stability_seconds:
                        ready.append(path)
                        self._observed.pop(key, None)
                except OSError:
                    continue
        except OSError:
            return ready

        for key in tuple(self._observed):
            if key not in present:
                self._observed.pop(key, None)
        return ready

    def reset(self) -> None:
        self._observed.clear()
