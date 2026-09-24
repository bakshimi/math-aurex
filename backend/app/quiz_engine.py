"""In-memory quiz session engine.

Loads the question bank per grade, deals out a shuffled, non-repeating set of
questions per session, and tracks attempts (max 3) per question.
"""
import json
import random
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from app.models import QuestionOut
from app import explanations
from app.generators import DYNAMIC_GENERATORS

QUESTIONS_DIR = Path(__file__).parent / "questions"

# Pilot supports grade 3 only; add more files here as new grades are authored.
GRADE_QUESTION_FILES = {
    3: "grade3.json",
}

# Deliberately set to exactly half of each category/difficulty bucket's size (12
# questions). That means every "Try Again" on the same bucket draws the OTHER
# half - guaranteed zero overlap with the previous attempt - before a full
# reshuffle starts a new cycle. A session length close to the bucket size (e.g.
# 10 of 12) would leave almost no fresh questions for the very next attempt.
QUESTIONS_PER_SESSION = 6
MAX_ATTEMPTS = 3

# The eight sub-categories offered once a grade is picked. Keyed by the
# question bank's "topic" field.
CATEGORY_LABELS = {
    "algebra": "Algebra",
    "addition": "Addition",
    "multiplication": "Multiplication",
    "division": "Division",
    "trigonometry": "Trigonometry",
    "word_problem": "Word Problems",
    "patterns": "Patterns",
    "fractions": "Fractions",
}
CATEGORY_ORDER = list(CATEGORY_LABELS.keys())

DIFFICULTY_LABELS = {
    "easy": "Easy",
    "medium": "Medium",
    "hard": "Hard",
}
DIFFICULTY_ORDER = list(DIFFICULTY_LABELS.keys())

_question_bank_cache: Dict[int, List[dict]] = {}

# Question IDs already served to a given (student_id, grade, category, difficulty)
# combo, so clicking "Try Again" serves fresh questions instead of repeats.
_seen_questions: Dict[tuple, set] = {}

# Caps how many past question ids we remember per (student, grade, category,
# difficulty) bucket, so long play sessions don't grow this unbounded.
_MAX_SEEN_HISTORY = 300


def _load_question_bank(grade: int) -> List[dict]:
    if grade not in GRADE_QUESTION_FILES:
        raise ValueError(f"Unsupported grade: {grade}")
    if grade not in _question_bank_cache:
        path = QUESTIONS_DIR / GRADE_QUESTION_FILES[grade]
        with open(path, "r", encoding="utf-8") as f:
            _question_bank_cache[grade] = json.load(f)
    return _question_bank_cache[grade]


def get_categories(grade: int) -> List[dict]:
    bank = _load_question_bank(grade)
    counts: Dict[str, int] = {}
    for q in bank:
        counts[q["topic"]] = counts.get(q["topic"], 0) + 1
    return [
        {
            "key": key,
            "label": CATEGORY_LABELS[key],
            # Dynamically-generated categories have no fixed pool size, so report a
            # large representative count rather than the (irrelevant) static bank size.
            "count": 999 if key in DYNAMIC_GENERATORS else counts.get(key, 0),
        }
        for key in CATEGORY_ORDER
    ]


def get_difficulties(grade: int, category: str) -> List[dict]:
    if category in DYNAMIC_GENERATORS:
        supported = set(DYNAMIC_GENERATORS[category].DIFFICULTY_KEYS)
        return [
            {"key": key, "label": DIFFICULTY_LABELS[key], "count": 999 if key in supported else 0}
            for key in DIFFICULTY_ORDER
        ]

    bank = [q for q in _load_question_bank(grade) if q["topic"] == category]
    counts: Dict[str, int] = {}
    for q in bank:
        counts[q.get("difficulty", "medium")] = counts.get(q.get("difficulty", "medium"), 0) + 1
    return [
        {"key": key, "label": DIFFICULTY_LABELS[key], "count": counts.get(key, 0)}
        for key in DIFFICULTY_ORDER
    ]


def _select_questions(grade: int, category: str, difficulty: str, student_id: Optional[str]) -> List[dict]:
    if category in DYNAMIC_GENERATORS:
        return _select_generated_questions(category, difficulty, student_id)

    bank = [
        q
        for q in _load_question_bank(grade)
        if q["topic"] == category and q.get("difficulty", "medium") == difficulty
    ]
    if not bank:
        raise ValueError(f"No questions available for grade {grade}, category '{category}', difficulty '{difficulty}'.")

    sample_size = min(QUESTIONS_PER_SESSION, len(bank))

    if not student_id:
        return random.sample(bank, sample_size)

    key = (student_id, grade, category, difficulty)
    seen = _seen_questions.setdefault(key, set())
    unseen = [q for q in bank if q["id"] not in seen]
    already_seen = [q for q in bank if q["id"] in seen]

    # Always prefer questions this student hasn't seen yet for this category/difficulty.
    random.shuffle(unseen)
    selected = unseen[:sample_size]

    if len(selected) < sample_size:
        # Not enough fresh questions left in the pool: top up with repeats, then
        # start a new cycle so future attempts prioritize what's freshest again.
        needed = sample_size - len(selected)
        selected += random.sample(already_seen, min(needed, len(already_seen)))
        seen.clear()

    seen.update(q["id"] for q in selected)
    random.shuffle(selected)
    return selected


