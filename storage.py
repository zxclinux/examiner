import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


class ResultStore:
    """Stores exam results as JSON files: one file per finished exam."""

    def __init__(self, results_dir: Path) -> None:
        self._dir = results_dir

    def save(self, record: dict[str, Any]) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = self._dir / f"{stamp}_{_slug(record['name'])}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, name: str, subject: str) -> list[dict[str, Any]]:
        if not self._dir.exists():
            return []
        records = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if _slug(record.get("name", "")) == _slug(name) and record.get("subject") == subject:
                records.append(record)
        return records


def _slug(text: str) -> str:
    return re.sub(r"[^\w]+", "_", text.strip().lower()).strip("_") or "student"
