"""Ejecutor de migraciones SQL.

Descubre y ejecuta archivos de migración en orden numérico contra PostgreSQL.
Cada migración se rastrea en la tabla ``schema_migrations`` para garantizar
idempotencia: re-ejecutar el script omite migraciones ya aplicadas.

Ejemplo de uso::

    # Desde línea de comandos
    python -m src.infrastructure.db.migrate

    # Programáticamente con un pool existente
    from src.infrastructure.db.connection import get_pool
    from src.infrastructure.db.migrate import run_migrations

    pool = await get_pool()
    await run_migrations(pool)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg

from src.core.config import Settings
from src.infrastructure.db.connection import close_pool, init_pool

logger = logging.getLogger(__name__)

# Ruta al directorio de migraciones relativo al root del proyecto
MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "migrations"


async def _ensure_migrations_table(pool: asyncpg.Pool) -> None:
    """Crea la tabla de rastreo de migraciones si no existe.

    La tabla ``schema_migrations`` registra cada migración aplicada con su
    nombre y timestamp de aplicación.

    Args:
        pool: Pool de conexiones asyncpg activo.
    """
    await pool.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)


async def _get_applied_versions(pool: asyncpg.Pool) -> set[str]:
    """Obtiene el conjunto de versiones de migraciones ya aplicadas.

    Args:
        pool: Pool de conexiones asyncpg activo.

    Returns:
        set[str]: Nombres de archivo de migraciones aplicadas (sin .sql).
    """
    rows = await pool.fetch("SELECT version FROM schema_migrations ORDER BY version")
    return {row["version"] for row in rows}


async def run_migrations(pool: asyncpg.Pool) -> list[str]:
    """Ejecuta todas las migraciones pendientes en orden numérico.

    Lee los archivos ``.sql`` del directorio ``migrations/``, los ordena
    por nombre y ejecuta cada uno dentro de una transacción si no ha sido
    aplicado previamente.

    Args:
        pool: Pool de conexiones asyncpg activo.

    Returns:
        list[str]: Lista de migraciones aplicadas en esta ejecución.

    Raises:
        FileNotFoundError: Si el directorio de migraciones no existe.
    """
    if not MIGRATIONS_DIR.exists():
        raise FileNotFoundError(f"Migrations directory not found: {MIGRATIONS_DIR}")

    await _ensure_migrations_table(pool)
    applied = await _get_applied_versions(pool)

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    applied_this_run: list[str] = []

    for migration_file in migration_files:
        version = migration_file.stem  # nombre sin extensión .sql

        if version in applied:
            logger.info("Skipping already applied migration: %s", version)
            continue

        logger.info("Applying migration: %s", version)
        sql = migration_file.read_text(encoding="utf-8")

        # Ejecutar dentro de una transacción para atomicidad
        async with pool.acquire() as conn, conn.transaction():
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO schema_migrations (version) VALUES ($1)",
                version,
            )

        applied_this_run.append(version)
        logger.info("Migration applied successfully: %s", version)

    if not applied_this_run:
        logger.info("No pending migrations. Database is up to date.")
    else:
        logger.info(
            "Applied %d migration(s): %s",
            len(applied_this_run),
            ", ".join(applied_this_run),
        )

    return applied_this_run


async def run_migrations_from_settings() -> list[str]:
    """Ejecuta migraciones creando un pool temporal desde Settings.

    Función de conveniencia para ejecución independiente (CLI). Crea un pool,
    ejecuta las migraciones y cierra el pool.

    Returns:
        list[str]: Lista de migraciones aplicadas en esta ejecución.
    """
    settings = Settings()
    await init_pool(settings)

    pool = await _get_pool_or_raise()
    try:
        return await run_migrations(pool)
    finally:
        await close_pool()


async def _get_pool_or_raise() -> asyncpg.Pool:
    """Obtiene el pool activo o lanza RuntimeError si no está inicializado.

    Returns:
        asyncpg.Pool: Pool de conexiones activo.

    Raises:
        RuntimeError: Si el pool no ha sido inicializado.
    """
    from src.infrastructure.db.connection import get_pool

    pool = await get_pool()
    if pool is None:
        raise RuntimeError("Database pool not initialized")
    return pool


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_migrations_from_settings())
