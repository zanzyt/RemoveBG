from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
DONE_DIR = PROJECT_ROOT / "done"
ERROR_DIR = PROJECT_ROOT / "error"

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}


@dataclass(frozen=True, slots=True)
class ModelSpec:
    key: str
    title: str
    model_name: str
    description: str
    first_run_hint: str


MODELS = {
    "fast": ModelSpec(
        key="fast",
        title="Fast",
        model_name="silueta",
        description="For simple images and fast batch processing.",
        first_run_hint="A compact model that is usually quick to download.",
    ),
    "balanced": ModelSpec(
        key="balanced",
        title="Balanced",
        model_name="u2net",
        description="Clean edge quality with balanced processing speed.",
        first_run_hint="The model will be downloaded on first use.",
    ),
    "maximum": ModelSpec(
        key="maximum",
        title="Maximum",
        model_name="bria-rmbg",
        description="For hair, fur, and complex subject boundaries.",
        first_run_hint="Large model: the first download may take some time (~1 GB).",
    ),
}

def ensure_working_directories() -> None:
    for folder in (INPUT_DIR, OUTPUT_DIR, DONE_DIR, ERROR_DIR):
        folder.mkdir(parents=True, exist_ok=True)
