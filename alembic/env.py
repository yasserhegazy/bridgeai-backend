from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add your app directory to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import your Base and models
from app.db.session import Base  # ✅ Correct path to Base
from app import models            # ✅ Make sure all models are imported so Alembic can see them
from app.core.config import settings  # Import settings to get DATABASE_URL

# Alembic Config object
config = context.config

# Override the sqlalchemy.url with the one from .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Set up Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is what Alembic uses to detect tables
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode'."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
