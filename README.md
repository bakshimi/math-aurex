# Math Education — Quiz App (Pilot: Grade 3)

A full-stack math skills quiz for students in grades 3–8. This pilot release
supports **Grade 3** only; more grades can be added by dropping a new
`gradeN.json` question bank into `backend/app/questions/` and registering it
in `GRADE_QUESTION_FILES`.

## Stack
- **Backend**: Python 3.11+, FastAPI, in-memory session store
- **Frontend**: React 18, loaded from locally vendored UMD bundles and written
  as plain JavaScript (`React.createElement`, no JSX). This avoids requiring
  Node.js/npm — the FastAPI server serves the frontend directly as static
  files, so the whole app runs from a single Python process.

## Rules implemented
- 25 multiple-choice questions per session (4 options, 1 correct)
- Up to 3 attempts per question before automatically moving to the next one
- Questions are randomly sampled per session and never repeat within that session

## Project layout
```
backend/
  app/
    main.py          FastAPI app + routes + mounts the frontend as static files
    models.py         Pydantic request/response schemas
    quiz_engine.py     Session state + scoring logic
    questions/
      grade3.json      Grade 3 question bank
  requirements.txt
frontend/
  index.html           Loads vendor/ React + src/ app scripts, no build step
  vendor/              Locally vendored React 18 + ReactDOM UMD bundles
  src/
    api.js             Fetch wrapper for the backend API
    App.js               Screen state machine (start / quiz / result), plain JS
    index.css
    components/
      StartScreen.js
      QuestionCard.js
      ResultScreen.js
```

## Running locally
Only Python is required — no Node.js/npm.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000, pick Grade 3, and start the quiz.

### Note on the build-free frontend
This project was set up in an environment where the npm registry was not
reachable (only Python's outbound HTTPS access was allowed). To keep "React JS
as the UI" without Node/npm, React and ReactDOM 18 UMD bundles were downloaded
once via Python into `frontend/vendor/`, and the app components are written as
plain `.js` files using `React.createElement` instead of JSX. If Node/npm
becomes available later, this can be migrated to a Vite + JSX setup by adding
back a bundler and converting `.js` files to `.jsx`.

