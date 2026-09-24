"""Rule-based dynamic addition question generator for Grade 3.

Each "rule" below encodes a pedagogical pattern (digit ranges + regrouping
constraints) as a small operand generator. Questions are assembled on demand
(no static question bank), so the pool of possible problems is effectively
unlimited - there's no fixed-size bucket to exhaust, and "Try Again" simply
generates a fresh random problem every time.
"""
import random
from typing import List, Optional, Tuple

HINT = "Try adding the tens first, then the ones."


def _digits_lsb_first(n: int) -> List[int]:
    return [int(c) for c in reversed(str(n))]


def _fmt(n: int) -> str:
    return f"{n:,}"


def sum_with_carries(*nums: int) -> Tuple[int, List[int]]:
    """Adds any number of positive integers, returning (result, place-indices that carried)."""
    digit_lists = [_digits_lsb_first(n) for n in nums]
    width = max(len(d) for d in digit_lists)
    for d in digit_lists:
        d.extend([0] * (width - len(d)))

    carry = 0
    carried_places: List[int] = []
    result_digits: List[int] = []
    for i in range(width):
        total = sum(d[i] for d in digit_lists) + carry
        result_digits.append(total % 10)
        carry = total // 10
        if carry:
            carried_places.append(i)
    while carry:
        result_digits.append(carry % 10)
        carry //= 10

    result = int("".join(str(d) for d in reversed(result_digits)))
    return result, carried_places


def _no_carry_sum(*nums: int) -> int:
    """Simulates the common student mistake of adding each column but forgetting to carry."""
    digit_lists = [_digits_lsb_first(n) for n in nums]
    width = max(len(d) for d in digit_lists)
    for d in digit_lists:
        d.extend([0] * (width - len(d)))
    result_digits = [sum(d[i] for d in digit_lists) % 10 for i in range(width)]
    return int("".join(str(d) for d in reversed(result_digits)))


def _transpose_digits(n: int) -> Optional[int]:
    """Swaps two adjacent digits - models a common written/typing slip."""
    s = list(str(n))
    if len(s) < 2:
        return None
    i = random.randrange(len(s) - 1)
    s[i], s[i + 1] = s[i + 1], s[i]
    if s[0] == "0":
        return None
    return int("".join(s))


def _build_options(correct: int, *operands: int) -> Tuple[List[str], int]:
    candidates: List[int] = []

    no_carry = _no_carry_sum(*operands)
    if no_carry != correct:
        candidates.append(no_carry)

    for delta in (10, -10, 1, -1, 11, -11, 100, -100):
        v = correct + delta
        if v > 0:
            candidates.append(v)

    transposed = _transpose_digits(correct)
    if transposed:
        candidates.append(transposed)

    random.shuffle(candidates)
    distractors: List[int] = []
    seen = {correct}
    for c in candidates:
        if c not in seen:
            distractors.append(c)
            seen.add(c)
        if len(distractors) == 3:
            break

    # Fallback (extremely rare): fill any remaining slots with random nearby offsets.
    fallback_deltas = [-25, -20, -15, -5, 5, 15, 20, 25]
    random.shuffle(fallback_deltas)
    for delta in fallback_deltas:
        if len(distractors) == 3:
            break
        v = correct + delta
        if v > 0 and v not in seen:
            distractors.append(v)
            seen.add(v)

    values = [correct] + distractors
    random.shuffle(values)
    answer_index = values.index(correct)
    return [_fmt(v) for v in values], answer_index


def _make_question(rule_id: str, *operands: int) -> dict:
    correct, _ = sum_with_carries(*operands)
    options, answer_index = _build_options(correct, *operands)
    question_text = "What is " + " + ".join(_fmt(n) for n in operands) + "?"
    signature = f"{rule_id}:" + "+".join(str(n) for n in operands)
    return {
        "id": f"gen_add_{signature}",
        "topic": "addition",
        "question": question_text,
        "options": options,
        "answer_index": answer_index,
    }


