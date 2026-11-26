
import os

from dotenv import load_dotenv

load_dotenv()

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Try .env.local first, then .env
if os.path.exists('.env.local'):
    load_dotenv('.env.local')
else:
    load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)


from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from database.pg_models import Base  # Import your models here

target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    """What `alembic revision --autogenerate` may touch.

    A table that is in the database but not in our models (reflected, with
    nothing to compare to) belongs to someone else, e.g. the waitlist app's
    `waitlist` table, which shares this database. Autogenerate must never
    write a DROP for it: migration cf2b1944f856 did exactly that. Our own
    tables are unaffected."""
    return not (type_ == "table" and reflected and compare_to is None)


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, include_object=include_object
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
