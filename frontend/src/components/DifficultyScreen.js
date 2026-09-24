// Plain React (no JSX) difficulty picker shown after a category is selected.
function DifficultyScreen(props) {
  const e = React.createElement;
  const { grade, categoryLabel, difficulties, timerEnabled, onToggleTimer, onSelectDifficulty, onBack, loading, error } = props;

  const difficultyButtons = (difficulties || []).map((diff) => {
    const available = diff.count > 0;
    return e(
      "button",
      {
        key: diff.key,
        className: `grade-btn difficulty-btn-${diff.key} ${available ? "" : "grade-btn-disabled"}`,
        disabled: !available || loading,
        onClick: () => onSelectDifficulty(diff.key),
        title: available ? `Start ${diff.label} difficulty` : "No questions yet",
      },
      diff.label,
      !available && e("span", { className: "badge", key: "badge" }, "Coming soon")
    );
  });

  const timerToggle = e(
    "div",
    { className: "timer-toggle", key: "timer-toggle" },
    e("span", { className: "timer-toggle-label" }, "Question timer:"),
    e(
      "div",
      { className: "timer-toggle-buttons" },
      e(
        "button",
        {
          type: "button",
          className: `toggle-btn ${timerEnabled ? "toggle-btn-active" : ""}`,
          onClick: () => onToggleTimer(true),
        },
        "⏱ 15s Timer"
      ),
      e(
        "button",
        {
          type: "button",
          className: `toggle-btn ${!timerEnabled ? "toggle-btn-active" : ""}`,
          onClick: () => onToggleTimer(false),
        },
        "🕒 No Timer"
      )
    )
  );

  return e(
    "div",
    { className: "card start-card" },
    e("h1", null, `Grade ${grade} — ${categoryLabel}`),
    e("p", { className: "subtitle" }, "Choose a difficulty level to begin your challenge!"),
    timerToggle,
    e("div", { className: "grade-grid difficulty-grid" }, difficultyButtons),
    loading && e("p", { className: "status" }, "Loading questions..."),
    error && e("p", { className: "error" }, error),
    e("button", { className: "continue-btn back-btn", onClick: onBack }, "Back to Topics")
  );
}

