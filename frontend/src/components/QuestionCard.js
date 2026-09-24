// Plain React (no JSX) question card: shows one question, 4 options, feedback, and attempts.
const OPTION_LABELS = ["A", "B", "C", "D"];

function QuestionCard(props) {
  const e = React.createElement;
  const { question, triedIndices, lastResult, pending, loading, hint, hintLoading, onSelect, onContinue, onRequestHint } = props;
  // Reflect the latest attempt's remaining count once the user has answered; otherwise use the fresh question's value.
  const attemptsLeft = lastResult ? lastResult.attemptsLeft : question.attempts_left;

  function optionClass(idx) {
    const classes = ["option-btn"];
    if (lastResult && lastResult.selectedIndex === idx) {
      classes.push(lastResult.correct ? "option-correct" : "option-wrong");
    }
    if (lastResult && !lastResult.correct && lastResult.attemptsLeft === 0 && idx === lastResult.correctAnswerIndex) {
      classes.push("option-correct");
    }
    if (triedIndices.has(idx)) {
      classes.push("option-tried");
    }
    return classes.join(" ");
  }

  const optionButtons = question.options.map((opt, idx) =>
    e(
      "button",
      {
        key: idx,
        className: optionClass(idx),
        disabled: loading || !!pending || triedIndices.has(idx),
        onClick: () => onSelect(idx),
      },
      e("span", { className: "option-label", key: "label" }, OPTION_LABELS[idx]),
      opt
    )
  );

  let feedbackNode = null;
  if (lastResult) {
    let feedbackClass = "feedback-wrong";
    let text = `Not quite. ${lastResult.attemptsLeft} attempt(s) left.`;
    if (lastResult.correct) {
      feedbackClass = "feedback-correct";
      text = "Correct! Great job.";
    } else if (lastResult.timedOut) {
      feedbackClass = "feedback-exhausted";
      text = `Time's up! The correct answer was ${OPTION_LABELS[lastResult.correctAnswerIndex]}: ${question.options[lastResult.correctAnswerIndex]}.`;
    } else if (lastResult.attemptsLeft === 0) {
      feedbackClass = "feedback-exhausted";
      text = `Out of attempts. The correct answer was ${OPTION_LABELS[lastResult.correctAnswerIndex]}: ${question.options[lastResult.correctAnswerIndex]}.`;
    }
    feedbackNode = e("div", { className: `feedback ${feedbackClass}` }, text);
  }

  // "Teacher" step-by-step solution card, shown once attempts are exhausted or time runs out.
  let explanationNode = null;
  if (lastResult && !lastResult.correct && lastResult.explanation && lastResult.explanation.length > 0) {
    explanationNode = e(
      "div",
      { className: "explanation-card" },
      e("div", { className: "explanation-title" }, "📚 Let's learn this together"),
      e(
        "ol",
        { className: "explanation-steps" },
        lastResult.explanation.map((step, idx) =>
          e("li", { key: idx, style: { animationDelay: `${0.5 + idx * 0.45}s` } }, step)
        )
      )
    );
  }

  const canRequestHint = !pending;
  const hintNode = e(
    "div",
    { className: "hint-row" },
    canRequestHint &&
      e(
        "button",
        { className: "hint-btn", onClick: onRequestHint, disabled: hintLoading || !!hint },
        hintLoading ? "Loading hint..." : "💡 Need a hint?"
      ),
    hint && e("div", { className: "hint-box" }, "💡 ", hint)
  );

  return e(
    "div",
    { className: "card quiz-card" },
    e(
      "div",
      { className: "quiz-header" },
      e("span", null, `Question ${question.index} / ${question.total}`),
      e("span", { className: "topic-badge" }, question.topic.replace("_", " "))
    ),
    e("h2", { className: "question-text" }, question.question),
    e("div", { className: "options-grid" }, optionButtons),
    e("div", { className: "attempts-row" }, "Attempts left: ", e("strong", null, attemptsLeft)),
    hintNode,
    feedbackNode,
    explanationNode,
    pending &&
      e(
        "button",
        { className: "continue-btn", onClick: onContinue },
        pending.finished ? "See Results" : "Next Question"
      )
  );
}
