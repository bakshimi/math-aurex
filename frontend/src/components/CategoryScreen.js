// Plain React (no JSX) category picker shown after a grade is selected.
function CategoryScreen(props) {
  const e = React.createElement;
  const { grade, categories, onSelectCategory, onBack, loading, error } = props;

  const categoryButtons = (categories || []).map((cat) => {
    const available = cat.count > 0;
    return e(
      "button",
      {
        key: cat.key,
        className: `grade-btn ${available ? "" : "grade-btn-disabled"}`,
        disabled: !available || loading,
        onClick: () => onSelectCategory(cat.key),
        title: available ? `Start ${cat.label}` : "No questions yet",
      },
      cat.label,
      !available && e("span", { className: "badge", key: "badge" }, "Coming soon")
    );
  });

  return e(
    "div",
    { className: "card start-card" },
    e("h1", null, `Grade ${grade} — Pick a Topic`),
    e("p", { className: "subtitle" }, "Choose a category to begin your challenge!"),
    e("div", { className: "grade-grid" }, categoryButtons),
    loading && e("p", { className: "status" }, "Loading questions..."),
    error && e("p", { className: "error" }, error),
    e("button", { className: "continue-btn back-btn", onClick: onBack }, "Back to Grade Selection")
  );
}
