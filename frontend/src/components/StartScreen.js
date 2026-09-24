// Plain React (no JSX) start screen: grade picker for the quiz.
const GRADES = [3, 4, 5, 6, 7, 8];
const AVAILABLE_GRADES = new Set([3]); // pilot: grade 3 only

function StartScreen(props) {
  const e = React.createElement;
  const { onSelectGrade, loading, error } = props;

  const gradeButtons = GRADES.map((grade) => {
    const available = AVAILABLE_GRADES.has(grade);
    return e(
      "button",
      {
        key: grade,
        className: `grade-btn ${available ? "" : "grade-btn-disabled"}`,
        disabled: !available || loading,
        onClick: () => onSelectGrade(grade),
        title: available ? `Start Grade ${grade} quiz` : "Coming soon",
      },
      `Grade ${grade}`,
      !available && e("span", { className: "badge", key: "badge" }, "Coming soon")
    );
  });

  return e(
    "div",
    { className: "card start-card" },
    e("h1", null, "Math Skills Quiz"),
    e("p", { className: "subtitle" }, "Pick your grade to begin a multiple-choice challenge!"),
    e("div", { className: "grade-grid" }, gradeButtons),
    loading && e("p", { className: "status" }, "Loading categories..."),
    error && e("p", { className: "error" }, error),
    e(
      "ul",
      { className: "rules" },
      e("li", null, "Up to 6 questions per topic & difficulty"),
      e("li", null, "4 answer choices per question"),
      e("li", null, "Up to 3 attempts per question"),
      e("li", null, "15 seconds per question"),
      e("li", null, "Questions won't repeat until you've seen the whole set")
    )
  );
}

