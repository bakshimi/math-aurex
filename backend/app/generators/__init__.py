"""Pluggable, rule-based question generators.

Each entry in DYNAMIC_GENERATORS maps a category key to a module exposing:
    generate_questions(difficulty: str, count: int, exclude: set) -> list[dict]
    DIFFICULTY_KEYS: list[str]  (which difficulty tiers this generator supports)

Categories without an entry here fall back to the static JSON question bank.
"""
from app.generators import addition

DYNAMIC_GENERATORS = {
    "addition": addition,
}