# --- Rule operand generators ------------------------------------------------

def _rule_two_digit_no_regroup() -> Tuple[int, int]:
    for _ in range(200):
        a = random.randint(10, 99)
        b = random.randint(10, 99)
        if (a % 10 + b % 10 < 10) and (a // 10 + b // 10 < 10):
            return a, b
    return 10, 10  # unreachable in practice; safe deterministic fallback


def _rule_two_digit_with_regroup() -> Tuple[int, int]:
    for _ in range(200):
        a = random.randint(10, 99)
        b = random.randint(10, 99)
        if (a % 10 + b % 10) >= 10:
            return a, b
    return 19, 19


def _rule_three_two_digit() -> Tuple[int, int]:
    return random.randint(100, 999), random.randint(10, 99)


def _rule_three_three_light() -> Tuple[int, int]:
    for _ in range(200):
        a = random.randint(100, 500)
        b = random.randint(100, 500)
        _, carries = sum_with_carries(a, b)
        if carries:
            return a, b
    return 199, 199


def _rule_three_three_heavy() -> Tuple[int, int]:
    fallback = None
    for _ in range(200):
        a = random.randint(300, 999)
        b = random.randint(300, 999)
        _, carries = sum_with_carries(a, b)
        if len(carries) >= 2:
            return a, b
        if carries and fallback is None:
            fallback = (a, b)
    if fallback:
        return fallback
    return 399, 399


def _rule_four_three_digit() -> Tuple[int, int]:
    return random.randint(1000, 9999), random.randint(100, 999)


def _rule_four_four_digit() -> Tuple[int, int]:
    for _ in range(200):
        a = random.randint(1000, 9999)
        b = random.randint(1000, 9999)
        _, carries = sum_with_carries(a, b)
        if carries:
            return a, b
    return 1999, 1999


def _rule_multi_step() -> Tuple[int, int, int]:
    return random.randint(100, 999), random.randint(100, 999), random.randint(100, 999)


_RULES = {
    "two_digit_no_regroup": _rule_two_digit_no_regroup,
    "two_digit_with_regroup": _rule_two_digit_with_regroup,
    "three_two_digit": _rule_three_two_digit,
    "three_three_light": _rule_three_three_light,
    "three_three_heavy": _rule_three_three_heavy,
    "four_three_digit": _rule_four_three_digit,
    "four_four_digit": _rule_four_four_digit,
    "multi_step": _rule_multi_step,
}

# Maps the app's existing Easy/Medium/Hard tiers onto the rule set above.
RULES_BY_DIFFICULTY = {
    "easy": ["two_digit_no_regroup", "two_digit_with_regroup"],
    "medium": ["three_two_digit", "three_three_light"],
    "hard": ["three_three_heavy", "four_three_digit", "four_four_digit", "multi_step"],
}

DIFFICULTY_KEYS = list(RULES_BY_DIFFICULTY.keys())


def _generate_one(difficulty: str) -> dict:
    rule_ids = RULES_BY_DIFFICULTY.get(difficulty)
    if not rule_ids:
        raise ValueError(f"No addition rules defined for difficulty '{difficulty}'.")
    rule_id = random.choice(rule_ids)
    operands = _RULES[rule_id]()
    q = _make_question(rule_id, *operands)
    q["difficulty"] = difficulty
    return q


def generate_questions(difficulty: str, count: int, exclude: Optional[set] = None) -> List[dict]:
    """Generates `count` fresh, mutually-unique addition questions for the given tier."""
    exclude = set(exclude or [])
    results: List[dict] = []
    for _ in range(count):
        q = None
        for _attempt in range(50):
            candidate = _generate_one(difficulty)
            if candidate["id"] not in exclude:
                q = candidate
                break
        if q is None:
            q = candidate  # accept a rare collision rather than looping forever
        exclude.add(q["id"])
        results.append(q)
    return results
