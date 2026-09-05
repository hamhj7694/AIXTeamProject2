"""Environment names only; never load a local environment file implicitly."""
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent


def internal_path(value: str, root: Path = ROOT) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError("Runtime paths must remain inside the application root")
    # Reject links even when they happen to point back inside this root.
    for part in (candidate, *candidate.parents):
        if part == resolved_root:
            break
        if part.is_symlink() or (part.exists() and bool(getattr(part.lstat(), "st_file_attributes", 0) & 0x400)):
            raise ValueError("Runtime paths cannot use links")
    return resolved


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    database_url: str = field(default="", repr=False)
    ai_api_base_url: str = "http://127.0.0.1:8101"
    ai_timeout_seconds: float = 5.0
    admin_case_password: str = field(default="", repr=False)
    attachment_storage_root: Path = ROOT / "backend/data/uploads"
    vector_store_path: Path = ROOT / "backend/data/vector_db"

    @classmethod
    def from_environment(cls) -> "Settings":
        settings = cls(
            app_env=os.getenv("APP_ENV", "development"),
            database_url=os.getenv("DATABASE_URL", ""),
            ai_api_base_url=os.getenv("AI_API_BASE_URL", "http://127.0.0.1:8101"),
            ai_timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "5")),
            admin_case_password=os.getenv("ADMIN_CASE_PASSWORD", ""),
            attachment_storage_root=internal_path(os.getenv("ATTACHMENT_STORAGE_ROOT", "backend/data/uploads")),
            vector_store_path=internal_path(os.getenv("VECTOR_STORE_PATH", "backend/data/vector_db")),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.app_env not in {"development", "test", "production"}:
            raise ValueError("Invalid APP_ENV")
        target = urlsplit(self.ai_api_base_url)
        if (target.scheme != "http" or target.hostname != "127.0.0.1" or not target.port
                or (self.app_env == "production" and target.port != 8101)
                or target.path not in {"", "/"} or target.query or target.fragment or target.username):
            raise ValueError("AI API must use loopback, and port 8101 in production")
        if not 0 < self.ai_timeout_seconds <= 30:
            raise ValueError("AI_TIMEOUT_SECONDS must be in (0, 30]")
        if self.database_url:
            self.validate_database()

    def validate_database(self) -> None:
        if not self.database_url:
            raise ValueError("DATABASE_URL is required")
        try:
            url = make_url(self.database_url)
        except Exception:
            raise ValueError("Invalid DATABASE_URL format") from None
        if url.drivername == "mysql+pymysql":
            if not url.database or not url.database.startswith("csr_v4"):
                raise ValueError("Database name must start with csr_v4")
        elif url.drivername == "sqlite" and self.app_env == "test":
            if url.database != ":memory:":
                if not url.database:
                    raise ValueError("A test database path is required")
                internal_path(url.database)
        else:
            raise ValueError("Use MySQL; SQLite is allowed only for isolated tests")
