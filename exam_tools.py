"""Agent tools: plain Python functions bound to one exam session + their JSON schemas for the LLM."""

import json
import random
from datetime import datetime
from statistics import mean
from typing import Any, Literal, TypedDict

from config import Settings
from question_bank import QuestionBank, Subject, Topic, normalize
from storage import ResultStore


class Message(TypedDict):
    role: Literal["system", "user", "assistant", "tool_call"]
    content: str
    datetime: str


class ToolError(Exception):
    """An error the model should see and react to (e.g. ask the student again)."""


def to_nmt_score(topic_scores: list[float]) -> int:
    """Trivial linear mapping of the mean topic score 0..10 to the NMT scale 100..200."""
    return round(100 + 10 * mean(topic_scores))


class ExamSession:
    """State of one student's exam and the tools the agent can call."""

    def __init__(
        self,
        bank: QuestionBank,
        store: ResultStore,
        settings: Settings,
        rng: random.Random | None = None,
    ) -> None:
        self._bank = bank
        self._store = store
        self._settings = settings
        self._rng = rng or random.Random()
        self.history: list[Message] = []
        self._reset_exam()

    def _reset_exam(self) -> None:
        self.name: str | None = None
        self.subject: Subject | None = None
        self.topics: list[Topic] = []
        self._topic_idx = -1
        self._asked: set[str] = set()
        self.in_progress = False

    def log(self, role: str, content: str) -> None:
        self.history.append(
            {"role": role, "content": content, "datetime": datetime.now().isoformat(timespec="seconds")}
        )

    #tools 

    def list_subjects(self) -> list[str]:
        return self._bank.subject_names

    def start_exam(self, name: str, subject: str) -> list[str]:
        if self.in_progress:
            raise ToolError("An exam is already in progress. Finish it with end_exam before starting a new one.")
        name = name.strip()
        if not name:
            raise ToolError("Empty name. Ask the student for their name.")
        found = self._bank.subject(subject)
        if found is None:
            raise ToolError(
                f"Subject '{subject}' not found. Available subjects: {', '.join(self._bank.subject_names)}. "
                "Ask the student which one they choose."
            )
        self._reset_exam()
        k = min(self._settings.topics_per_exam, len(found.topics))
        self.name, self.subject = name, found
        self.topics = self._rng.sample(list(found.topics), k)
        self.in_progress = True
        return [t.name for t in self.topics]

    def get_next_topic(self) -> str:
        self._require_exam()
        if self._topic_idx + 1 >= len(self.topics):
            raise ToolError("No topics left. Call end_exam with grades for all topics.")
        self._topic_idx += 1
        return self.topics[self._topic_idx].name

    def get_question(self, topic: str) -> dict[str, Any]:
        current = self._current_topic()
        if normalize(current.name) != normalize(topic):
            raise ToolError(f"The current topic is '{current.name}'. Take questions from it.")
        remaining = [q for q in current.questions if q.id not in self._asked]
        if not remaining:
            raise ToolError("No questions left in this topic. Grade the topic and call get_next_topic.")
        question = self._rng.choice(remaining)
        self._asked.add(question.id)
        return {
            "topic": current.name,
            "question": question.text,
            "reference_answer": question.answer,
            "questions_left_in_topic": len(remaining) - 1,
        }

    def get_weak_topics(self) -> dict[str, Any]:
        self._require_exam()
        records = self._store.load(self.name, self.subject.name)
        per_topic: dict[str, list[float]] = {}
        for record in records:
            for item in record.get("topic_scores", []):
                if item.get("skipped"):
                    continue
                per_topic.setdefault(item["topic"], []).append(float(item["score"]))
        ranked = sorted(
            ({"topic": t, "avg_score": round(mean(s), 1), "times": len(s)} for t, s in per_topic.items()),
            key=lambda x: x["avg_score"],
        )
        return {
            "previous_attempts": len(records),
            "previous_nmt_scores": [r["nmt_score"] for r in records],
            "topics_from_weakest": ranked,
        }

    def end_exam(self, topic_scores: list[dict[str, Any]], feedback: str) -> dict[str, Any]:
        self._require_exam()
        if self._topic_idx + 1 < len(self.topics):
            left = [t.name for t in self.topics[self._topic_idx + 1:]]
            raise ToolError(f"Topics not covered yet: {', '.join(left)}. Go through them first.")
        return self._finish(topic_scores, feedback, completed=True)

    def quit_exam(self, topic_scores: list[dict[str, Any]], feedback: str) -> dict[str, Any]:
        self._require_exam()
        return self._finish(topic_scores, feedback, completed=False)

    def _finish(self, topic_scores: list[dict[str, Any]], feedback: str, completed: bool) -> dict[str, Any]:
        """Grades discussed topics from topic_scores; topics never reached get 0 and are marked skipped."""
        scores_by_topic = {normalize(str(item.get("topic", ""))): item.get("score") for item in topic_scores}
        cleaned = []
        for idx, topic in enumerate(self.topics):
            if idx > self._topic_idx:
                cleaned.append({"topic": topic.name, "score": 0.0, "skipped": True})
                continue
            score = scores_by_topic.get(normalize(topic.name))
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 10:
                raise ToolError(f"A grade from 0..10 is required for topic '{topic.name}'.")
            cleaned.append({"topic": topic.name, "score": float(score)})

        nmt = to_nmt_score([c["score"] for c in cleaned])
        self._save_result(nmt, cleaned, feedback, completed)
        self.in_progress = False
        return {"nmt_score": nmt, "scale": "100..200", "completed": completed, "topic_scores": cleaned}

    def _save_result(
        self, nmt_score: int, topic_scores: list[dict[str, Any]], feedback: str, completed: bool
    ) -> None:
        """Analogue of end_exam(email, score, history) from the assignment: writes the result to a file."""
        self._store.save({
            "name": self.name,
            "subject": self.subject.name,
            "nmt_score": nmt_score,
            "topic_scores": topic_scores,
            "feedback": feedback,
            "completed": completed,
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "history": self.history,
        })

    #helpers

    def _require_exam(self) -> None:
        if not self.in_progress:
            raise ToolError("The exam has not started yet. Call start_exam(name, subject) first.")

    def _current_topic(self) -> Topic:
        self._require_exam()
        if self._topic_idx < 0:
            raise ToolError("No topic selected yet. Call get_next_topic first.")
        return self.topics[self._topic_idx]

    #dispatcher

    def call(self, tool_name: str, arguments_json: str) -> str:
        """Runs a tool requested by the model and returns the result as a JSON string."""
        try:
            args = json.loads(arguments_json or "{}")
            func = getattr(self, tool_name) if tool_name in TOOL_NAMES else None
            if func is None:
                raise ToolError(f"Unknown tool: {tool_name}")
            result: Any = {"result": func(**args)}
        except ToolError as e:
            result = {"error": str(e)}
        except (TypeError, json.JSONDecodeError) as e:
            result = {"error": f"Invalid arguments for {tool_name}: {e}"}

        output = json.dumps(result, ensure_ascii=False)
        self.log("tool_call", json.dumps({"name": tool_name, "arguments": arguments_json, "result": result},
                                         ensure_ascii=False))
        return output


