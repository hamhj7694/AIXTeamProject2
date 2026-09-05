from pathlib import Path

import pytest

from backend.config import ROOT, Settings, internal_path


def test_runtime_path_cannot_escape():
    assert internal_path("backend/data/uploads").is_relative_to(ROOT)
    with pytest.raises(ValueError):
        internal_path("../outside")
    with pytest.raises(ValueError):
        internal_path(str(ROOT.parent / "outside"))


@pytest.mark.parametrize("url", ["mysql+pymysql://localhost/legacy", "sqlite:///:memory:", "postgresql://localhost/csr_v4"])
def test_non_v4_database_rejected(url):
    with pytest.raises(ValueError):
        Settings(database_url=url).validate_database()


def test_secret_not_in_settings_repr():
    assert "private-value" not in repr(Settings(database_url="private-value"))


def test_ai_endpoint_is_dedicated_local_service():
    with pytest.raises(ValueError):
        Settings(app_env="production", ai_api_base_url="http://127.0.0.1:8001").validate()


def test_migration_is_repeatable():
    from tempfile import TemporaryDirectory
    from sqlalchemy import text
    from backend.database import database_engine, database_readiness
    from backend.scripts.migrate import upgrade

    (ROOT / ".cache").mkdir(exist_ok=True)
    with TemporaryDirectory(dir=ROOT / ".cache") as directory:
        settings = Settings(app_env="test", database_url=f"sqlite:///{Path(directory).as_posix()}/test.db")
        upgrade(settings)
        upgrade(settings)
        assert database_readiness(settings) == "ok"
        engine = database_engine(settings)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT value FROM application_metadata")).scalar_one() == "csr_v4"
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "003"
        engine.dispose()
