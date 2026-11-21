import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    request_timeout: float = 60.0
    topics_per_exam: int = 3
    max_tool_rounds: int = 8
    response_language: str = "Ukrainian"
    data_path: Path = BASE_DIR / "data" / "subjects.json"
    results_dir: Path = BASE_DIR / "results"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model=os.getenv("EXAMINER_MODEL", cls.model),
            temperature=float(os.getenv("EXAMINER_TEMPERATURE", cls.temperature)),
            request_timeout=float(os.getenv("EXAMINER_REQUEST_TIMEOUT", cls.request_timeout)),
            topics_per_exam=int(os.getenv("EXAMINER_TOPICS_PER_EXAM", cls.topics_per_exam)),
            response_language=os.getenv("EXAMINER_RESPONSE_LANGUAGE", cls.response_language),
            results_dir=Path(os.getenv("EXAMINER_RESULTS_DIR", cls.results_dir)),
        )
