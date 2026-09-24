// Plain React (no JSX) results screen.
const MEDALS = [
  { minPct: 90, tier: "gold", emoji: "🥇", label: "Gold Medal!" },
  { minPct: 70, tier: "silver", emoji: "🥈", label: "Silver Medal!" },
  { minPct: 50, tier: "bronze", emoji: "🥉", label: "Bronze Medal!" },
];

function getMedal(pct) {
  return MEDALS.find((m) => pct >= m.minPct) || null;
}

function ResultScreen(props) {
  const e = React.createElement;
  const { score, total, onTryAgain, onChooseTopic } = props;
  const pct = Math.round((score / total) * 100);
  const medal = getMedal(pct);

  let message = "Keep practicing — you'll get there!";
  if (pct >= 90) message = "Outstanding work! You're a math star!";
  else if (pct >= 70) message = "Great job! Solid math skills.";
  else if (pct >= 50) message = "Good effort! A little more practice will help.";

  return e(
    "div",
    { className: "card result-card" },
    e("h1", null, "Quiz Complete!"),
    medal &&
      e(
        "div",
        { className: `medal-badge medal-${medal.tier}`, key: "medal" },
        e("div", { className: "medal-emoji" }, medal.emoji),
        e("div", { className: "medal-label" }, medal.label)
      ),
    e("p", { className: "score-line" }, "You scored ", e("strong", null, score), " out of ", e("strong", null, total)),
    e("p", { className: "score-pct" }, `${pct}%`),
    e("p", { className: "message" }, message),
    e("button", { className: "continue-btn", onClick: onTryAgain }, "Try Again"),
    e("button", { className: "continue-btn back-btn", onClick: onChooseTopic }, "Choose Another Topic")
  );
}
