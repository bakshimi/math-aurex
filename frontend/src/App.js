// Plain React (no JSX) app state machine: start -> category -> quiz -> result.
const QUESTION_SECONDS = 15;

function App() {
  const e = React.createElement;
  const { useState, useEffect } = React;

  const [screen, setScreen] = useState("start"); // 'start' | 'category' | 'difficulty' | 'quiz' | 'result'
  const [grade, setGrade] = useState(null);
  const [categories, setCategories] = useState([]);
  const [category, setCategory] = useState(null);
  const [categoryLabel, setCategoryLabel] = useState(null);
  const [difficulties, setDifficulties] = useState([]);
  const [difficulty, setDifficulty] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [question, setQuestion] = useState(null);
  const [triedIndices, setTriedIndices] = useState(new Set());
  const [lastResult, setLastResult] = useState(null);
  const [pending, setPending] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [secondsLeft, setSecondsLeft] = useState(QUESTION_SECONDS);
  const [timerEnabled, setTimerEnabled] = useState(true);
  const [hint, setHint] = useState(null);
  const [hintLoading, setHintLoading] = useState(false);

  const [authChecked, setAuthChecked] = useState(false);
  const [authUser, setAuthUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState(null);

  function resetQuizState() {
    setScreen("start");
    setGrade(null);
    setCategories([]);
    setCategory(null);
    setCategoryLabel(null);
    setDifficulties([]);
    setDifficulty(null);
    setSessionId(null);
    setQuestion(null);
    setTriedIndices(new Set());
    setLastResult(null);
    setPending(null);
    setResult(null);
    setHint(null);
  }

  // On first load, restore a session from a saved token (if any) instead of forcing re-login every visit.
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setAuthChecked(true);
      return;
    }
    fetchMe()
      .then((user) => setAuthUser(user))
      .catch(() => clearToken())
      .finally(() => setAuthChecked(true));
  }, []);

  // If any API call comes back 401 (expired/invalid token), drop back to the login screen.
  useEffect(() => {
    function handleUnauthorized() {
      clearToken();
      setAuthUser(null);
      resetQuizState();
    }
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, []);

  async function handleAuthenticated(mode, { username, password, displayName }) {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const res = mode === "login" ? await login(username, password) : await register(username, password, displayName);
      setToken(res.access_token);
      setAuthUser(res.user);
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    clearToken();
    setAuthUser(null);
    resetQuizState();
  }

  async function handleSelectGrade(selectedGrade) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchCategories(selectedGrade);
      setGrade(selectedGrade);
      setCategories(res.categories);
      setScreen("category");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectCategory(selectedCategory) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchDifficulties(grade, selectedCategory);
      const match = categories.find((c) => c.key === selectedCategory);
      setCategory(selectedCategory);
      setCategoryLabel(match ? match.label : selectedCategory);
      setDifficulties(res.difficulties);
      setScreen("difficulty");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectDifficulty(selectedDifficulty) {
    setLoading(true);
    setError(null);
    try {
      const res = await startSession(grade, category, selectedDifficulty);
      setDifficulty(selectedDifficulty);
      setSessionId(res.session_id);
      setQuestion(res.question);
      setTriedIndices(new Set());
      setLastResult(null);
      setPending(null);
      setHint(null);
      setScreen("quiz");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelect(idx) {
    if (loading || pending) return;
    setLoading(true);
    setError(null);
    try {
      const res = await submitAnswer(sessionId, idx);
      setLastResult({
        selectedIndex: idx,
        correct: res.correct,
        attemptsLeft: res.attempts_left,
        correctAnswerIndex: res.correct_answer_index,
        explanation: res.explanation,
      });
      if (res.correct || res.attempts_left === 0) {
        setPending({
          nextQuestion: res.next_question,
          finished: res.finished,
          score: res.score,
          total: res.total,
        });
      } else {
        setTriedIndices((prev) => new Set(prev).add(idx));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleTimeout() {
    if (loading || pending) return;
    setLoading(true);
    setError(null);
    try {
      const res = await timeoutQuestion(sessionId);
      setLastResult({
        selectedIndex: null,
        correct: false,
        attemptsLeft: 0,
        correctAnswerIndex: res.correct_answer_index,
        timedOut: true,
        explanation: res.explanation,
      });
      setPending({
        nextQuestion: res.next_question,
        finished: res.finished,
        score: res.score,
        total: res.total,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleRequestHint() {
    if (hint || hintLoading) return;
    setHintLoading(true);
    try {
      const res = await fetchHint(sessionId);
      setHint(res.hint);
    } catch (err) {
      setError(err.message);
    } finally {
      setHintLoading(false);
    }
  }

  function handleContinue() {
    if (pending.finished) {
      setResult({ score: pending.score, total: pending.total });
      setScreen("result");
    } else {
      setQuestion(pending.nextQuestion);
    }
    setPending(null);
    setLastResult(null);
    setTriedIndices(new Set());
    setHint(null);
  }

  function handleBackToGrades() {
    setScreen("start");
    setCategories([]);
  }

  function handleBackToCategories() {
    setScreen("category");
    setDifficulties([]);
  }

  function handleAbandonQuiz() {
    if (!window.confirm("Leave this quiz and choose a different topic? Your progress on this attempt will be lost.")) {
      return;
    }
    if (sessionId) endSession(sessionId);
    setSessionId(null);
    setQuestion(null);
    setPending(null);
    setLastResult(null);
    setHint(null);
    setDifficulty(null);
    setScreen("category");
  }

  function handleChooseAnotherTopic() {
    setSessionId(null);
    setQuestion(null);
    setResult(null);
    setDifficulty(null);
    setScreen("category");
  }

  function handleTryAgain() {
    setResult(null);
    handleSelectDifficulty(difficulty);
  }

  // Reset & (re)start the per-question countdown whenever a fresh question becomes active.
  useEffect(() => {
    if (!timerEnabled || screen !== "quiz" || !question || pending) return undefined;
    setSecondsLeft(QUESTION_SECONDS);
    const intervalId = setInterval(() => {
      setSecondsLeft((s) => (s > 0 ? s - 1 : 0));
    }, 1000);
    return () => clearInterval(intervalId);
  }, [question, pending, screen, timerEnabled]);

  // Trigger the timeout handler exactly once when the countdown reaches zero.
  useEffect(() => {
    if (timerEnabled && screen === "quiz" && !pending && !loading && secondsLeft === 0) {
      handleTimeout();
    }
  }, [secondsLeft]);

  const children = [];
  if (!authChecked) {
    children.push(e("div", { className: "card start-card", key: "loading" }, e("p", { className: "status" }, "Loading...")));
  } else if (!authUser) {
    children.push(e(AuthScreen, { key: "auth", onAuthenticated: handleAuthenticated, loading: authLoading, error: authError }));
  } else if (screen === "start") {
    children.push(e(StartScreen, { key: "start", onSelectGrade: handleSelectGrade, loading, error }));
  } else if (screen === "category") {
    children.push(
      e(CategoryScreen, {
        key: "category",
        grade,
        categories,
        onSelectCategory: handleSelectCategory,
        onBack: handleBackToGrades,
        loading,
        error,
      })
    );
  } else if (screen === "difficulty") {
    children.push(
      e(DifficultyScreen, {
        key: "difficulty",
        grade,
        categoryLabel,
        difficulties,
        timerEnabled,
        onToggleTimer: setTimerEnabled,
        onSelectDifficulty: handleSelectDifficulty,
        onBack: handleBackToCategories,
        loading,
        error,
      })
    );
  } else if (screen === "quiz" && question) {
    children.push(
      e("button", { className: "back-to-topics-btn", key: "back-nav", onClick: handleAbandonQuiz }, "‹ Back to Topics")
    );
    if (timerEnabled) {
      children.push(
        e("div", { className: "timer-badge", key: "timer", "data-warning": secondsLeft <= 5 }, `${secondsLeft}s`)
      );
    }
    children.push(
      e(QuestionCard, {
        key: "quiz",
        question,
        triedIndices,
        lastResult,
        pending,
        loading,
        hint,
        hintLoading,
        onSelect: handleSelect,
        onContinue: handleContinue,
        onRequestHint: handleRequestHint,
      })
    );
    if (error) children.push(e("p", { className: "error", key: "error" }, error));
  } else if (screen === "result" && result) {
    children.push(
      e(ResultScreen, {
        key: "result",
        score: result.score,
        total: result.total,
        onTryAgain: handleTryAgain,
        onChooseTopic: handleChooseAnotherTopic,
      })
    );
  }

  if (authUser) {
    children.push(
      e(
        "div",
        { className: "account-bar", key: "account-bar" },
        `\uD83D\uDC4B ${authUser.display_name}`,
        e("button", { className: "logout-btn", onClick: handleLogout }, "Log out")
      )
    );
  }

  return e("div", { className: "app-container" }, children);
}

