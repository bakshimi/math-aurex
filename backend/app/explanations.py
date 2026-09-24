"""Generates kid-friendly hints and step-by-step solution explanations for questions.

Uses lightweight regex parsing of the question text for the formulaic categories
(addition, multiplication, division, algebra, patterns, some trigonometry) so the
explanation shows real worked-out steps. Falls back to a generic, still-helpful
explanation for anything that can't be safely parsed (never guesses a rule that
doesn't actually match the recorded correct answer).
"""
import re
from math import gcd
from typing import Callable, Dict, List, Optional


def _clean_num(text: str) -> int:
    return int(text.replace(",", "").strip())


def _fmt(n: int) -> str:
    return f"{n:,}"


HINTS: Dict[str, str] = {
    "addition": "Try adding the tens first, then the ones.",
    "multiplication": "Think of multiplication as equal groups - how many groups, and how big is each group?",
    "division": "Think about how many equal groups you can make, or what number times the divisor gives the total.",
    "algebra": "Try working backwards from the equals sign using the opposite operation.",
    "trigonometry": "Compare the angle to the corner of a square (a right angle) - is it smaller, the same, or bigger?",
    "word_problem": "Decide if you need to combine amounts, take away, share equally, or make equal groups.",
    "patterns": "Look at how much the numbers change by each time - is the 'jump' the same every time?",
    "fractions": "The bottom number (denominator) tells you how many equal parts the whole is split into.",
}

_TRIG_CONCEPTS = {
    "right angle": "A right angle is exactly 90 degrees - like the corner of a square piece of paper.",
    "acute angle": "An acute angle is smaller than a right angle - it looks narrow or 'pointy', less than 90 degrees.",
    "obtuse angle": "An obtuse angle is bigger than a right angle but smaller than a straight line - between 90 and 180 degrees.",
    "straight angle": "A straight angle is a flat line - exactly 180 degrees.",
    "reflex angle": "A reflex angle is bigger than a straight angle - more than 180 degrees.",
}


_PLACE_NAMES = ["ones", "tens", "hundreds", "thousands", "ten-thousands", "hundred-thousands"]


def _column_addition_steps(a: int, b: int) -> List[str]:
    """Standard 'add on paper' column method, explained one place-value column at a time."""
    a_str, b_str = str(a), str(b)
    width = max(len(a_str), len(b_str))
    a_digits = [int(d) for d in a_str.zfill(width)]
    b_digits = [int(d) for d in b_str.zfill(width)]

    steps = [f"Let's add {_fmt(a)} + {_fmt(b)} one column at a time, starting from the ones place - just like on paper."]
    carry = 0
    result_digits: List[int] = []
    for i in range(width - 1, -1, -1):
        place = _PLACE_NAMES[width - 1 - i] if (width - 1 - i) < len(_PLACE_NAMES) else f"place value {width - 1 - i}"
        da, db = a_digits[i], b_digits[i]
        total = da + db + carry
        digit = total % 10
        new_carry = total // 10
        if carry:
            line = f"{place.capitalize()}: {da} + {db} + {carry} (carried from before) = {total}."
        else:
            line = f"{place.capitalize()}: {da} + {db} = {total}."
        if new_carry:
            line += f" Write down {digit}, and carry the {new_carry} over to the next column."
        else:
            line += f" Write down {digit}."
        steps.append(line)
        result_digits.append(digit)
        carry = new_carry
    if carry:
        result_digits.append(carry)
    result_digits.reverse()
    result = int("".join(map(str, result_digits)))
    steps.append(f"Reading all the digits together, top to bottom, gives us {_fmt(result)}.")
    return steps, result


def _addition_builder(question: str, correct_text: str, q: dict) -> Optional[dict]:
    m = re.search(r"What is ([\d,]+) \+ ([\d,]+)(?: \+ ([\d,]+))?", question)
    if not m:
        return None
    nums = [_clean_num(g) for g in m.groups() if g]
    total = sum(nums)
    try:
        correct_num = int(str(correct_text).replace(",", ""))
    except ValueError:
        correct_num = None
    if correct_num is not None and correct_num != total:
        return None

    if len(nums) == 2:
        steps, computed = _column_addition_steps(nums[0], nums[1])
        if computed != total:
            return None
        steps.append(f"So {_fmt(nums[0])} + {_fmt(nums[1])} = {_fmt(total)}.")
        return {"hint": HINTS["addition"], "steps": steps}

    # three numbers: add the first two, then add the running total to the third,
    # narrating each pairwise step the same way.
    steps = [f"We need to find {' + '.join(_fmt(n) for n in nums)}. Let's add two numbers at a time."]
    running = nums[0]
    for i, n in enumerate(nums[1:], start=1):
        pair_steps, pair_result = _column_addition_steps(running, n)
        steps.append(f"Step {i}: add {_fmt(running)} + {_fmt(n)}.")
        steps.extend(pair_steps)
        running = pair_result
    steps.append(f"So the total is {_fmt(running)}.")
    return {"hint": HINTS["addition"], "steps": steps}



def _multiplication_builder(question: str, correct_text: str, q: dict) -> Optional[dict]:
    m = re.search(r"What is (\d+) x (\d+)", question)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    total = a * b
    steps = [f"{a} x {b} means {a} groups of {b} (or {b} groups of {a})."]
    if b <= 6:
        chain = " + ".join([str(a)] * b)
        steps.append(f"Add {a} to itself {b} times: {chain} = {total}.")
    else:
        half = b // 2
        rest = b - half
        steps.append(f"Since {b} is a bit big to add one at a time, split it: {a} x {b} = ({a} x {half}) + ({a} x {rest}).")
        steps.append(f"{a} x {half} = {a * half}, and {a} x {rest} = {a * rest}.")
        steps.append(f"Add them together: {a * half} + {a * rest} = {total}.")
    steps.append(f"So {a} x {b} = {total}.")
    return {"hint": HINTS["multiplication"], "steps": steps}


def _division_builder(question: str, correct_text: str, q: dict) -> Optional[dict]:
    m = re.search(r"What is (\d+) divided by (\d+)", question)
    if not m:
        return None
    a, b = int(m.group(1)), int(m.group(2))
    if b == 0:
        return None
    result = a // b
    steps = [
        f"Dividing {a} by {b} means splitting {a} into {b} equal groups, or asking 'how many {b}s fit into {a}?'.",
        f"Think of the related multiplication fact: {b} x ? = {a}.",
        f"Since {b} x {result} = {a}, the missing number is {result}.",
        f"So {a} divided by {b} = {result}.",
    ]
    return {"hint": HINTS["division"], "steps": steps}


