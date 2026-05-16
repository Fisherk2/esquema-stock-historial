"""Ejecutor de datos de prueba (seed data).

Inserta datos de ejemplo en la base de datos para desarrollo y pruebas
manuales. Se ejecuta de forma **manual** (``make seed``), nunca automática
al levantar Docker.

El script lee y ejecuta ``migrations/007_seed_data.sql``, que contiene
inserciones idempotentes (ON CONFLICT DO NOTHING).

Ejemplo de uso::

    # Desde línea de comandos
    python -m src.infrastructure.db.seed

    # Programáticamente con un pool existente
    from src.infrastructure.db.seed import run_seed

    await run_seed(pool)
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

# Ruta al archivo de seed data relativo al root del proyecto
SEED_FILE = Path(__file__).resolve().parents[3] / "migrations" / "007_seed_data.sql"


async def run_seed(pool: asyncpg.Pool) -> None:
    """Ejecuta el script de seed data contra la base de datos.

    Lee el archivo ``007_seed_data.sql`` y lo ejecuta dentro de una
    transacción. El SQL es idempotente (ON CONFLICT DO NOTHING), por
    lo que re-ejecutar es seguro.

    Args:
        pool: Pool de conexiones asyncpg activo.

    Raises:
        FileNotFoundError: Si el archivo de seed data no existe.
    """
    if not SEED_FILE.exists():
        raise FileNotFoundError(f"Seed file not found: {SEED_FILE}")

    sql = SEED_FILE.read_text(encoding="utf-8")

    async with pool.acquire() as conn, conn.transaction():
        await conn.execute(sql)

    logger.info("Seed data executed successfully")


async def run_seed_from_settings() -> None:
    """Ejecuta seed data creando un pool temporal desde Settings.

    Función de conveniencia para ejecución independiente (CLI). Crea un
    pool, ejecuta el seed y cierra el pool.

    Ejemplo::

        from src.infrastructure.db.seed import run_seed_from_settings

        await run_seed_from_settings()
    """
    settings = Settings()
    await init_pool(settings)

    from src.infrastructure.db.connection import get_pool

    pool = await get_pool()
    if pool is None:
        raise RuntimeError("Database pool not initialized")

    try:
        await run_seed(pool)
    finally:
        await close_pool()


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_seed_from_settings())
