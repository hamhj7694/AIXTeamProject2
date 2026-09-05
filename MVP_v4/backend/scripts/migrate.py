"""Run only this application's migrations against an explicitly selected V4 DB."""
from alembic import command
from alembic.config import Config

from backend.config import ROOT, Settings


def migration_config(settings: Settings) -> Config:
    settings.validate_database()
    config = Config()
    config.set_main_option("script_location", str(ROOT / "backend/migrations"))
    config.attributes["settings"] = settings
    return config


def upgrade(settings: Settings) -> None:
    command.upgrade(migration_config(settings), "head")


if __name__ == "__main__":
    try:
        upgrade(Settings.from_environment())
    except Exception:
        raise SystemExit("Migration failed. Check DATABASE_URL, V4 DB permissions and schema. No credentials logged.") from None
    print("Migration to head completed.")
