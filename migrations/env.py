import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Añadir la raíz del proyecto al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Importar Base y todos los modelos
from obtener_datos_clientes.db import Base
from obtener_datos_clientes.models import (
    Cliente,
    Jurisdiccion,
    ClienteJurisdiccion,
    UsuariosAutorizados,
    UsuarioCliente,
    MonitoreoBots,
    ProcesamientosDiariosGlobal,
)

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Configurar la URL de conexión desde .env
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DATABASE_URL")
config.set_main_option("sqlalchemy.url", url)

# Establecer el objetivo de la migración (tus modelos)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=url,
        target_metadata=target_metadata,
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
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
