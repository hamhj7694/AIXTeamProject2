from alembic import context

from backend.database import database_engine

engine = database_engine(context.config.attributes["settings"])
try:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
finally:
    engine.dispose()
