"""Environment-driven configuration. Reads from process env vars (or a .env file
loaded by the process manager / container runtime) so behavior differs cleanly
between development and production without code changes.
"""
import logging
import os
import secrets

logger = logging.getLogger("app.config")


def _split_csv(value: str) -> list:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings:
    def __init__(self) -> None:
        self.environment = os.environ.get("ENVIRONMENT", "development").lower()
        self.is_production = self.environment == "production"

        # Same-origin deployment (FastAPI serving the frontend) needs no CORS at
        # all; only set ALLOWED_ORIGINS if the frontend is ever hosted separately.
        origins_env = os.environ.get("ALLOWED_ORIGINS", "")
        self.allowed_origins = _split_csv(origins_env) if origins_env else [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]

        # Hide interactive API docs in production by default (reduces attack
        # surface / doesn't advertise internal endpoints); override if desired.
        self.enable_docs = os.environ.get("ENABLE_DOCS", "false" if self.is_production else "true").lower() == "true"

        # JWT signing secret for user auth. Fail fast in production rather than
        # silently signing tokens with a secret that changes every restart (which
        # would log every user out) or is otherwise insecure.
        jwt_secret = os.environ.get("JWT_SECRET", "")
        if not jwt_secret:
            if self.is_production:
                raise RuntimeError(
                    "JWT_SECRET must be set in production (e.g. a long random string). "
                    "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )
            jwt_secret = secrets.token_urlsafe(48)
            logger.warning(
                "JWT_SECRET not set - using an ephemeral development secret. "
                "All logins will be invalidated on restart. Set JWT_SECRET for persistent sessions."
            )
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = "HS256"
        self.jwt_expire_minutes = int(os.environ.get("JWT_EXPIRE_MINUTES", "10080"))  # 7 days

        # Where the SQLite user database file lives.
        self.users_db_path = os.environ.get("USERS_DB_PATH", "app/data/users.db")



settings = Settings()
