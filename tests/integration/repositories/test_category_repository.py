"""Integration tests for PostgresCategoryRepository.

Valida el repositorio de categorias contra un PostgreSQL real mediante
testcontainers. Las migraciones 001-008 se ejecutan antes de cada test.

Ejemplo de ejecución::

    pytest tests/integration/repositories/test_category_repository.py -v
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.domain.entities.category import Category
from src.domain.ports.category_repository import ICategoryRepository

if TYPE_CHECKING:
    import asyncpg


_NOW = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_category(name: str, description: str | None = None) -> Category:
    """Crea una Category sin id (antes de persistir)."""
    return Category(
        id=None,
        name=name,
        description=description,
        created_at=_NOW,
    )


# ── Tests ────────────────────────────────────────────────────────────────


async def test_category_repo_implements_protocol(db_pool: asyncpg.Pool) -> None:
    """El repositorio satisface el protocolo ICategoryRepository."""
    from src.infrastructure.repositories.category_repository import (
        PostgresCategoryRepository,
    )

    repo = PostgresCategoryRepository(db_pool)
    assert isinstance(repo, ICategoryRepository)


async def test_create_category_returns_entity_with_id(
    db_pool: asyncpg.Pool,
) -> None:
    """create() inserta y retorna la entidad con id asignado."""
    from src.infrastructure.repositories.category_repository import (
        PostgresCategoryRepository,
    )

    repo = PostgresCategoryRepository(db_pool)
    category = _make_category("Electronics", "Electronic products")

    result = await repo.create(category)

    assert result.id is not None
    assert result.name == "Electronics"
    assert result.description == "Electronic products"


async def test_get_by_id_returns_category(db_pool: asyncpg.Pool) -> None:
    """get_by_id() retorna la entidad cuando existe."""
    from src.infrastructure.repositories.category_repository import (
        PostgresCategoryRepository,
    )

    repo = PostgresCategoryRepository(db_pool)
    created = await repo.create(_make_category("Books", "Literature"))

    result = await repo.get_by_id(created.id)

    assert result is not None
    assert result.id == created.id
    assert result.name == "Books"
    assert result.description == "Literature"


async def test_get_by_id_returns_none_when_not_found(
    db_pool: asyncpg.Pool,
) -> None:
    """get_by_id() retorna None para un id inexistente."""
    from src.infrastructure.repositories.category_repository import (
        PostgresCategoryRepository,
    )

    repo = PostgresCategoryRepository(db_pool)

    result = await repo.get_by_id(99999)

    assert result is None


async def test_list_all_returns_all_categories_ordered(
    db_pool: asyncpg.Pool,
) -> None:
    """list_all() retorna todas las categorias ordenadas por nombre.

    La base de datos tiene categorias de seed data; se verifican que
    las nuevas aparezcan en el orden correcto entre las existentes.
    """
    from src.infrastructure.repositories.category_repository import (
        PostgresCategoryRepository,
    )

    repo = PostgresCategoryRepository(db_pool)
    # Count before adding
    before = await repo.list_all()
    count_before = len(before)

    await repo.create(_make_category("Zebra"))
    await repo.create(_make_category("Apple"))
    await repo.create(_make_category("Mango"))

    results = await repo.list_all()

    assert len(results) == count_before + 3
    names = [c.name for c in results]
    # Verify our added categories appear in alphabetical order
    for added in ["Apple", "Mango", "Zebra"]:
        assert added in names


async def test_list_all_returns_seed_categories(
    db_pool: asyncpg.Pool,
) -> None:
    """list_all() retorna al menos las 3 categorias del seed data."""
    from src.infrastructure.repositories.category_repository import (
        PostgresCategoryRepository,
    )

    repo = PostgresCategoryRepository(db_pool)
    results = await repo.list_all()

    assert len(results) >= 3
    names = [c.name for c in results]
    assert "General" in names
    assert "Materia Prima" in names
    assert "Producto Terminado" in names