_ALGEBRA_PATTERNS: List[tuple] = [
    (re.compile(r"(\d+) \+ \? = (\d+)"), lambda a, b: (b - a, f"Since {a} + ? = {b}, subtract {a} from {b}: {b} - {a} = {b - a}.")),
    (re.compile(r"\? \+ (\d+) = (\d+)"), lambda a, b: (b - a, f"Since ? + {a} = {b}, subtract {a} from {b}: {b} - {a} = {b - a}.")),
    (re.compile(r"(\d+) - \? = (\d+)"), lambda a, b: (a - b, f"Since {a} - ? = {b}, subtract {b} from {a}: {a} - {b} = {a - b}.")),
    (re.compile(r"\? - (\d+) = (\d+)"), lambda a, b: (a + b, f"Since ? - {a} = {b}, add {a} and {b}: {b} + {a} = {a + b}.")),
    (re.compile(r"(\d+) x \? = (\d+)"), lambda a, b: (b // a if a else None, f"Since {a} x ? = {b}, divide {b} by {a}: {b} / {a} = {b // a if a else '?'}.")),
    (re.compile(r"\? x (\d+) = (\d+)"), lambda a, b: (b // a if a else None, f"Since ? x {a} = {b}, divide {b} by {a}: {b} / {a} = {b // a if a else '?'}.")),
    (re.compile(r"\? (?:divided by|/) (\d+) = (\d+)"), lambda a, b: (a * b, f"Since ? / {a} = {b}, multiply {b} by {a}: {b} x {a} = {a * b}.")),
]


def _algebra_word_form_builder(question: str, correct_num: int) -> Optional[List[str]]:
    """Handles algebra questions phrased in plain words rather than symbols."""
    m = re.search(r"Two numbers add up to (\d+)\.? If the first number is (\d+)", question, re.IGNORECASE)
    if m:
        total, first = int(m.group(1)), int(m.group(2))
        answer = total - first
        if answer != correct_num:
            return None
        return [
            f"The two numbers add up to {total}, and we already know the first one is {first}.",
            f"To find the second number, subtract the first from the total: {total} - {first} = {answer}.",
            f"So the second number is {answer}.",
        ]
    return None


def _algebra_two_step_builder(question: str, correct_num: int) -> Optional[List[str]]:
    """Handles the two-step 'hard' tier algebra forms, e.g. '3 x ? + 4 = 19'."""

    # "{a} x ? + {b} = {c}"  or  "{a} x ? - {b} = {c}"
    m = re.search(r"(\d+) x \? ([+-]) (\d+) = (\d+)", question)
    if m:
        a, sign, b, c = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
        if sign == "+":
            after_undo = c - b
            undo_line = f"First, undo the '+ {b}' by doing the opposite: subtract it from {c}: {c} - {b} = {after_undo}."
        else:
            after_undo = c + b
            undo_line = f"First, undo the '- {b}' by doing the opposite: add it to {c}: {c} + {b} = {after_undo}."
        if a == 0 or after_undo % a != 0:
            return None
        answer = after_undo // a
        if answer != correct_num:
            return None
        return [
            f"This problem has two steps: a multiplication ({a} x ?) and a {'plus' if sign == '+' else 'minus'} {b}.",
            undo_line,
            f"Now we're left with a simpler problem: {a} x ? = {after_undo}.",
            f"Undo the multiplication by dividing: {after_undo} / {a} = {answer}.",
            f"So the missing number is {answer}.",
        ]

    # "{a} - {b} x ? = {c}"
    m = re.search(r"(\d+) - (\d+) x \? = (\d+)", question)
    if m:
        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        product = a - c
        if b == 0 or product % b != 0:
            return None
        answer = product // b
        if answer != correct_num:
            return None
        return [
            f"This problem has two steps: a subtraction and a multiplication ({b} x ?).",
            f"Think of it as {a} minus (something) = {c}. That 'something' must be {a} - {c} = {product}.",
            f"So {b} x ? = {product}.",
            f"Undo the multiplication by dividing: {product} / {b} = {answer}.",
            f"So the missing number is {answer}.",
        ]

    # "(? + {a}) x {b} = {c}"  or  "(? - {a}) x {b} = {c}"
    m = re.search(r"\(\? ([+-]) (\d+)\) x (\d+) = (\d+)", question)
    if m:
        sign, a, b, c = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        if b == 0 or c % b != 0:
            return None
        inner = c // b
        answer = inner - a if sign == "+" else inner + a
        if answer != correct_num:
            return None
        undo_word = "subtract" if sign == "+" else "add"
        return [
            "This problem has two steps, with parentheses around the first one.",
            f"First, undo the 'x {b}' on the outside by dividing: {c} / {b} = {inner}.",
            f"Now we're left with: ? {sign} {a} = {inner}.",
            f"Undo the '{sign} {a}' by doing the opposite - {undo_word} {a}: {inner} {'-' if sign == '+' else '+'} {a} = {answer}.",
            f"So the missing number is {answer}.",
        ]

    # "{a} x (? + {b}) = {c}"  or  "{a} x (? - {b}) = {c}"
    m = re.search(r"(\d+) x \(\? ([+-]) (\d+)\) = (\d+)", question)
    if m:
        a, sign, b, c = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
        if a == 0 or c % a != 0:
            return None
        inner = c // a
        answer = inner - b if sign == "+" else inner + b
        if answer != correct_num:
            return None
        undo_word = "subtract" if sign == "+" else "add"
        return [
            "This problem has two steps, with parentheses around the second one.",
            f"First, undo the '{a} x' on the outside by dividing: {c} / {a} = {inner}.",
            f"Now we're left with: ? {sign} {b} = {inner}.",
            f"Undo the '{sign} {b}' by doing the opposite - {undo_word} {b}: {inner} {'-' if sign == '+' else '+'} {b} = {answer}.",
            f"So the missing number is {answer}.",
        ]

    # "? divided by {a}, plus {b}, equals {c}"
    m = re.search(r"\? divided by (\d+),? plus (\d+),? equals (\d+)", question, re.IGNORECASE)
    if m:
        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        after_undo = c - b
        answer = after_undo * a
        if answer != correct_num:
            return None
        return [
            f"This problem has two steps: a division (? / {a}) and a plus {b}.",
            f"First, undo the '+ {b}' by subtracting it: {c} - {b} = {after_undo}.",
            f"Now we're left with: ? / {a} = {after_undo}.",
            f"Undo the division by multiplying: {after_undo} x {a} = {answer}.",
            f"So the missing number is {answer}.",
        ]

    # "? + {a} = {b} x {c}"  (right side is itself a small multiplication)
    m = re.search(r"\? \+ (\d+) = (\d+) x (\d+)", question)
    if m:
        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        rhs = b * c
        answer = rhs - a
        if answer != correct_num:
            return None
        return [
            f"First, work out the right side of the equals sign: {b} x {c} = {rhs}.",
            f"Now we're left with: ? + {a} = {rhs}.",
            f"Undo the '+ {a}' by subtracting it: {rhs} - {a} = {answer}.",
            f"So the missing number is {answer}.",
        ]

    return None


def _algebra_builder(question: str, correct_text: str, q: dict) -> Optional[dict]:
    try:
        correct_num = int(str(correct_text).strip())
    except ValueError:
        correct_num = None

    if correct_num is not None:
        two_step_steps = _algebra_two_step_builder(question, correct_num)
        if two_step_steps:
            return {"hint": HINTS["algebra"], "steps": two_step_steps}

        word_form_steps = _algebra_word_form_builder(question, correct_num)
        if word_form_steps:
            return {"hint": HINTS["algebra"], "steps": word_form_steps}

    for pattern, fn in _ALGEBRA_PATTERNS:
        m = pattern.search(question)
        if not m:
            continue
        a, b = int(m.group(1)), int(m.group(2))
        answer, explanation_line = fn(a, b)
        if answer is None or str(answer) != str(correct_text).strip():
            continue
        steps = [
            "To find a missing number, do the opposite (inverse) operation of what's shown.",
            explanation_line,
            f"So the missing number is {answer}.",
        ]
        return {"hint": HINTS["algebra"], "steps": steps}
    return None



def _cycle_pattern_builder(items: List[str], correct_text: str) -> Optional[dict]:
    """Handles repeating non-numeric sequences, e.g. shape or color patterns."""
    n = len(items)
    if n < 2:
        return None
    for period in range(1, n):
        if all(items[i] == items[i % period] for i in range(n)):
            predicted = items[n % period]
            if predicted != str(correct_text).strip():
                return None
            unit = ", ".join(items[:period])
            steps = [
                f"Look at the pattern: {', '.join(items)}.",
                f"It repeats every {period} item(s): {unit}.",
                f"Following that repeating pattern, the next one is: {predicted}.",
            ]
            return {"hint": HINTS["patterns"], "steps": steps}
    return None


def _quadratic_pattern_steps(seq: List[Optional[int]], gap: int, correct_num: int) -> Optional[List[str]]:
    """Handles sequences whose 'jumps' themselves grow by a constant amount (e.g. squares, triangular numbers)."""
    diffs: List[Optional[int]] = [
        (seq[i + 1] - seq[i]) if (seq[i] is not None and seq[i + 1] is not None) else None
        for i in range(len(seq) - 1)
    ]
    known_idx = [i for i, d in enumerate(diffs) if d is not None]
    if len(known_idx) < 2:
        return None

    second_diffs = [diffs[b] - diffs[a] for a, b in zip(known_idx, known_idx[1:]) if b - a == 1]
    if not second_diffs or len(set(second_diffs)) != 1 or second_diffs[0] == 0:
        return None
    d2 = second_diffs[0]

    filled = list(diffs)
    for i in range(len(filled)):
        if filled[i] is None and i > 0 and filled[i - 1] is not None:
            filled[i] = filled[i - 1] + d2
    for i in range(len(filled) - 1, -1, -1):
        if filled[i] is None and i < len(filled) - 1 and filled[i + 1] is not None:
            filled[i] = filled[i + 1] - d2
    if any(f is None for f in filled):
        return None

    if gap > 0 and seq[gap - 1] is not None:
        predicted = seq[gap - 1] + filled[gap - 1]
    elif gap < len(seq) - 1 and seq[gap + 1] is not None:
        predicted = seq[gap + 1] - filled[gap]
    else:
        return None
    if predicted != correct_num:
        return None

    known_diff_vals = [diffs[i] for i in known_idx]
    return [
        f"Look at the 'jumps' between each number: {', '.join(str(d) for d in known_diff_vals)}.",
        f"Notice the jumps themselves grow by {d2} each time - that's a growing pattern, not a steady one.",
        f"Following that rule, the missing number is {predicted}.",
    ]


def _patterns_builder(question: str, correct_text: str, q: dict) -> Optional[dict]:
    if ":" not in question:
        return None
    seq_part = question.split(":", 1)[1].strip()
    if seq_part.endswith("?"):
        seq_part = seq_part[:-1]
    raw_tokens = [t.strip() for t in seq_part.split(",")]
    items = [t for t in raw_tokens if t not in ("...", "…", "")]

    is_numeric = all(t == "?" or re.fullmatch(r"-?[\d,]+", t) for t in items)
    if not is_numeric:
        return _cycle_pattern_builder(items, correct_text)

    seq: List[Optional[int]] = []
    gap_positions: List[int] = []
    for t in items:
        if t == "?":
            seq.append(None)
            gap_positions.append(len(seq) - 1)
        else:
            seq.append(int(t.replace(",", "")))

    if len(gap_positions) == 0:
        # "What is the next number..." style: no literal "?" in the sequence,
        # just trailing "..." - treat the slot right after the last known value as the gap.
        seq.append(None)
        gap_positions = [len(seq) - 1]
    if len(gap_positions) != 1:
        return None
    gap = gap_positions[0]

    try:
        correct_num = int(str(correct_text).replace(",", ""))
    except ValueError:
        return None

    known_diffs = [seq[i + 1] - seq[i] for i in range(len(seq) - 1) if seq[i] is not None and seq[i + 1] is not None]
    if known_diffs and len(set(known_diffs)) == 1 and known_diffs[0] != 0:
        diff = known_diffs[0]
        predicted = None
        if gap > 0 and seq[gap - 1] is not None:
            predicted = seq[gap - 1] + diff
        elif gap < len(seq) - 1 and seq[gap + 1] is not None:
            predicted = seq[gap + 1] - diff
        if predicted == correct_num:
            rule = f"add {diff}" if diff > 0 else f"subtract {abs(diff)}"
            steps = [
                f"Look at how much the numbers change each time: {', '.join(str(d) for d in known_diffs)}.",
                f"Every step, the rule is: {rule}.",
                f"Applying that rule gives {predicted}, so the missing number is {predicted}.",
            ]
            return {"hint": HINTS["patterns"], "steps": steps}

    # try a constant multiply (geometric growth) rule
    ratio_pairs = [(seq[i], seq[i + 1]) for i in range(len(seq) - 1) if seq[i] not in (None, 0) and seq[i + 1] is not None]
    if ratio_pairs and all(b % a == 0 for a, b in ratio_pairs):
        ratios = {b // a for a, b in ratio_pairs}
        if len(ratios) == 1 and ratios != {1}:
            ratio = ratios.pop()
            predicted = None
            if gap > 0 and seq[gap - 1] is not None:
                predicted = seq[gap - 1] * ratio
            elif gap < len(seq) - 1 and seq[gap + 1] is not None and seq[gap + 1] % ratio == 0:
                predicted = seq[gap + 1] // ratio
            if predicted == correct_num:
                steps = [
                    "Look at how the numbers change - each one is multiplied by the same amount.",
                    f"Every step, the rule is: multiply by {ratio}.",
                    f"Applying that rule gives {predicted}, so the missing number is {predicted}.",
                ]
                return {"hint": HINTS["patterns"], "steps": steps}

    # try a constant divide (geometric shrink) rule, e.g. 81, 27, 9, 3, ...
    if ratio_pairs and all(a % b == 0 for a, b in ratio_pairs):
        divisors = {a // b for a, b in ratio_pairs}
        if len(divisors) == 1 and divisors != {1}:
            divisor = divisors.pop()
            predicted = None
            if gap > 0 and seq[gap - 1] is not None and seq[gap - 1] % divisor == 0:
                predicted = seq[gap - 1] // divisor
            elif gap < len(seq) - 1 and seq[gap + 1] is not None:
                predicted = seq[gap + 1] * divisor
            if predicted == correct_num:
                steps = [
                    "Look at how the numbers change - each one is divided by the same amount.",
                    f"Every step, the rule is: divide by {divisor}.",
                    f"Applying that rule gives {predicted}, so the missing number is {predicted}.",
                ]
                return {"hint": HINTS["patterns"], "steps": steps}

    quadratic_steps = _quadratic_pattern_steps(seq, gap, correct_num)
    if quadratic_steps:
        return {"hint": HINTS["patterns"], "steps": quadratic_steps}

    return None


_ANGLE_BASE_DEGREES = {
    "straight angle": 180,
    "right angle": 90,
    "full circle": 360,
    "circle": 360,
}
_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


def _word_to_int(text: str) -> Optional[int]:
    if text.isdigit():
        return int(text)
    return _NUMBER_WORDS.get(text.lower())


# Exact-match knowledge base for conceptual (non-computational) trigonometry facts.
_TRIG_QA: Dict[str, List[str]] = {
    "Which type of angle looks like the corner of a square?": [
        "A right angle is a special angle that looks exactly like the corner of a square or a piece of paper.",
        "It always measures exactly 90 degrees.",
        "So the answer is: Right angle.",
    ],
    "An angle smaller than a right angle is called a(n)?": [
        "Picture a right angle (90 degrees) - like the corner of a square.",
        "An angle that is smaller and looks more 'pointy' or 'narrow' than that is called an acute angle.",
        "So the answer is: Acute angle.",
    ],
    "An angle bigger than a right angle but smaller than a straight line is called a(n)?": [
        "A right angle is 90 degrees, and a straight line (a straight angle) is 180 degrees.",
        "An angle that is wider than 90 degrees but not as wide as 180 degrees is called an obtuse angle.",
        "So the answer is: Obtuse angle.",
    ],
    "How many right angles does a square have?": [
        "A square has 4 corners.",
        "Every single corner of a square forms a perfect right angle (90 degrees).",
        "So a square has 4 right angles.",
    ],
    "A triangle has how many angles?": [
        "A triangle is a shape with exactly 3 straight sides.",
        "Every place where two sides meet forms a corner, and each corner makes an angle.",
        "Since a triangle has 3 corners, it has 3 angles.",
    ],
    "A triangle with exactly one right angle is called a?": [
        "Triangles can be named by their angles.",
        "A triangle that has one angle measuring exactly 90 degrees (a right angle) is called a right triangle.",
        "So the answer is: Right triangle.",
    ],
    "A straight line makes an angle of how many degrees?": [
        "If you open an angle all the way until it looks like a flat, straight line, that's called a straight angle.",
        "A straight angle always measures 180 degrees.",
    ],
    "A full turn all the way around makes an angle of how many degrees?": [
        "If you spin all the way around in a circle and come back to where you started, that's called a full turn.",
        "A full turn always measures 360 degrees.",
    ],
    "A right angle measures how many degrees?": [
        "A right angle is the angle you see at the corner of a square piece of paper.",
        "It always measures exactly 90 degrees.",
    ],
    "Which of these is an example of an acute angle?": [
        "An acute angle is any angle smaller than a right angle (less than 90 degrees).",
        "Out of the choices, 30 degrees is the only one less than 90 degrees.",
        "So the answer is: 30 degrees.",
    ],
    "Which of these is an example of an obtuse angle?": [
        "An obtuse angle is bigger than a right angle (more than 90 degrees) but smaller than a straight angle (less than 180 degrees).",
        "Out of the choices, 120 degrees fits between 90 and 180 degrees.",
        "So the answer is: 120 degrees.",
    ],
    "The corner of a book page forms what kind of angle?": [
        "The corner of a book page is a square corner, just like the corner of a piece of paper.",
        "That makes it a right angle (90 degrees).",
    ],
    "Which shape has no corners or angles at all?": [
        "Angles are formed where two straight sides meet at a corner.",
        "A circle is round all the way around - it has no straight sides and no corners.",
        "So a circle has no angles at all.",
    ],
    "Which angle looks 'wide open', more than a right angle?": [
        "A right angle looks like the corner of a square (90 degrees).",
        "An angle that looks more 'open' or spread out than that is bigger than 90 degrees - that's an obtuse angle.",
    ],
    "Which angle looks 'narrow' or 'pointy', less than a right angle?": [
        "A right angle looks like the corner of a square (90 degrees).",
        "An angle that looks narrower, or comes more to a point, is smaller than 90 degrees - that's an acute angle.",
    ],
    "A door usually opens to make what kind of angle with the wall?": [
        "When a door is opened partway, picture the angle between the door and the wall.",
        "A door is usually opened to about 90 degrees - a right angle.",
    ],
    "Which of these shapes has 4 right angles?": [
        "A right angle is a square corner (90 degrees).",
        "A rectangle always has exactly 4 corners, and every one of them is a right angle.",
    ],
    "How many angles does a triangle have?": [
        "A triangle is a shape with exactly 3 straight sides.",
        "Every place where two sides meet forms a corner, and each corner makes an angle.",
        "Since a triangle has 3 corners, it has 3 angles.",
    ],
    "How many angles does a square have?": [
        "A square has 4 straight sides.",
        "Every place where two sides meet forms a corner, and each corner makes an angle.",
        "Since a square has 4 corners, it has 4 angles.",
    ],
    "The hands of a clock at 3:00 form what kind of angle?": [
        "At 3:00, the minute hand points straight up (to the 12) and the hour hand points straight to the right (to the 3).",
        "The angle between them is a perfect square-corner angle - a right angle (90 degrees).",
    ],
    "A rectangle's four angles add up to how many degrees in total?": [
        "Every angle in a rectangle is a right angle (90 degrees), and a rectangle has 4 of them.",
        "Add them up: 90 + 90 + 90 + 90 = 360 degrees.",
    ],
    "Which of these has square corners (right angles) at every corner?": [
        "A right angle is a square corner (90 degrees).",
        "A square has 4 corners, and every one of them is a perfect right angle.",
        "So the answer is: Square.",
    ],
    "A slice of pizza usually looks like what kind of angle?": [
        "A right angle looks like the corner of a square (90 degrees) - not too narrow, not too wide.",
        "A pizza slice is usually much narrower and pointier than that, so it's smaller than 90 degrees.",
        "That makes it an acute angle.",
    ],
    "An open book lying flat makes what kind of angle?": [
        "When a book lies completely flat open, the two pages form one straight line.",
        "An angle that looks like a flat, straight line is a straight angle (180 degrees).",
    ],
    "Which shape is made only of straight sides and angles: a circle or a triangle?": [
        "A circle is round all the way around, with no straight sides at all.",
        "A triangle has 3 straight sides that meet at 3 corners, forming angles.",
        "So the answer is: Triangle.",
    ],
    "An angle of 200 degrees (more than a straight line) is called what kind of angle?": [
        "A straight angle is 180 degrees - a flat line.",
        "An angle bigger than that, like 200 degrees, is called a reflex angle.",
        "So the answer is: Reflex angle.",
    ],
}


def _trigonometry_builder(question: str, correct_text: str, q: dict) -> Optional[dict]:
    # "A triangle has angles of X degrees and Y degrees. What is the third angle?"
    m = re.search(r"triangle has angles of (\d+) degrees and (\d+) degrees", question, re.IGNORECASE)
    if not m:
        m = re.search(r"one angle.*?(\d+) degrees and (?:another|one).*?(\d+) degrees", question, re.IGNORECASE)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        result = 180 - a - b
        if str(result) in correct_text:
            steps = [
                "Remember: the three angles inside any triangle always add up to 180 degrees.",
                f"We know two angles: {a} degrees and {b} degrees.",
                f"Add them: {a} + {b} = {a + b} degrees.",
                f"Subtract from 180: 180 - {a + b} = {result} degrees.",
                f"So the missing angle is {result} degrees.",
            ]
            return {"hint": HINTS["trigonometry"], "steps": steps}

    # Two angles that sum to a known total (phrased either as "(X degrees)" or "add up to X degrees")
    total_m = re.search(r"\((\d+) degrees\)", question) or re.search(r"add up to (\d+) degrees", question, re.IGNORECASE)
    given_m = re.search(r"If one (?:angle )?is (\d+) degrees", question, re.IGNORECASE)
    if total_m and given_m:
        total, a = int(total_m.group(1)), int(given_m.group(1))
        result = total - a
        if str(result) in correct_text:
            steps = [
                f"These two angles together always add up to {total} degrees.",
                f"Subtract the angle we know from the total: {total} - {a} = {result}.",
                f"So the other angle is {result} degrees.",
            ]
            return {"hint": HINTS["trigonometry"], "steps": steps}

    # "{base angle/shape} is split into {n} equal parts/angles" -> base degrees / n
    m = re.search(
        r"(straight angle|right angle|full circle|circle)s? is split into (\w+|\d+) equal (?:smaller )?(?:parts?|angles?)",
        question,
        re.IGNORECASE,
    )
    base = n = None
    if m:
        base = _ANGLE_BASE_DEGREES.get(m.group(1).lower())
        n = _word_to_int(m.group(2))
    else:
        # "{X} degree corner is split ... into {n} equal parts"
        m2 = re.search(
            r"(\d+) degree corner is split (?:evenly )?into (\w+|\d+) (?:equal )?(?:smaller )?parts?",
            question,
            re.IGNORECASE,
        )
        if m2:
            base = int(m2.group(1))
            n = _word_to_int(m2.group(2))
    if base and n:
        result = base // n
        if str(result) in correct_text:
            steps = [
                f"The whole angle here is {base} degrees.",
                f"Splitting it evenly into {n} equal parts means dividing: {base} / {n} = {result}.",
                f"So each part is {result} degrees.",
            ]
            return {"hint": HINTS["trigonometry"], "steps": steps}

    if question in _TRIG_QA:
        return {"hint": HINTS["trigonometry"], "steps": list(_TRIG_QA[question])}

    return None


# Exact-match, hand-written step-by-step explanations for every word problem in the
# bank. Using exact text (rather than a generic NLP-lite solver) guarantees each
# explanation genuinely narrates the intended story and operation correctly.
_WORD_PROBLEM_EXPLANATIONS: Dict[str, List[str]] = {
    "Maria has 14 apples. She gives 6 to her friend. How many apples does she have left?": [
        "Maria starts with 14 apples.",
        "She gives 6 away, so we subtract: 14 - 6.",
        "14 - 6 = 8.",
        "So Maria has 8 apples left.",
    ],
    "A classroom has 5 rows of 6 desks. How many desks are there in total?": [
        "There are 5 rows, and each row has 6 desks.",
        "To find the total, multiply the rows by the desks in each row: 5 x 6.",
        "5 x 6 = 30.",
        "So there are 30 desks in total.",
    ],
    "Tom has 3 bags with 8 marbles in each bag. How many marbles does he have in total?": [
        "Tom has 3 bags, and each bag has 8 marbles.",
        "To find the total, multiply: 3 x 8.",
        "3 x 8 = 24.",
        "So Tom has 24 marbles in total.",
    ],
    "There are 48 cookies to be shared equally among 6 kids. How many cookies does each kid get?": [
        "There are 48 cookies to share equally among 6 kids.",
        "Sharing equally means dividing: 48 / 6.",
        "48 / 6 = 8.",
        "So each kid gets 8 cookies.",
    ],
    "A farmer has 9 rows of corn with 7 plants in each row. How many corn plants are there in total?": [
        "There are 9 rows, and each row has 7 plants.",
        "Multiply the rows by the plants in each row: 9 x 7.",
        "9 x 7 = 63.",
        "So there are 63 corn plants in total.",
    ],
    "Ben read 23 pages on Monday and 18 pages on Tuesday. How many pages did he read in total?": [
        "Ben read 23 pages on Monday and 18 pages on Tuesday.",
        "To find the total, add the two amounts: 23 + 18.",
        "23 + 18 = 41.",
        "So Ben read 41 pages in total.",
    ],
    "There are 32 students going on a field trip. Each bus holds 8 students. How many buses are needed?": [
        "There are 32 students, and each bus holds 8 students.",
        "To find how many buses are needed, divide the students by how many fit on each bus: 32 / 8.",
        "32 / 8 = 4.",
        "So 4 buses are needed.",
    ],
    "Emma had $50. She spent $18 on a book. How much money does she have left?": [
        "Emma starts with $50.",
        "She spends $18, so we subtract: $50 - $18.",
        "$50 - $18 = $32.",
        "So Emma has $32 left.",
    ],
    "A baker makes 6 trays of muffins with 8 muffins on each tray. How many muffins are there in total?": [
        "There are 6 trays, and each tray has 8 muffins.",
        "Multiply the trays by the muffins on each tray: 6 x 8.",
        "6 x 8 = 48.",
        "So there are 48 muffins in total.",
    ],
    "Liam has 45 stickers. He gives away 17. How many stickers does he have left?": [
        "Liam starts with 45 stickers.",
        "He gives away 17, so we subtract: 45 - 17.",
        "45 - 17 = 28.",
        "So Liam has 28 stickers left.",
    ],
    "There are 4 shelves with 9 books on each shelf. How many books are there in total?": [
        "There are 4 shelves, and each shelf has 9 books.",
        "Multiply the shelves by the books on each shelf: 4 x 9.",
        "4 x 9 = 36.",
        "So there are 36 books in total.",
    ],
    "A garden has 72 flowers divided equally into 8 rows. How many flowers are in each row?": [
        "There are 72 flowers divided equally into 8 rows.",
        "Dividing equally means: 72 / 8.",
        "72 / 8 = 9.",
        "So there are 9 flowers in each row.",
    ],
    "Sam has 3 apples. He gets 2 more. How many apples does he have now?": [
        "Sam starts with 3 apples.",
        "He gets 2 more, so we add: 3 + 2.",
        "3 + 2 = 5.",
        "So Sam has 5 apples now.",
    ],
    "There are 5 birds on a tree. 2 fly away. How many birds are left?": [
        "There are 5 birds on the tree.",
        "2 fly away, so we subtract: 5 - 2.",
        "5 - 2 = 3.",
        "So there are 3 birds left.",
    ],
    "A box has 4 pencils. Another box has 3 pencils. How many pencils in total?": [
        "One box has 4 pencils, and the other box has 3 pencils.",
        "To find the total, add them: 4 + 3.",
        "4 + 3 = 7.",
        "So there are 7 pencils in total.",
    ],
    "Maya has 6 candies and eats 2. How many candies are left?": [
        "Maya starts with 6 candies.",
        "She eats 2, so we subtract: 6 - 2.",
        "6 - 2 = 4.",
        "So Maya has 4 candies left.",
    ],
    "There are 2 rows of chairs with 3 chairs in each row. How many chairs in total?": [
        "There are 2 rows, and each row has 3 chairs.",
        "Multiply the rows by the chairs in each row: 2 x 3.",
        "2 x 3 = 6.",
        "So there are 6 chairs in total.",
    ],
    "Jake has 10 dollars and spends 4. How much does he have left?": [
        "Jake starts with 10 dollars.",
        "He spends 4, so we subtract: 10 - 4.",
        "10 - 4 = 6.",
        "So Jake has 6 dollars left.",
    ],
    "A bag has 5 red balls and 4 blue balls. How many balls in total?": [
        "There are 5 red balls and 4 blue balls.",
        "To find the total, add them: 5 + 4.",
        "5 + 4 = 9.",
        "So there are 9 balls in total.",
    ],
    "There are 8 cupcakes and 3 are eaten. How many cupcakes are left?": [
        "There are 8 cupcakes.",
        "3 are eaten, so we subtract: 8 - 3.",
        "8 - 3 = 5.",
        "So there are 5 cupcakes left.",
    ],
    "A store had 120 apples. They sold 45 in the morning and 38 in the afternoon. How many apples are left?": [
        "The store starts with 120 apples.",
        "First, find the total sold: 45 + 38 = 83.",
        "Then subtract that from what they started with: 120 - 83.",
        "120 - 83 = 37.",
        "So there are 37 apples left.",
    ],
    "Each box holds 24 crayons. There are 9 boxes, and 3 crayons are broken. How many good crayons are there?": [
        "There are 9 boxes, and each box holds 24 crayons.",
        "First, find the total number of crayons: 9 x 24 = 216.",
        "Then subtract the 3 broken ones: 216 - 3.",
        "216 - 3 = 213.",
        "So there are 213 good crayons.",
    ],
    "Tickets cost $8 each. A family of 4 buys tickets and pays with $50. How much change do they get?": [
        "Each ticket costs $8, and the family needs 4 tickets.",
        "First, find the total cost: 4 x $8 = $32.",
        "They pay with $50, so subtract the cost: $50 - $32.",
        "$50 - $32 = $18.",
        "So they get $18 in change.",
    ],
    "A school has 6 classrooms with 24 students each. If 15 students are absent today, how many students are present?": [
        "There are 6 classrooms, and each one has 24 students.",
        "First, find the total number of students: 6 x 24 = 144.",
        "15 students are absent, so subtract: 144 - 15.",
        "144 - 15 = 129.",
        "So 129 students are present.",
    ],
    "A garden has 8 rows of 12 flowers. If 19 flowers wilt, how many flowers are still healthy?": [
        "There are 8 rows, and each row has 12 flowers.",
        "First, find the total number of flowers: 8 x 12 = 96.",
        "19 flowers wilt, so subtract: 96 - 19.",
        "96 - 19 = 77.",
        "So 77 flowers are still healthy.",
    ],
    "Ravi buys 5 packs of stickers with 12 stickers in each pack. He gives 17 stickers to his friends. How many stickers does he have left?": [
        "Ravi buys 5 packs, and each pack has 12 stickers.",
        "First, find the total number of stickers: 5 x 12 = 60.",
        "He gives away 17, so subtract: 60 - 17.",
        "60 - 17 = 43.",
        "So Ravi has 43 stickers left.",
    ],
    "A theater has 18 rows with 15 seats in each row. If 52 seats are empty, how many seats are filled?": [
        "There are 18 rows, and each row has 15 seats.",
        "First, find the total number of seats: 18 x 15 = 270.",
        "52 seats are empty, so subtract: 270 - 52.",
        "270 - 52 = 218.",
        "So 218 seats are filled.",
    ],
    "Maria earns $9 per hour. She works 6 hours on Saturday and 4 hours on Sunday. How much does she earn in total?": [
        "First, find the total hours Maria worked: 6 + 4 = 10 hours.",
        "She earns $9 for every hour, so multiply: 10 x $9.",
        "10 x $9 = $90.",
        "So Maria earns $90 in total.",
    ],
    "A pond has 6 ducks. 3 more ducks arrive. How many ducks are there now?": [
        "The pond starts with 6 ducks.",
        "3 more arrive, so we add: 6 + 3.",
        "6 + 3 = 9.",
        "So there are 9 ducks now.",
    ],
    "There are 12 crayons and 5 are given away. How many crayons are left?": [
        "There are 12 crayons.",
        "5 are given away, so we subtract: 12 - 5.",
        "12 - 5 = 7.",
        "So there are 7 crayons left.",
    ],
    "A pack has 3 rows of 3 cookies. How many cookies are there in total?": [
        "There are 3 rows, and each row has 3 cookies.",
        "Multiply the rows by the cookies in each row: 3 x 3.",
        "3 x 3 = 9.",
        "So there are 9 cookies in total.",
    ],
    "Nina has 7 dollars. Her mom gives her 3 more. How much money does she have now?": [
        "Nina starts with 7 dollars.",
        "Her mom gives her 3 more, so we add: 7 + 3.",
        "7 + 3 = 10.",
        "So Nina has 10 dollars now.",
    ],
    "A parking lot has 14 rows with 20 cars in each row. If 37 spots are empty, how many cars are parked?": [
        "There are 14 rows, and each row has 20 spots.",
        "First, find the total number of spots: 14 x 20 = 280.",
        "37 spots are empty, so subtract: 280 - 37.",
        "280 - 37 = 243.",
        "So 243 cars are parked.",
    ],
    "A bakery makes 15 dozen cookies (12 per dozen). If they sell 140 cookies, how many are left?": [
        "A dozen means 12, so 15 dozen cookies is 15 x 12 = 180 cookies.",
        "They sell 140, so subtract: 180 - 140.",
        "180 - 140 = 40.",
        "So there are 40 cookies left.",
    ],
    "Jon reads 24 pages a day for 6 days, then 15 more pages on the 7th day. How many pages has he read in total?": [
        "For the first 6 days, Jon reads 24 pages each day: 6 x 24 = 144.",
        "On the 7th day, he reads 15 more pages, so add: 144 + 15.",
        "144 + 15 = 159.",
        "So Jon has read 159 pages in total.",
    ],
    "A farmer collects 18 eggs each day for 5 days. If 12 eggs break, how many good eggs remain?": [
        "The farmer collects 18 eggs each day for 5 days: 5 x 18 = 90.",
        "12 eggs break, so subtract: 90 - 12.",
        "90 - 12 = 78.",
        "So 78 good eggs remain.",
    ],
}


def _word_problem_builder(question: str, correct_text: str, q: dict) -> Optional[dict]:
    steps = _WORD_PROBLEM_EXPLANATIONS.get(question)
    if not steps:
        return None
    # Safety check: the last step must actually state the recorded correct answer.
    if str(correct_text).strip() not in steps[-1]:
        return None
    return {"hint": HINTS["word_problem"], "steps": steps}


# --- Fractions -----------------------------------------------------------

_FRACTION_QA: Dict[str, List[str]] = {
    "Which fraction represents one half?": [
        "1/2 means one part out of two equal parts - that's exactly 'one half'.",
        "So the answer is: 1/2.",
    ],
    "Which fraction is equal to one half?": [
        "One half means splitting something into 2 equal parts and taking 1 of them - that's 1/2.",
        "2/4 also means splitting into 4 equal parts and taking 2 of them, which is the same amount as 1/2.",
        "So the answer is: 2/4.",
    ],
    "If a pizza is cut into 4 equal slices and you eat 1, what fraction did you eat?": [
        "There are 4 equal slices in total, and you ate 1 of them.",
        "That means you ate 1 out of 4 parts, written as 1/4.",
    ],
    "Which fraction represents one whole?": [
        "A fraction equals 'one whole' when the top number (numerator) and bottom number (denominator) are the same.",
        "4/4 means all 4 out of 4 parts - the whole thing.",
        "So the answer is: 4/4.",
    ],
    "In the fraction 3/4, what is the top number (3) called?": [
        "In a fraction, the top number tells us how many parts we have.",
        "That number is called the numerator.",
        "So the answer is: Numerator.",
    ],
    "In the fraction 3/4, what is the bottom number (4) called?": [
        "In a fraction, the bottom number tells us how many equal parts the whole is divided into.",
        "That number is called the denominator.",
        "So the answer is: Denominator.",
    ],
    "A candy bar is split into 3 equal parts. What is each part called?": [
        "The candy bar is split into 3 equal parts in total.",
        "Each single part out of those 3 is called 1/3 (one third).",
        "So the answer is: 1/3.",
    ],
    "Which of these fractions means 'two out of five equal parts'?": [
        "The top number (numerator) tells us how many parts we have: 2.",
        "The bottom number (denominator) tells us the total equal parts: 5.",
        "So 'two out of five' is written as 2/5.",
    ],
    "If you shade 2 out of 4 equal parts of a shape, what fraction is shaded?": [
        "You shaded 2 parts, and there are 4 equal parts in total.",
        "That's written as 2 (numerator) over 4 (denominator): 2/4.",
    ],
    "Which fraction shows 3 equal parts out of 3 total (a whole)?": [
        "When the numerator and denominator are the same number, the fraction equals one whole.",
        "3 out of 3 parts is the whole thing, written as 3/3.",
    ],
    "A cake is cut into 6 equal pieces. If you take 1 piece, what fraction is that?": [
        "The cake is cut into 6 equal pieces in total.",
        "Taking just 1 piece out of those 6 is written as 1/6.",
    ],
    "Which of these fractions is the same as 1 whole?": [
        "A fraction equals 1 whole when the numerator and denominator are the same number.",
        "5/5 means 5 out of 5 parts - that's the whole thing.",
        "So the answer is: 5/5.",
    ],
}

_FRACTION_WORD_PROBLEMS: Dict[str, List[str]] = {
    "Maria ate 2/8 of a pizza and her brother ate 3/8. How much of the pizza did they eat together?": [
        "Maria ate 2/8, and her brother ate 3/8 - both are eighths, so we can add the numerators.",
        "2 + 3 = 5.",
        "Keep the denominator the same: 5/8.",
        "So together they ate 5/8 of the pizza.",
    ],
    "A recipe needs 1/4 cup of sugar and 2/4 cup of flour. How much more flour than sugar is needed?": [
        "The flour is 2/4 cup and the sugar is 1/4 cup - both are fourths, so we can subtract the numerators.",
        "2 - 1 = 1.",
        "Keep the denominator the same: 1/4.",
        "So there is 1/4 cup more flour than sugar.",
    ],
}


def _fraction_of_builder(question: str, correct_text: str) -> Optional[List[str]]:
    m = re.search(r"What is 1/(\d+) of (\d+)", question)
    if not m:
        return None
    denom, whole = int(m.group(1)), int(m.group(2))
    if denom == 0 or whole % denom != 0:
        return None
    result = whole // denom
    if str(result) != str(correct_text).strip():
        return None
    return [
        f"Finding 1/{denom} of a number means splitting it into {denom} equal groups.",
        f"Divide {whole} by {denom}: {whole} / {denom} = {result}.",
        f"So 1/{denom} of {whole} is {result}.",
    ]


def _fraction_add_sub_builder(question: str, correct_text: str) -> Optional[List[str]]:
    m = re.search(r"What is (\d+)/(\d+) \+ (\d+)/(\d+)", question)
    if m:
        n1, d1, n2, d2 = (int(g) for g in m.groups())
        if d1 != d2:
            return None
        result = f"{n1 + n2}/{d1}"
        if result != str(correct_text).strip():
            return None
        return [
            f"Since both fractions have the same denominator ({d1}), we can just add the numerators.",
            f"{n1} + {n2} = {n1 + n2}.",
            f"Keep the denominator the same: {result}.",
            f"So {n1}/{d1} + {n2}/{d2} = {result}.",
        ]

    m = re.search(r"What is (\d+)/(\d+) - (\d+)/(\d+)", question)
    if m:
        n1, d1, n2, d2 = (int(g) for g in m.groups())
        if d1 != d2:
            return None
        result = f"{n1 - n2}/{d1}"
        if result != str(correct_text).strip():
            return None
        return [
            f"Since both fractions have the same denominator ({d1}), we can just subtract the numerators.",
            f"{n1} - {n2} = {n1 - n2}.",
            f"Keep the denominator the same: {result}.",
            f"So {n1}/{d1} - {n2}/{d2} = {result}.",
        ]

    return None


def _fraction_comparison_builder(question: str, correct_text: str) -> Optional[List[str]]:
    """Handles 'Which fraction is larger/smaller/closer to 0: A/B or C/D?' style questions."""
    fracs = re.findall(r"(\d+)/(\d+)", question)
    if len(fracs) != 2:
        return None
    (n1, d1), (n2, d2) = ((int(a), int(b)) for a, b in fracs)
    frac1_text, frac2_text = f"{n1}/{d1}", f"{n2}/{d2}"

    lower_q = question.lower()
    want_smaller = "smaller" in lower_q or "closer to 0" in lower_q

    left, right = n1 * d2, n2 * d1
    if left == right:
        return None  # not designed to handle a genuine tie; fall back to generic

    bigger_text = frac1_text if left > right else frac2_text
    smaller_text = frac2_text if left > right else frac1_text
    answer = smaller_text if want_smaller else bigger_text
    if answer != str(correct_text).strip():
        return None

    common = d1 * d2
    return [
        f"To compare {frac1_text} and {frac2_text}, let's rewrite them with the same denominator.",
        f"{frac1_text} = {n1 * d2}/{common} (multiply top and bottom by {d2}).",
        f"{frac2_text} = {n2 * d1}/{common} (multiply top and bottom by {d1}).",
        f"Now compare the numerators over {common}: {n1 * d2} vs {n2 * d1}.",
        f"So {answer} is the {'smaller' if want_smaller else 'larger'} fraction.",
    ]


def _fraction_extreme_builder(question: str, correct_text: str, q: dict) -> Optional[List[str]]:
    """Handles 'Which fraction is the largest/smallest?' where the 4 options are the fractions to compare."""
    if not re.search(r"largest|biggest|smallest", question, re.IGNORECASE):
        return None
    parsed = []
    for opt in q["options"]:
        m = re.fullmatch(r"(\d+)/(\d+)", opt.strip())
        if not m:
            return None
        parsed.append((int(m.group(1)), int(m.group(2)), opt))

    denom_lcm = 1
    for _, d, _ in parsed:
        denom_lcm = denom_lcm * d // gcd(denom_lcm, d)

    converted = [(n * (denom_lcm // d), opt) for n, d, opt in parsed]
    is_smallest = "smallest" in question.lower()
    target = min(converted, key=lambda x: x[0]) if is_smallest else max(converted, key=lambda x: x[0])
    if target[1] != str(correct_text).strip():
        return None

    lines = [f"{opt} = {scaled}/{denom_lcm}" for scaled, opt in converted]
    return [
        f"Let's compare all the fractions by giving them the same denominator: {denom_lcm}.",
        *lines,
        f"Now compare the numerators over {denom_lcm}: {', '.join(str(c[0]) for c in converted)}.",
        f"The {'smallest' if is_smallest else 'largest'} one is {target[1]}.",
    ]


def _fraction_equivalent_builder(question: str, correct_text: str) -> Optional[List[str]]:
    m = re.search(r"equivalent to (\d+)/(\d+)", question, re.IGNORECASE)
    if not m:
        return None
    n, d = int(m.group(1)), int(m.group(2))
    cm = re.fullmatch(r"(\d+)/(\d+)", str(correct_text).strip())
    if not cm:
        return None
    cn, cd = int(cm.group(1)), int(cm.group(2))
    if n * cd != cn * d:
        return None  # the recorded answer isn't actually equivalent - don't claim it is

    if cd % d == 0:
        factor = cd // d
        return [
            "Two fractions are equivalent if they represent the same amount, just written differently.",
            f"Multiply the top and bottom of {n}/{d} by {factor}: {n} x {factor} / {d} x {factor} = {cn}/{cd}.",
            f"So {cn}/{cd} is equivalent to {n}/{d}.",
        ]
    if d % cd == 0:
        factor = d // cd
        return [
            "Two fractions are equivalent if they represent the same amount, just written differently.",
            f"Divide the top and bottom of {n}/{d} by {factor}: {n} / {factor} over {d} / {factor} = {cn}/{cd}.",
            f"So {cn}/{cd} is equivalent to {n}/{d}.",
        ]
    return [
        "Two fractions are equivalent if they represent the same amount, just written differently.",
        f"{n}/{d} and {cn}/{cd} both represent the same value.",
        f"So {cn}/{cd} is equivalent to {n}/{d}.",
    ]


def _fractions_builder(question: str, correct_text: str, q: dict) -> Optional[dict]:
    word_problem_steps = _FRACTION_WORD_PROBLEMS.get(question)
    if word_problem_steps and str(correct_text).strip() in word_problem_steps[-1]:
        return {"hint": HINTS["fractions"], "steps": word_problem_steps}

    for builder in (
        lambda: _fraction_of_builder(question, correct_text),
        lambda: _fraction_add_sub_builder(question, correct_text),
        lambda: _fraction_extreme_builder(question, correct_text, q),
        lambda: _fraction_comparison_builder(question, correct_text),
        lambda: _fraction_equivalent_builder(question, correct_text),
    ):
        steps = builder()
        if steps:
            return {"hint": HINTS["fractions"], "steps": steps}

    if question in _FRACTION_QA:
        return {"hint": HINTS["fractions"], "steps": list(_FRACTION_QA[question])}

    return None



_BUILDERS: Dict[str, Callable[[str, str, dict], Optional[dict]]] = {
    "addition": _addition_builder,
    "multiplication": _multiplication_builder,
    "division": _division_builder,
    "algebra": _algebra_builder,
    "patterns": _patterns_builder,
    "trigonometry": _trigonometry_builder,
    "word_problem": _word_problem_builder,
    "fractions": _fractions_builder,
}


def _generic(question: str, correct_text: str, topic: str) -> dict:
    steps = [f'Let\'s look at the question together: "{question}"']
    if topic == "trigonometry":
        lower = correct_text.lower()
        for key, note in _TRIG_CONCEPTS.items():
            if key in lower:
                steps.append(note)
                break
    elif topic == "word_problem":
        steps.append("Decide what the story is asking: are we combining, taking away, sharing equally, or making groups?")
    steps.append(f"The correct answer is: {correct_text}.")
    return {"hint": HINTS.get(topic, "Read the question again and look for key words that tell you what to do."), "steps": steps}


def build_explanation(q: dict) -> dict:
    """Returns {"hint": str, "steps": [str, ...]} teaching how to reach the correct answer."""
    topic = q["topic"]
    question = q["question"]
    correct_text = q["options"][q["answer_index"]]

    builder = _BUILDERS.get(topic)
    if builder:
        result = builder(question, correct_text, q)
        if result:
            return result
    return _generic(question, correct_text, topic)


def build_hint(q: dict) -> str:
    """A lighter-weight nudge shown on demand, without revealing the answer."""
    return HINTS.get(q["topic"], "Read the question again and look for key words that tell you what to do.")
