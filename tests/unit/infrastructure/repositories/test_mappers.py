"""Unit tests for mapper functions — pure functions with no I/O.

Valida que las funciones de mapeo transforman correctly un
asyncpg.Record-like en entidades de dominio. Se usa un mock simple
con __getitem__ para simular el comportamiento de asyncpg.Record.

Ejemplo de ejecución::

    pytest tests/unit/infrastructure/repositories/test_mappers.py -v
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from src.domain.entities.category import Category
from src.domain.entities.movement import Movement
from src.domain.entities.product import Product
from src.domain.exceptions.invalid_sku import InvalidSKUError
from src.domain.value_objects.movement_type import MovementType
from src.domain.value_objects.quantity import Quantity
from src.domain.value_objects.sku import SKU


class FakeRecord:
    """Mock que simula el acceso por clave de asyncpg.Record."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]


# ── Helpers ──────────────────────────────────────────────────────────────

_NOW = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)


def _make_category_row(**overrides: Any) -> FakeRecord:
    return FakeRecord(
        {
            "id": 1,
            "name": "Electronics",
            "description": "Electronic products",
            "created_at": _NOW,
            **overrides,
        }
    )


def _make_product_row(**overrides: Any) -> FakeRecord:
    return FakeRecord(
        {
            "id": 1,
            "sku": "PROD-001",
            "name": "Laptop",
            "description": "A nice laptop",
            "unit_of_measure": "unit",
            "category_id": 1,
            "min_stock_threshold": 5,
            "created_at": _NOW,
            **overrides,
        }
    )


def _make_movement_row(**overrides: Any) -> FakeRecord:
    return FakeRecord(
        {
            "id": 1,
            "product_id": 10,
            "movement_type": "IN",
            "quantity": 50,
            "metadata": {"warehouse": "A"},
            "reference": "PO-123",
            "created_at": _NOW,
            **overrides,
        }
    )


# ── map_category_row ─────────────────────────────────────────────────────


def test_map_category_row_valid_record() -> None:
    """Un record válido se transforma en una Category con campos correctos."""
    from src.infrastructure.repositories.mappers import map_category_row

    row = _make_category_row()
    result = map_category_row(row)

    assert isinstance(result, Category)
    assert result.id == 1
    assert result.name == "Electronics"
    assert result.description == "Electronic products"
    assert result.created_at == _NOW


def test_map_category_row_null_description() -> None:
    """description = None se mapea como None."""
    from src.infrastructure.repositories.mappers import map_category_row

    row = _make_category_row(description=None)
    result = map_category_row(row)

    assert result.description is None


# ── map_product_row ──────────────────────────────────────────────────────


def test_map_product_row_valid_record() -> None:
    """Un record válido se transforma en un Product con SKU como VO."""
    from src.infrastructure.repositories.mappers import map_product_row

    row = _make_product_row()
    result = map_product_row(row)

    assert isinstance(result, Product)
    assert result.id == 1
    assert isinstance(result.sku, SKU)
    assert result.sku.value == "PROD-001"
    assert result.name == "Laptop"
    assert result.description == "A nice laptop"
    assert result.unit_of_measure == "unit"
    assert result.category_id == 1
    assert result.min_stock_threshold == 5
    assert result.created_at == _NOW


def test_map_product_row_invalid_sku_raises() -> None:
    """SKU con formato inválido lanza InvalidSKUError."""
    from src.infrastructure.repositories.mappers import map_product_row

    row = _make_product_row(sku="")  # empty → invalid
    with pytest.raises(InvalidSKUError):
        map_product_row(row)


# ── map_movement_row ─────────────────────────────────────────────────────


def test_map_movement_row_valid_record() -> None:
    """Un record válido se transforma en un Movement con tipos correctos."""
    from src.infrastructure.repositories.mappers import map_movement_row

    row = _make_movement_row()
    result = map_movement_row(row)

    assert isinstance(result, Movement)
    assert result.id == 1
    assert result.product_id == 10
    assert isinstance(result.movement_type, MovementType)
    assert result.movement_type == MovementType.IN
    assert isinstance(result.quantity, Quantity)
    assert result.quantity.value == 50
    assert result.metadata == {"warehouse": "A"}
    assert result.reference == "PO-123"
    assert result.created_at == _NOW


def test_map_movement_row_metadata_none_defaults_to_empty_dict() -> None:
    """metadata = None se convierte en dict vacío."""
    from src.infrastructure.repositories.mappers import map_movement_row

    row = _make_movement_row(metadata=None)
    result = map_movement_row(row)

    assert result.metadata == {}


def test_map_movement_row_invalid_type_raises_value_error() -> None:
    """movement_type no reconocido lanza ValueError (Enum nativo)."""
    from src.infrastructure.repositories.mappers import map_movement_row

    row = _make_movement_row(movement_type="INVALID_TYPE")
    with pytest.raises(ValueError):
        map_movement_row(row)


def test_map_movement_row_all_movement_types() -> None:
    """Los 4 tipos de movimiento se mapean correctamente."""
    from src.infrastructure.repositories.mappers import map_movement_row

    for type_value in ("IN", "OUT", "ADJUSTMENT", "TRANSFER"):
        row = _make_movement_row(
            movement_type=type_value,
            metadata={"origin": "A", "destination": "B", "reason": "test"},
        )
        result = map_movement_row(row)
        assert result.movement_type == MovementType(type_value)
