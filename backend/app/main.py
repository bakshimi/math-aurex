"""FastAPI app exposing the math quiz API and serving the build-free React frontend."""
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles

from app import auth_db, quiz_engine, security
from app.config import settings
from app.models import (
    AnswerRequest,
    AnswerResponse,
    CategoriesResponse,
    DifficultiesResponse,
    HintResponse,
    LoginRequest,
    RegisterRequest,
    StartSessionRequest,
    StartSessionResponse,
    TokenResponse,
    UserOut,
)

app = FastAPI(
    title="Math Education Quiz API",
    version="0.1.0",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
)

auth_db.init_db()

# Kept for flexibility if the frontend is ever served from a different origin/port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def no_cache_for_app_source(request, call_next):
    """Prevent browsers from serving a stale index.html/src/*.js after a deploy.
    (/vendor/* is exempt since those UMD bundles are pinned and never change.)
    """
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/src/"):
        response.headers["Cache-Control"] = "no-store"
    return response

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme)) -> UserOut:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    payload = security.decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please log in again.")
    row = auth_db.get_user_by_id(int(payload["sub"]))
    if row is None:
        raise HTTPException(status_code=401, detail="Account no longer exists. Please register again.")
    return UserOut(id=row["id"], username=row["username"], display_name=row["display_name"])


SUPPORTED_GRADES = sorted(quiz_engine.GRADE_QUESTION_FILES.keys())


@app.get("/healthz")
def healthz():
    """Liveness/readiness probe for load balancers, containers, and uptime checks."""
    return {"status": "ok"}


@app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest):
    if auth_db.username_exists(payload.username):
        raise HTTPException(status_code=409, detail="That username is already taken.")

    password_hash = security.hash_password(payload.password)
    row = auth_db.create_user(
        username=payload.username,
        display_name=payload.display_name or payload.username,
        password_hash=password_hash,
    )
    token = security.create_access_token(row["id"], row["username"])
    return TokenResponse(
        access_token=token,
        user=UserOut(id=row["id"], username=row["username"], display_name=row["display_name"]),
    )


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    rate_limit_key = payload.username.lower()
    if security.is_rate_limited(rate_limit_key):
        raise HTTPException(status_code=429, detail="Too many failed attempts. Please wait a minute and try again.")

    row = auth_db.get_user_by_username(payload.username)
    if row is None or not security.verify_password(payload.password, row["password_hash"]):
        security.record_failed_attempt(rate_limit_key)
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    security.clear_failed_attempts(rate_limit_key)
    token = security.create_access_token(row["id"], row["username"])
    return TokenResponse(
        access_token=token,
        user=UserOut(id=row["id"], username=row["username"], display_name=row["display_name"]),
    )


@app.get("/api/auth/me", response_model=UserOut)
def get_me(current_user: UserOut = Depends(get_current_user)):
    return current_user


@app.get("/api/grades")
def get_grades():
    return {"grades": SUPPORTED_GRADES}


@app.get("/api/categories", response_model=CategoriesResponse)
def get_categories(grade: int):
    if grade not in quiz_engine.GRADE_QUESTION_FILES:
        raise HTTPException(status_code=400, detail=f"Grade {grade} is not supported yet.")
    return CategoriesResponse(categories=quiz_engine.get_categories(grade))


@app.get("/api/difficulties", response_model=DifficultiesResponse)
def get_difficulties(grade: int, category: str):
    if grade not in quiz_engine.GRADE_QUESTION_FILES:
        raise HTTPException(status_code=400, detail=f"Grade {grade} is not supported yet.")
    return DifficultiesResponse(difficulties=quiz_engine.get_difficulties(grade, category))


@app.post("/api/session/start", response_model=StartSessionResponse)
def start_session(payload: StartSessionRequest, current_user: UserOut = Depends(get_current_user)):
    if payload.grade not in quiz_engine.GRADE_QUESTION_FILES:
        raise HTTPException(status_code=400, detail=f"Grade {payload.grade} is not supported yet.")

    try:
        session_id, session = quiz_engine.create_session(
            payload.grade, payload.category, payload.difficulty, f"user:{current_user.id}"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return StartSessionResponse(
        session_id=session_id,
        grade=payload.grade,
        category=payload.category,
        difficulty=payload.difficulty,
        total_questions=session.total,
        question=session.current_question_out(),
    )


@app.post("/api/session/{session_id}/answer", response_model=AnswerResponse)
def submit_answer(session_id: str, payload: AnswerRequest, current_user: UserOut = Depends(get_current_user)):
    session = quiz_engine.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found. Please start a new quiz.")
    if session.finished:
        raise HTTPException(status_code=400, detail="This quiz session has already finished.")

    result = session.submit_answer(payload.selected_index)
    return AnswerResponse(**result)


@app.get("/api/session/{session_id}/hint", response_model=HintResponse)
def get_hint(session_id: str, current_user: UserOut = Depends(get_current_user)):
    session = quiz_engine.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found. Please start a new quiz.")
    if session.finished:
        raise HTTPException(status_code=400, detail="This quiz session has already finished.")

    return HintResponse(hint=session.get_hint())


@app.post("/api/session/{session_id}/timeout", response_model=AnswerResponse)
def timeout_question(session_id: str, current_user: UserOut = Depends(get_current_user)):
    session = quiz_engine.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found. Please start a new quiz.")
    if session.finished:
        raise HTTPException(status_code=400, detail="This quiz session has already finished.")

    result = session.handle_timeout()
    return AnswerResponse(**result)


@app.delete("/api/session/{session_id}")
def delete_session(session_id: str, current_user: UserOut = Depends(get_current_user)):
    quiz_engine.end_session(session_id)
    return {"status": "ended"}


# Serve the build-free React frontend (plain JS + vendored UMD React, no npm/Node required).
# Mounted last so it never shadows the /api/* routes above.
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