def _function(name: str, description: str, properties: dict | None = None, required: list[str] | None = None):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


def _topic_scores_schema(description: str) -> dict:
    return {
        "type": "array",
        "description": description,
        "items": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic name"},
                "score": {"type": "number", "description": "Grade from 0 to 10"},
            },
            "required": ["topic", "score"],
            "additionalProperties": False,
        },
    }


_FEEDBACK_SCHEMA = {
    "type": "string",
    "description": "What went well and what to work on, written in the language you reply to the student in",
}


TOOLS = [
    _function(
        "list_subjects",
        "Returns the list of NMT subjects available for practice.",
    ),
    _function(
        "start_exam",
        "Starts the exam once the student's name and subject are known. Returns the list of exam topics. "
        "If the subject is not found, returns an error — then clarify the subject with the student.",
        {
            "name": {"type": "string", "description": "Student's name"},
            "subject": {"type": "string", "description": "Subject name from the list_subjects list"},
        },
        ["name", "subject"],
    ),
    _function(
        "get_weak_topics",
        "Returns this student's previous practice results in this subject: NMT scores and topics from weakest. "
        "Call it right after start_exam.",
    ),
    _function(
        "get_next_topic",
        "Moves to the next exam topic and returns its name. "
        "When there are no topics left, returns an error — then call end_exam.",
    ),
    _function(
        "get_question",
        "Returns a random not-yet-asked question from the current topic and its reference answer. "
        "Do not show the reference answer to the student before they answer.",
        {"topic": {"type": "string", "description": "Name of the current topic (from get_next_topic)"}},
        ["topic"],
    ),
    _function(
        "end_exam",
        "Finishes the exam: takes a 0..10 grade for each topic and short feedback, saves the result "
        "and returns the score on the NMT scale (100..200).",
        {
            "topic_scores": _topic_scores_schema("Grade for each exam topic"),
            "feedback": _FEEDBACK_SCHEMA,
        },
        ["topic_scores", "feedback"],
    ),
    _function(
        "quit_exam",
        "Ends the exam early when the student does not want to continue. Takes grades only for the topics "
        "already discussed (including the current one; give 0 if its question went unanswered); topics not "
        "reached yet are graded 0 automatically. Saves the result and returns the score on the NMT scale (100..200).",
        {
            "topic_scores": _topic_scores_schema("Grade for each topic discussed so far"),
            "feedback": _FEEDBACK_SCHEMA,
        },
        ["topic_scores", "feedback"],
    ),
]

TOOL_NAMES = {t["function"]["name"] for t in TOOLS}
