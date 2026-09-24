FROM python:3.11-slim

WORKDIR /srv

# Install dependencies first so this layer is cached unless requirements change.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the backend app and the build-free frontend (sibling directories, same
# layout main.py expects: FRONTEND_DIR = backend/app/main.py's parent.parent.parent / "frontend").
COPY backend/ backend/
COPY frontend/ frontend/

WORKDIR /srv/backend

ENV ENVIRONMENT=production \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1

# Single worker is required: quiz sessions live in process memory, so multiple
# workers would each have their own disjoint session store (see README).
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "1", "-b", "0.0.0.0:8000", "--access-logfile", "-"]
