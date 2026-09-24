// Plain React (no JSX) login/register screen shown before the app is usable.
function AuthScreen(props) {
  const e = React.createElement;
  const { useState } = React;
  const { onAuthenticated, loading, error } = props;

  const [mode, setMode] = useState("login"); // 'login' | 'register'
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [localError, setLocalError] = useState(null);

  function handleSubmit(ev) {
    ev.preventDefault();
    setLocalError(null);
    if (username.trim().length < 3) {
      setLocalError("Username must be at least 3 characters.");
      return;
    }
    if (password.length < 8) {
      setLocalError("Password must be at least 8 characters.");
      return;
    }
    onAuthenticated(mode, { username: username.trim(), password, displayName: displayName.trim() });
  }

  const shownError = localError || error;

  return e(
    "div",
    { className: "card start-card" },
    e("h1", null, "Math Skills Quiz"),
    e("p", { className: "subtitle" }, mode === "login" ? "Log in to start practicing!" : "Create an account to get started!"),
    e(
      "form",
      { className: "auth-form", onSubmit: handleSubmit },
      e("label", { className: "auth-label", htmlFor: "auth-username" }, "Username"),
      e("input", {
        id: "auth-username",
        className: "auth-input",
        type: "text",
        value: username,
        autoComplete: "username",
        onChange: (ev) => setUsername(ev.target.value),
        placeholder: "e.g. mathwhiz3",
      }),
      mode === "register" &&
        e(
          "div",
          { key: "display-name-field" },
          e("label", { className: "auth-label", htmlFor: "auth-display-name" }, "Display name (optional)"),
          e("input", {
            id: "auth-display-name",
            className: "auth-input",
            type: "text",
            value: displayName,
            onChange: (ev) => setDisplayName(ev.target.value),
            placeholder: "e.g. Alex",
          })
        ),
      e("label", { className: "auth-label", htmlFor: "auth-password" }, "Password"),
      e("input", {
        id: "auth-password",
        className: "auth-input",
        type: "password",
        value: password,
        autoComplete: mode === "login" ? "current-password" : "new-password",
        onChange: (ev) => setPassword(ev.target.value),
        placeholder: "At least 8 characters",
      }),
      shownError && e("p", { className: "error", key: "error" }, shownError),
      e(
        "button",
        { className: "continue-btn", type: "submit", disabled: loading },
        loading ? "Please wait..." : mode === "login" ? "Log In" : "Register"
      )
    ),
    e(
      "button",
      {
        className: "continue-btn back-btn",
        type: "button",
        onClick: () => {
          setLocalError(null);
          setMode(mode === "login" ? "register" : "login");
        },
      },
      mode === "login" ? "Need an account? Register" : "Already have an account? Log In"
    )
  );
}
