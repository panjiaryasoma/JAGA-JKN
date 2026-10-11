"""Process-owned paths. HTTP requests cannot choose a dataset or a file path."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_root: Path = ROOT / "data/synthetic/curated"
    manifest_path: Path = ROOT / "config/backend_dataset_manifest.json"
    database_path: Path = ROOT / "var/jaga-jkn.sqlite3"
    experimental_ml_enabled: bool = False
    ml_model_path: Path = ROOT / "models/best_model.pkl"
    reviewer_token: str | None = field(default=None, repr=False)
    supervisor_token: str | None = field(default=None, repr=False)
    reviewer_id: str = "demo-reviewer"
    supervisor_id: str = "demo-supervisor"

    def __post_init__(self):
        if type(self.experimental_ml_enabled) is not bool:
            raise ValueError("Experimental ML opt-in must be a boolean")
        tokens = [
            token for token in (self.reviewer_token, self.supervisor_token) if token is not None
        ]
        if any(not re.fullmatch(r"[!-~]{32,256}", token) for token in tokens):
            raise ValueError("Demo tokens must contain 32 to 256 non-whitespace ASCII characters")
        if len(tokens) != len(set(tokens)):
            raise ValueError("Demo tokens must be distinct")
        if any(
            not re.fullmatch(r"[a-z][a-z0-9_-]{2,63}", name)
            for name in (self.reviewer_id, self.supervisor_id)
        ):
            raise ValueError("Invalid demo actor identifier")
        if len(tokens) == 2 and self.reviewer_id == self.supervisor_id:
            raise ValueError("Demo actor identifiers must be distinct")

    @classmethod
    def from_environment(cls) -> "Settings":
        defaults = cls()
        experimental = os.environ.get("JAGA_EXPERIMENTAL_ML_ENABLED", "0")
        if experimental not in {"0", "1"}:
            raise ValueError("JAGA_EXPERIMENTAL_ML_ENABLED accepts only 0 or 1")
        return cls(
            data_root=Path(os.environ.get("JAGA_DATA_ROOT", defaults.data_root)),
            manifest_path=Path(os.environ.get("JAGA_DATASET_MANIFEST", defaults.manifest_path)),
            database_path=Path(os.environ.get("JAGA_DB_PATH", defaults.database_path)),
            experimental_ml_enabled=experimental == "1",
            reviewer_token=os.environ.get("JAGA_REVIEWER_TOKEN"),
            supervisor_token=os.environ.get("JAGA_SUPERVISOR_TOKEN"),
            reviewer_id=os.environ.get("JAGA_REVIEWER_ID", defaults.reviewer_id),
            supervisor_id=os.environ.get("JAGA_SUPERVISOR_ID", defaults.supervisor_id),
        )
