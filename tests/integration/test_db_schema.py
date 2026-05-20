"""Tests de integracion para el esquema de base de datos.

Validan la estructura del esquema, restricciones, trigger de inmutabilidad
e indices contra un PostgreSQL real con testcontainers compartido (1 contenedor
por sesion de tests).

Los tests que solo verifican estructura (tablas, columnas, indices, ENUMs)
usan ``db_pool`` (session-scoped). Los tests que insertan datos para probar
restricciones usan ``db_clean`` (function-scoped, TRUNCATE + re-seed).

Ejemplo de ejecucion::

    pytest tests/integration/test_db_schema.py -v
"""

from __future__ import annotations

from pathlib import Path

import asyncpg
import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
SEED_FILE = MIGRATIONS_DIR / "007_seed_data.sql"


# ── Tests de existencia de tablas (solo leen metadata, no insertan) ─────


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


# ── Tests de ENUM (solo leen metadata) ──────────────────────────────────


async def test_movement_type_enum_exists(db_pool: asyncpg.Pool) -> None:
    """Verifica que el ENUM movement_type tiene los 4 valores esperados."""
    rows = await db_pool.fetch(
        "SELECT UNNEST(ENUM_RANGE(NULL::movement_type)) AS value"
    )
    values = [r["value"] for r in rows]
    assert values == ["IN", "OUT", "ADJUSTMENT", "TRANSFER"]


# ── Tests de restricciones FK (insertan datos, necesitan estado limpio) ─


async def test_fk_product_category(db_clean: asyncpg.Pool) -> None:
    """Verifica que no se puede crear un producto con categoria
    inexistente."""
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await db_clean.execute(
            "INSERT INTO products (sku, name, category_id) "
            "VALUES ('TEST-001', 'Test Product', 99999)"
        )


async def test_fk_movement_product(db_clean: asyncpg.Pool) -> None:
    """Verifica que no se puede crear un movimiento con producto
    inexistente."""
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await db_clean.execute(
            "INSERT INTO movements (product_id, movement_type, quantity) "
            "VALUES (99999, 'IN', 10)"
        )


# ── Tests de restricciones CHECK (insertan datos) ───────────────────────


async def test_quantity_positive_check(db_clean: asyncpg.Pool) -> None:
    """Verifica que quantity debe ser mayor que cero."""
    with pytest.raises(asyncpg.CheckViolationError):
        await db_clean.execute(
            "INSERT INTO movements (product_id, movement_type, quantity) "
            "VALUES (1, 'IN', 0)"
        )

    with pytest.raises(asyncpg.CheckViolationError):
        await db_clean.execute(
            "INSERT INTO movements (product_id, movement_type, quantity) "
            "VALUES (1, 'IN', -1)"
        )


async def test_min_stock_threshold_non_negative(
    db_clean: asyncpg.Pool,
) -> None:
    """Verifica que min_stock_threshold no puede ser negativo."""
    await db_clean.execute("INSERT INTO categories (name) VALUES ('Test Cat')")
    cat = await db_clean.fetchrow("SELECT id FROM categories WHERE name = 'Test Cat'")
    with pytest.raises(asyncpg.CheckViolationError):
        await db_clean.execute(
            "INSERT INTO products "
            "(sku, name, category_id, min_stock_threshold) "
            "VALUES ('TEST-002', 'Test', $1, -1)",
            cat["id"],
        )


# ── Tests de inmutabilidad (trigger) (insertan datos) ───────────────────


async def _create_test_movement(
    pool: asyncpg.Pool,
    suffix: str = "",
) -> None:
    """Crea categoria, producto y movimiento de prueba."""
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
    db_clean: asyncpg.Pool,
) -> None:
    """Verifica que UPDATE en movements lanza excepcion."""
    await _create_test_movement(db_clean, "UPD")

    with pytest.raises(asyncpg.RaiseError):
        await db_clean.execute("UPDATE movements SET quantity = 999 WHERE id = 1")


async def test_immutability_trigger_blocks_delete(
    db_clean: asyncpg.Pool,
) -> None:
    """Verifica que DELETE en movements lanza excepcion."""
    await _create_test_movement(db_clean, "DEL")

    with pytest.raises(asyncpg.RaiseError):
        await db_clean.execute("DELETE FROM movements WHERE id = 1")


# ── Tests de indices (solo leen metadata) ───────────────────────────────


async def test_composite_index_exists(db_pool: asyncpg.Pool) -> None:
    """Verifica que el indice compuesto existe."""
    rows = await db_pool.fetch(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename = 'movements' "
        "AND indexname = 'ix_movements_product_created'"
    )
    assert len(rows) == 1


async def test_partial_indexes_exist(db_pool: asyncpg.Pool) -> None:
    """Verifica que los 4 indices parciales por movement_type existen."""
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
    """Verifica que el indice FK en products(category_id) existe."""
    rows = await db_pool.fetch(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename = 'products' "
        "AND indexname = 'ix_products_category_id'"
    )
    assert len(rows) == 1


# ── Tests de restricciones UNIQUE (insertan datos) ──────────────────────


async def test_sku_unique_constraint(db_clean: asyncpg.Pool) -> None:
    """Verifica que no se pueden crear dos productos con mismo SKU."""
    await db_clean.execute("INSERT INTO categories (name) VALUES ('Unique Test Cat')")
    cat = await db_clean.fetchrow(
        "SELECT id FROM categories WHERE name = 'Unique Test Cat'"
    )

    await db_clean.execute(
        "INSERT INTO products (sku, name, category_id) "
        "VALUES ('UNIQUE-001', 'Test 1', $1)",
        cat["id"],
    )

    with pytest.raises(asyncpg.UniqueViolationError):
        await db_clean.execute(
            "INSERT INTO products (sku, name, category_id) "
            "VALUES ('UNIQUE-001', 'Test 2', $1)",
            cat["id"],
        )


async def test_category_name_unique_constraint(
    db_clean: asyncpg.Pool,
) -> None:
    """Verifica que no se pueden crear dos categorias con mismo nombre."""
    await db_clean.execute("INSERT INTO categories (name) VALUES ('Unique Cat')")

    with pytest.raises(asyncpg.UniqueViolationError):
        await db_clean.execute("INSERT INTO categories (name) VALUES ('Unique Cat')")


# ── Tests de seed data (insertan datos) ─────────────────────────────────


async def test_seed_data_inserts(db_clean: asyncpg.Pool) -> None:
    """Verifica que el seed data inserta ~10 productos y ~30
    movimientos."""
    if not SEED_FILE.exists():
        pytest.skip("Seed file not found")

    sql = SEED_FILE.read_text(encoding="utf-8")
    await db_clean.execute(sql)

    product_count = await db_clean.fetchval("SELECT COUNT(*) FROM products")
    movement_count = await db_clean.fetchval("SELECT COUNT(*) FROM movements")

    assert product_count >= 10, f"Expected >= 10 products, got {product_count}"
    assert movement_count >= 30, f"Expected >= 30 movements, got {movement_count}"


# ── Tests de run_seed() del modulo seed.py ──────────────────────────────


async def test_run_seed_from_seed_module(db_clean: asyncpg.Pool) -> None:
    """Verifica que run_seed() del modulo seed.py ejecuta correctamente."""
    if not SEED_FILE.exists():
        pytest.skip("Seed file not found")

    from src.infrastructure.db.seed import run_seed

    await run_seed(db_clean)

    product_count = await db_clean.fetchval("SELECT COUNT(*) FROM products")
    assert product_count >= 10, f"Expected >= 10 products, got {product_count}"
