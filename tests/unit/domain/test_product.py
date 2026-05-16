"""Tests unitarios para la entidad Product.

Valida que ``Product`` tiene los campos esperados y las validaciones
de nombre, umbral minimo y unidad de medida.

Ejemplo::

    pytest tests/unit/domain/test_product.py -v
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest


def _make_product(**overrides: object) -> object:
    """Helper para crear un Product con valores por defecto."""
    from src.domain.entities.product import Product
    from src.domain.value_objects.sku import SKU

    defaults: dict[str, object] = {
        "id": None,
        "sku": SKU("PROD-001"),
        "name": "Test Product",
        "description": None,
        "unit_of_measure": "unit",
        "category_id": 1,
        "min_stock_threshold": 0,
        "created_at": datetime.now(tz=UTC),
    }
    defaults.update(overrides)
    return Product(**defaults)  # type: ignore[arg-type]


class TestProductConstruction:
    """Tests para la construccion de Product."""

    def test_creates_product_with_valid_data(self) -> None:
        """Verifica que Product se crea con datos validos."""
        p = _make_product()
        assert p.name == "Test Product"  # type: ignore[attr-defined]
        assert p.category_id == 1  # type: ignore[attr-defined]

    def test_product_has_all_required_fields(self) -> None:
        """Verifica que Product tiene todos los campos requeridos."""
        p = _make_product()
        assert hasattr(p, "id")  # type: ignore[attr-defined]
        assert hasattr(p, "sku")  # type: ignore[attr-defined]
        assert hasattr(p, "name")  # type: ignore[attr-defined]
        assert hasattr(p, "description")  # type: ignore[attr-defined]
        assert hasattr(p, "unit_of_measure")  # type: ignore[attr-defined]
        assert hasattr(p, "category_id")  # type: ignore[attr-defined]
        assert hasattr(p, "min_stock_threshold")  # type: ignore[attr-defined]
        assert hasattr(p, "created_at")  # type: ignore[attr-defined]


class TestProductValidation:
    """Tests para validaciones de Product."""

    def test_empty_name_raises(self) -> None:
        """Verifica que Product con nombre vacio lanza ValueError."""
        with pytest.raises(ValueError):
            _make_product(name="")

    def test_negative_threshold_raises(self) -> None:
        """Verifica que min_stock_threshold negativo lanza ValueError."""
        with pytest.raises(ValueError):
            _make_product(min_stock_threshold=-1)

    def test_zero_threshold_accepted(self) -> None:
        """Verifica que min_stock_threshold=0 es valido."""
        p = _make_product(min_stock_threshold=0)
        assert p.min_stock_threshold == 0  # type: ignore[attr-defined]

    def test_empty_unit_of_measure_raises(self) -> None:
        """Verifica que unit_of_measure vacio lanza ValueError."""
        with pytest.raises(ValueError):
            _make_product(unit_of_measure="")

    def test_positive_threshold_accepted(self) -> None:
        """Verifica que min_stock_threshold positivo es valido."""
        p = _make_product(min_stock_threshold=10)
        assert p.min_stock_threshold == 10  # type: ignore[attr-defined]

    def test_accepts_optional_description(self) -> None:
        """Verifica que Product acepta descripcion opcional."""
        p = _make_product(description="A test product")
        assert p.description == "A test product"  # type: ignore[attr-defined]
