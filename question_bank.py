import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    answer: str


@dataclass(frozen=True)
class Topic:
    name: str
    questions: tuple[Question, ...]


@dataclass(frozen=True)
class Subject:
    name: str
    topics: tuple[Topic, ...]

    def topic(self, name: str) -> Topic | None:
        key = _normalize(name)
        return next((t for t in self.topics if _normalize(t.name) == key), None)


class QuestionBank:
    """Subjects -> topics -> questions with reference answers, loaded from a JSON file."""

    def __init__(self, subjects: list[Subject]) -> None:
        self._subjects = {_normalize(s.name): s for s in subjects}

    @classmethod
    def from_file(cls, path: Path) -> "QuestionBank":
        raw = json.loads(path.read_text(encoding="utf-8"))
        subjects = []
        for s_idx, s in enumerate(raw["subjects"], start=1):
            topics = []
            for t_idx, t in enumerate(s["topics"], start=1):
                questions = tuple(
                    Question(id=f"{s_idx}.{t_idx}.{q_idx}", text=q["question"], answer=q["answer"])
                    for q_idx, q in enumerate(t["questions"], start=1)
                )
                topics.append(Topic(name=t["name"], questions=questions))
            subjects.append(Subject(name=s["name"], topics=tuple(topics)))
        return cls(subjects)

    @property
    def subject_names(self) -> list[str]:
        return [s.name for s in self._subjects.values()]

    def subject(self, name: str) -> Subject | None:
        return self._subjects.get(_normalize(name))


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace("’", "'").split())
