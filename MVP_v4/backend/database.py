from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from backend.config import Settings

CURRENT_SCHEMA_REVISION = "002"


def database_engine(settings: Settings) -> Engine:
    settings.validate_database()
    kwargs = {"connect_args": {"connect_timeout": 3}} if settings.database_url.startswith("mysql+") else {}
    return create_engine(settings.database_url, pool_pre_ping=True, **kwargs)


def database_readiness(settings: Settings) -> str:
    if not settings.database_url:
        return "DATABASE_URL_REQUIRED"
    engine = None
    try:
        engine = database_engine(settings)
        with engine.connect() as connection:
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
            return "ok" if revision == CURRENT_SCHEMA_REVISION else "MIGRATION_REQUIRED"
    except Exception:
        # Never return connection strings, SQL parameter values or driver exceptions.
        return "DATABASE_UNAVAILABLE_OR_UNMIGRATED"
    finally:
        if engine is not None:
            engine.dispose()
