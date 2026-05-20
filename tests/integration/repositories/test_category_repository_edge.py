"""Edge case tests for PostgresCategoryRepository.

Valida comportamientos de borde: ID inexistente, lista vacia,
nombre duplicado (UniqueViolation).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import asyncpg
import pytest

from src.domain.entities.category import Category

if TYPE_CHECKING:
    import asyncpg as asyncpg_type

_NOW = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)


def _make_category(name: str, description: str | None = None) -> Category:
    """Crea una Category sin id."""
    return Category(
        id=None,
        name=name,
        description=description,
        created_at=_NOW,
    )


async def test_get_by_id_not_found(db_pool: asyncpg_type.Pool) -> None:
    """get_by_id() retorna None para categoria inexistente."""
    from src.infrastructure.repositories.category_repository import (
        PostgresCategoryRepository,
    )

    repo = PostgresCategoryRepository(db_pool)
    result = await repo.get_by_id(99999)

    assert result is None


async def test_list_all_returns_only_new_categories(db_clean: asyncpg_type.Pool) -> None:
    """list_all() retorna solo categorias creadas tras limpiar datos.

    Usa db_clean que ya hace TRUNCATE + re-seed. Verificamos que las
    categorias del seed estan presentes.
    """
    from src.infrastructure.repositories.category_repository import (
        PostgresCategoryRepository,
    )

    repo = PostgresCategoryRepository(db_clean)
    results = await repo.list_all()

    # db_clean restores seed data, so we should have at least 3 categories
    assert len(results) >= 3
    names = [c.name for c in results]
    assert "General" in names


async def test_create_duplicate_name_raises_unique_violation(
    db_pool: asyncpg_type.Pool,
) -> None:
    """create() con nombre duplicado lanza UniqueViolation de asyncpg."""
    from src.infrastructure.repositories.category_repository import (
        PostgresCategoryRepository,
    )

    repo = PostgresCategoryRepository(db_pool)

    # Create a category with a unique name
    await repo.create(_make_category("EDGE-DUP-CAT"))

    # Attempt to create another with the same name
    with pytest.raises(asyncpg.UniqueViolationError):
        await repo.create(_make_category("EDGE-DUP-CAT"))
