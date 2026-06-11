"""Alembic migration environment for member-service."""
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.models.member import Base

config = context.config

db_url = os.getenv("DATABASE_URL_SYNC")
if not db_url:
    async_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://library:library@localhost:5432/librarydb")
    db_url = async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata, literal_binds=True,
        version_table_schema="members_db", include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.", poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            version_table_schema="members_db", include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
