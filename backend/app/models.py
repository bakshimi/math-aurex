"""Pydantic request/response models for the Math Education quiz API."""
import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


class RegisterRequest(BaseModel):
    username: str = Field(..., description="3-32 characters: letters, numbers, underscore")
    password: str = Field(..., min_length=8, max_length=128)
    display_name: Optional[str] = Field(None, description="Friendly name shown in the app; defaults to username")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not _USERNAME_RE.match(v):
            raise ValueError("Username must be 3-32 characters: letters, numbers, or underscore only.")
        return v


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class StartSessionRequest(BaseModel):
    grade: int = Field(..., description="Student grade level, e.g. 3")
    category: str = Field(..., description="Question category, e.g. 'addition'")
    difficulty: str = Field(..., description="Difficulty tier: 'easy', 'medium', or 'hard'")


class CategoryOut(BaseModel):
    key: str
    label: str
    count: int


class CategoriesResponse(BaseModel):
    categories: List[CategoryOut]


class DifficultyOut(BaseModel):
    key: str
    label: str
    count: int


class DifficultiesResponse(BaseModel):
    difficulties: List[DifficultyOut]


class QuestionOut(BaseModel):
    question_id: str
    index: int  # 1-based position of this question within the session
    total: int  # total number of questions in the session
    topic: str
    question: str
    options: List[str]
    attempts_left: int


class StartSessionResponse(BaseModel):
    session_id: str
    grade: int
    category: str
    difficulty: str
    total_questions: int
    question: QuestionOut


class AnswerRequest(BaseModel):
    selected_index: int = Field(..., ge=0, le=3)


class AnswerResponse(BaseModel):
    correct: bool
    attempts_left: int
    correct_answer_index: Optional[int] = None
    finished: bool
    score: int
    total: int
    next_question: Optional[QuestionOut] = None
    timed_out: bool = False
    explanation: Optional[List[str]] = None


class HintResponse(BaseModel):
    hint: str
