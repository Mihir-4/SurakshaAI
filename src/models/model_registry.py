"""Model artifact registry helpers for SurakshaAI."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.config import settings


# Project root:
# D:\Data Vidwan\Final Capstone Project\surakshaai
ROOT_DIR = Path(__file__).resolve().parents[2]


def portable_path(value: str | Path | None) -> str | None:
    """Convert an artifact path to a portable project-relative POSIX path."""
    if value is None:
        return None

    path = Path(value)

    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except ValueError:
        # If the path is already relative, preserve it in POSIX form.
        return path.as_posix()


@dataclass
class ModelCard:
    model_name: str
    model_type: str
    version: str
    artifact_path: str
    metrics: Dict[str, Any]
    hyperparameters: Dict[str, Any]
    dataset_version: str = "v1"
    feature_version: str = "v1"
    training_seed: int = settings.RANDOM_SEED
    calibration_method: str = "none"
    decision_threshold: float = 0.5
    trained_at: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)

        # Store a portable path instead of a machine-specific
        # absolute Windows path.
        data["artifact_path"] = portable_path(self.artifact_path)

        data["trained_at"] = (
            self.trained_at
            or datetime.now(timezone.utc).isoformat()
        )

        return data


class ArtifactRegistry:
    """Writes lightweight JSON model cards next to saved model artifacts."""

    def __init__(self, registry_path: Optional[Path] = None) -> None:
        self.registry_path = registry_path or (settings.model_dir / "registry.json")
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[dict]:
        if not self.registry_path.exists():
            return []

        return json.loads(
            self.registry_path.read_text(encoding="utf-8")
        )

    def register(self, card: ModelCard) -> dict:
        entries = self.load()
        record = card.to_dict()

        entries = [
            e
            for e in entries
            if not (
                e.get("model_name") == card.model_name
                and e.get("version") == card.version
            )
        ]

        entries.append(record)

        self.registry_path.write_text(
            json.dumps(entries, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        return record

    def latest(self, model_type: Optional[str] = None) -> Optional[dict]:
        entries = self.load()

        if model_type:
            entries = [
                e
                for e in entries
                if e.get("model_type") == model_type
            ]

        if not entries:
            return None

        return sorted(
            entries,
            key=lambda e: e.get("trained_at", ""),
        )[-1]