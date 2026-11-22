import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Provider:
    """An OpenAI-compatible LLM API the student can pick in the UI."""

    name: str
    base_url: str | None
    models: tuple[str, ...]
    key_placeholder: str
    key_url: str
    # Groq does not document `parallel_tool_calls`, so it is sent only where supported.
    supports_parallel_tool_calls_flag: bool = False


PROVIDERS: dict[str, Provider] = {
    p.name: p
    for p in (
        Provider(
            name="Groq (безкоштовно)",
            base_url="https://api.groq.com/openai/v1",
            models=("openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"),
            key_placeholder="gsk_...",
            key_url="https://console.groq.com/keys",
        ),
        Provider(
            name="OpenAI",
            base_url=None,
            models=("gpt-4o-mini", "gpt-4.1-mini", "gpt-4o"),
            key_placeholder="sk-...",
            key_url="https://platform.openai.com/api-keys",
            supports_parallel_tool_calls_flag=True,
        ),
    )
}
DEFAULT_PROVIDER = next(iter(PROVIDERS.values()))


@dataclass(frozen=True)
class Settings:
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
            temperature=float(os.getenv("EXAMINER_TEMPERATURE", cls.temperature)),
            request_timeout=float(os.getenv("EXAMINER_REQUEST_TIMEOUT", cls.request_timeout)),
            topics_per_exam=int(os.getenv("EXAMINER_TOPICS_PER_EXAM", cls.topics_per_exam)),
            response_language=os.getenv("EXAMINER_RESPONSE_LANGUAGE", cls.response_language),
            results_dir=Path(os.getenv("EXAMINER_RESULTS_DIR", cls.results_dir)),
        )
