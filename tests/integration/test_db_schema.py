"""Tests de integración para el esquema de base de datos.

Validan la estructura del esquema, restricciones, trigger de inmutabilidad
e índices contra un PostgreSQL real mediante testcontainers.

Cada test usa un contenedor aislado que se crea y destruye automáticamente.
Las migraciones se ejecutan en el fixture ``db_pool`` antes de cada test.

Ejemplo de ejecución::

    pytest tests/integration/test_db_schema.py -v
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer

from src.infrastructure.db.migrate import run_migrations

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
SEED_FILE = MIGRATIONS_DIR / "007_seed_data.sql"


@pytest.fixture
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Fixture que crea un PostgreSQL aislado, ejecuta migraciones y limpia.

    Usa testcontainers para levantar un contenedor PostgreSQL 16, crea un
    pool de conexiones asyncpg, ejecuta todas las migraciones y devuelve
    el pool. Al finalizar el test, cierra el pool y el contenedor.

    Yields:
        asyncpg.Pool: Pool de conexiones con migraciones aplicadas.
    """
    with PostgresContainer("postgres:16-alpine") as postgres:
        dsn = postgres.get_connection_url()
        # testcontainers returns postgresql+psycopg2:// but asyncpg needs
        # postgresql://
        dsn = dsn.replace("postgresql+psycopg2://", "postgresql://")
        pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)

        try:
            await run_migrations(pool)
            yield pool
        finally:
            await pool.close()


# ── Tests de existencia de tablas ──────────────────────────────────────


async def test_categories_table_exists(db_pool: asyncpg.Pool) -> None:
    """Verifica que la tabla categories existe y tiene las columnas
    esperadas."""
    row = await db_pool.fetchrow(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'categories' ORDER BY ordinal_position"
    )
    assert row is not None, "Table 'categories' does not exist"

    columns = await db_pool.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'categories' ORDER BY ordinal_position"
    )
    column_names = [c["column_name"] for c in columns]
    assert column_names == ["id", "name", "description", "created_at"]


async def test_products_table_exists(db_pool: asyncpg.Pool) -> None:
    """Verifica que la tabla products existe y tiene las columnas
    esperadas."""
    columns = await db_pool.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'products' ORDER BY ordinal_position"
    )
    column_names = [c["column_name"] for c in columns]
    expected = [
        "id",
        "sku",
        "name",
        "description",
        "unit_of_measure",
        "category_id",
        "min_stock_threshold",
        "created_at",
    ]
    assert column_names == expected


async def test_movements_table_exists(db_pool: asyncpg.Pool) -> None:
    """Verifica que la tabla movements existe y tiene las columnas
    esperadas."""
    columns = await db_pool.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'movements' ORDER BY ordinal_position"
    )
    column_names = [c["column_name"] for c in columns]
    expected = [
        "id",
        "product_id",
        "movement_type",
        "quantity",
        "metadata",
        "reference",
        "created_at",
    ]
    assert column_names == expected


# ── Tests de ENUM ──────────────────────────────────────────────────────


async def test_movement_type_enum_exists(db_pool: asyncpg.Pool) -> None:
    """Verifica que el ENUM movement_type tiene los 4 valores esperados."""
    rows = await db_pool.fetch(
        "SELECT UNNEST(ENUM_RANGE(NULL::movement_type)) AS value"
    )
    values = [r["value"] for r in rows]
    assert values == ["IN", "OUT", "ADJUSTMENT", "TRANSFER"]


# ── Tests de restricciones FK ─────────────────────────────────────────


async def test_fk_product_category(db_pool: asyncpg.Pool) -> None:
    """Verifica que no se puede crear un producto con categoría
    inexistente."""
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await db_pool.execute(
            "INSERT INTO products (sku, name, category_id) "
            "VALUES ('TEST-001', 'Test Product', 99999)"
        )


async def test_fk_movement_product(db_pool: asyncpg.Pool) -> None:
    """Verifica que no se puede crear un movimiento con producto
    inexistente."""
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await db_pool.execute(
            "INSERT INTO movements (product_id, movement_type, quantity) "
            "VALUES (99999, 'IN', 10)"
        )


# ── Tests de restricciones CHECK ───────────────────────────────────────


async def test_quantity_positive_check(db_pool: asyncpg.Pool) -> None:
    """Verifica que quantity debe ser mayor que cero."""
    with pytest.raises(asyncpg.CheckViolationError):
        await db_pool.execute(
            "INSERT INTO movements (product_id, movement_type, quantity) "
            "VALUES (1, 'IN', 0)"
        )

    with pytest.raises(asyncpg.CheckViolationError):
        await db_pool.execute(
            "INSERT INTO movements (product_id, movement_type, quantity) "
            "VALUES (1, 'IN', -1)"
        )


async def test_min_stock_threshold_non_negative(
    db_pool: asyncpg.Pool,
) -> None:
    """Verifica que min_stock_threshold no puede ser negativo."""
    await db_pool.execute("INSERT INTO categories (name) VALUES ('Test Cat')")
    cat = await db_pool.fetchrow("SELECT id FROM categories WHERE name = 'Test Cat'")
    with pytest.raises(asyncpg.CheckViolationError):
        await db_pool.execute(
            "INSERT INTO products "
            "(sku, name, category_id, min_stock_threshold) "
            "VALUES ('TEST-002', 'Test', $1, -1)",
            cat["id"],
        )


