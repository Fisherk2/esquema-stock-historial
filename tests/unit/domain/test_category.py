"""Tests unitarios para la entidad Category.

Valida que ``Category`` tiene los campos esperados y la validacion
de nombre no vacio.

Ejemplo::

    pytest tests/unit/domain/test_category.py -v
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest


def _make_category(**overrides: object) -> object:
    """Helper para crear una Category con valores por defecto."""
    from src.domain.entities.category import Category

    defaults: dict[str, object] = {
        "id": None,
        "name": "Electronics",
        "description": None,
        "created_at": datetime.now(tz=UTC),
    }
    defaults.update(overrides)
    return Category(**defaults)  # type: ignore[arg-type]


class TestCategoryConstruction:
    """Tests para la construccion de Category."""

    def test_creates_category_with_valid_data(self) -> None:
        """Verifica que Category se crea con datos validos."""
        c = _make_category()
        assert c.name == "Electronics"  # type: ignore[attr-defined]

    def test_category_has_all_required_fields(self) -> None:
        """Verifica que Category tiene todos los campos requeridos."""
        c = _make_category()
        assert hasattr(c, "id")  # type: ignore[attr-defined]
        assert hasattr(c, "name")  # type: ignore[attr-defined]
        assert hasattr(c, "description")  # type: ignore[attr-defined]
        assert hasattr(c, "created_at")  # type: ignore[attr-defined]

    def test_empty_name_raises(self) -> None:
        """Verifica que Category con nombre vacio lanza ValueError."""
        with pytest.raises(ValueError):
            _make_category(name="")

    def test_accepts_optional_description(self) -> None:
        """Verifica que Category acepta descripcion opcional."""
        c = _make_category(description="Tech products")
        assert c.description == "Tech products"  # type: ignore[attr-defined]