def _select_generated_questions(category: str, difficulty: str, student_id: Optional[str]) -> List[dict]:
    """Procedurally generates a fresh, mutually-unique question set (no static bank)."""
    generator = DYNAMIC_GENERATORS[category]
    if difficulty not in generator.DIFFICULTY_KEYS:
        raise ValueError(f"No '{category}' rules defined for difficulty '{difficulty}'.")

    if not student_id:
        return generator.generate_questions(difficulty, QUESTIONS_PER_SESSION)

    key = (student_id, 0, category, difficulty)
    seen = _seen_questions.setdefault(key, set())
    selected = generator.generate_questions(difficulty, QUESTIONS_PER_SESSION, exclude=seen)
    seen.update(q["id"] for q in selected)
    if len(seen) > _MAX_SEEN_HISTORY:
        # Drop the oldest entries so this doesn't grow forever across a long play session.
        trimmed = list(seen)[-_MAX_SEEN_HISTORY:]
        seen.clear()
        seen.update(trimmed)
    return selected


class QuizSession:
    def __init__(self, grade: int, category: str, difficulty: str, questions: List[dict]):
        self.grade = grade
        self.category = category
        self.difficulty = difficulty
        self.questions = questions  # already sampled without repeats by _select_questions
        self.total = len(questions)
        self.current_index = 0
        self.attempts_used = 0
        self.score = 0
        self.finished = False

    @property
    def current_question(self) -> dict:
        return self.questions[self.current_index]

    def current_question_out(self) -> QuestionOut:
        q = self.current_question
        return QuestionOut(
            question_id=q["id"],
            index=self.current_index + 1,
            total=self.total,
            topic=q["topic"],
            question=q["question"],
            options=q["options"],
            attempts_left=MAX_ATTEMPTS - self.attempts_used,
        )

    def submit_answer(self, selected_index: int):
        q = self.current_question
        is_correct = selected_index == q["answer_index"]
        correct_answer_index: Optional[int] = None
        next_question: Optional[QuestionOut] = None
        explanation: Optional[List[str]] = None

        if is_correct:
            self.score += 1
            correct_answer_index = q["answer_index"]
            attempts_left = 0
            self._advance()
        else:
            self.attempts_used += 1
            attempts_left = MAX_ATTEMPTS - self.attempts_used
            if attempts_left <= 0:
                # out of attempts: reveal the answer, teach the steps, and move on
                correct_answer_index = q["answer_index"]
                explanation = explanations.build_explanation(q)["steps"]
                self._advance()
            # else: stay on the same question for another attempt

        if not self.finished and (is_correct or attempts_left <= 0):
            next_question = self.current_question_out()

        return {
            "correct": is_correct,
            "attempts_left": max(attempts_left, 0),
            "correct_answer_index": correct_answer_index,
            "finished": self.finished,
            "score": self.score,
            "total": self.total,
            "next_question": next_question,
            "explanation": explanation,
        }

    def handle_timeout(self):
        """Called when the 15-second per-question timer runs out with no answer submitted."""
        q = self.current_question
        correct_answer_index = q["answer_index"]
        explanation = explanations.build_explanation(q)["steps"]
        self._advance()
        next_question = self.current_question_out() if not self.finished else None

        return {
            "correct": False,
            "attempts_left": 0,
            "correct_answer_index": correct_answer_index,
            "finished": self.finished,
            "score": self.score,
            "total": self.total,
            "next_question": next_question,
            "timed_out": True,
            "explanation": explanation,
        }

    def get_hint(self) -> str:
        """A lighter-weight nudge shown on demand; doesn't consume an attempt or reveal the answer."""
        return explanations.build_hint(self.current_question)

    def _advance(self):
        self.attempts_used = 0
        self.current_index += 1
        if self.current_index >= self.total:
            self.finished = True


_sessions: Dict[str, QuizSession] = {}


def create_session(grade: int, category: str, difficulty: str, student_id: Optional[str] = None) -> tuple[str, QuizSession]:
    questions = _select_questions(grade, category, difficulty, student_id)
    session_id = str(uuid.uuid4())
    session = QuizSession(grade, category, difficulty, questions)
    _sessions[session_id] = session
    return session_id, session


def get_session(session_id: str) -> Optional[QuizSession]:
    return _sessions.get(session_id)


def end_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
