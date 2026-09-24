// Same-origin by default since FastAPI serves this static frontend directly.
const API_BASE = window.API_BASE || "";
const TOKEN_STORAGE_KEY = "mathQuizToken";

function getToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handleResponse(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    if (res.status === 401) {
      // Token missing/expired/invalid: let the app know so it can show the login screen again.
      window.dispatchEvent(new CustomEvent("auth:unauthorized"));
    }
    throw new Error(body.detail || `Request failed with status ${res.status}`);
  }
  return res.json();
}

function register(username, password, displayName) {
  return fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, display_name: displayName || undefined }),
  }).then(handleResponse);
}

function login(username, password) {
  return fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  }).then(handleResponse);
}

function fetchMe() {
  return fetch(`${API_BASE}/api/auth/me`, { headers: { ...authHeaders() } }).then(handleResponse);
}

function fetchGrades() {
  return fetch(`${API_BASE}/api/grades`).then(handleResponse);
}

function fetchCategories(grade) {
  return fetch(`${API_BASE}/api/categories?grade=${grade}`).then(handleResponse);
}

function fetchDifficulties(grade, category) {
  return fetch(`${API_BASE}/api/difficulties?grade=${grade}&category=${encodeURIComponent(category)}`).then(handleResponse);
}

function startSession(grade, category, difficulty) {
  return fetch(`${API_BASE}/api/session/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ grade, category, difficulty }),
  }).then(handleResponse);
}

function submitAnswer(sessionId, selectedIndex) {
  return fetch(`${API_BASE}/api/session/${sessionId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ selected_index: selectedIndex }),
  }).then(handleResponse);
}

function timeoutQuestion(sessionId) {
  return fetch(`${API_BASE}/api/session/${sessionId}/timeout`, {
    method: "POST",
    headers: { ...authHeaders() },
  }).then(handleResponse);
}

function fetchHint(sessionId) {
  return fetch(`${API_BASE}/api/session/${sessionId}/hint`, { headers: { ...authHeaders() } }).then(handleResponse);
}

function endSession(sessionId) {
  return fetch(`${API_BASE}/api/session/${sessionId}`, { method: "DELETE", headers: { ...authHeaders() } }).catch(() => {});
}

