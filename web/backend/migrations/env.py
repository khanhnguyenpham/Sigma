from alembic import context
from sqlalchemy import create_engine, pool
import models  # Register both feature modules and remaining domain tables.
from core.settings import Settings

config = context.config
target_metadata = models.Base.metadata
url = config.attributes.get("database_url") or Settings.from_env().database_url

if context.is_offline_mode():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