# ── Tests de inmutabilidad (trigger) ───────────────────────────────────


async def _create_test_movement(
    pool: asyncpg.Pool,
    suffix: str = "",
) -> None:
    """Crea categoría, producto y movimiento de prueba."""
    cat_name = f"Trigger Test Cat {suffix}"
    await pool.execute("INSERT INTO categories (name) VALUES ($1)", cat_name)
    cat = await pool.fetchrow("SELECT id FROM categories WHERE name = $1", cat_name)
    sku = f"TRIGGER-{suffix}"
    await pool.execute(
        "INSERT INTO products (sku, name, category_id) " "VALUES ($1, 'Test', $2)",
        sku,
        cat["id"],
    )
    prod = await pool.fetchrow("SELECT id FROM products WHERE sku = $1", sku)
    await pool.execute(
        "INSERT INTO movements "
        "(product_id, movement_type, quantity) "
        "VALUES ($1, 'IN', 10)",
        prod["id"],
    )


async def test_immutability_trigger_blocks_update(
    db_pool: asyncpg.Pool,
) -> None:
    """Verifica que UPDATE en movements lanza excepción."""
    await _create_test_movement(db_pool, "UPD")

    with pytest.raises(asyncpg.RaiseError):
        await db_pool.execute("UPDATE movements SET quantity = 999 WHERE id = 1")


async def test_immutability_trigger_blocks_delete(
    db_pool: asyncpg.Pool,
) -> None:
    """Verifica que DELETE en movements lanza excepción."""
    await _create_test_movement(db_pool, "DEL")

    with pytest.raises(asyncpg.RaiseError):
        await db_pool.execute("DELETE FROM movements WHERE id = 1")


# ── Tests de índices ───────────────────────────────────────────────────


async def test_composite_index_exists(db_pool: asyncpg.Pool) -> None:
    """Verifica que el índice compuesto existe."""
    rows = await db_pool.fetch(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename = 'movements' "
        "AND indexname = 'ix_movements_product_created'"
    )
    assert len(rows) == 1


async def test_partial_indexes_exist(db_pool: asyncpg.Pool) -> None:
    """Verifica que los 4 índices parciales por movement_type existen."""
    expected = [
        "ix_movements_type_in",
        "ix_movements_type_out",
        "ix_movements_type_adjustment",
        "ix_movements_type_transfer",
    ]
    for name in expected:
        rows = await db_pool.fetch(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'movements' "
            "AND indexname = $1",
            name,
        )
        assert len(rows) == 1, f"Index {name} not found"


async def test_fk_index_on_products_category(
    db_pool: asyncpg.Pool,
) -> None:
    """Verifica que el índice FK en products(category_id) existe."""
    rows = await db_pool.fetch(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename = 'products' "
        "AND indexname = 'ix_products_category_id'"
    )
    assert len(rows) == 1


# ── Tests de restricciones UNIQUE ──────────────────────────────────────


async def test_sku_unique_constraint(db_pool: asyncpg.Pool) -> None:
    """Verifica que no se pueden crear dos productos con mismo SKU."""
    await db_pool.execute("INSERT INTO categories (name) VALUES ('Unique Test Cat')")
    cat = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'Unique Test Cat'"
    )

    await db_pool.execute(
        "INSERT INTO products (sku, name, category_id) "
        "VALUES ('UNIQUE-001', 'Test 1', $1)",
        cat["id"],
    )

    with pytest.raises(asyncpg.UniqueViolationError):
        await db_pool.execute(
            "INSERT INTO products (sku, name, category_id) "
            "VALUES ('UNIQUE-001', 'Test 2', $1)",
            cat["id"],
        )


async def test_category_name_unique_constraint(
    db_pool: asyncpg.Pool,
) -> None:
    """Verifica que no se pueden crear dos categorías con mismo nombre."""
    await db_pool.execute("INSERT INTO categories (name) VALUES ('Unique Cat')")

    with pytest.raises(asyncpg.UniqueViolationError):
        await db_pool.execute("INSERT INTO categories (name) VALUES ('Unique Cat')")


# ── Tests de seed data ─────────────────────────────────────────────────


async def test_seed_data_inserts(db_pool: asyncpg.Pool) -> None:
    """Verifica que el seed data inserta ~10 productos y ~30
    movimientos."""
    if not SEED_FILE.exists():
        pytest.skip("Seed file not found")

    sql = SEED_FILE.read_text(encoding="utf-8")
    await db_pool.execute(sql)

    product_count = await db_pool.fetchval("SELECT COUNT(*) FROM products")
    movement_count = await db_pool.fetchval("SELECT COUNT(*) FROM movements")

    assert product_count >= 10, f"Expected >= 10 products, got {product_count}"
    assert movement_count >= 30, f"Expected >= 30 movements, got {movement_count}"
