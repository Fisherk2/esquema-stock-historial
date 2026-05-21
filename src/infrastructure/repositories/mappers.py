"""Mappers — funciones puras que transforman asyncpg.Record en entidades de dominio.

Cada mapper toma un record (objeto con acceso por clave estilo dict) y
retorna una instancia de entidad de dominio. No tienen estado, no hacen
I/O y son deterministicas — testeables de forma aislada.

La base de datos protege la integridad con CHECK constraints, FK y
triggers; los mappers solo transforman tipos. Si un valor no coincide
con el dominio (ej: movimiento_type no reconocido), se lanza la
excepcion nativa correspondiente.

Ejemplo de uso::

    row = await pool.fetchrow("SELECT * FROM categories WHERE id = $1", 1)
    category = map_category_row(row)
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from src.domain.entities.category import Category
from src.domain.entities.movement import Movement
from src.domain.entities.product import Product
from src.domain.value_objects.movement_type import MovementType
from src.domain.value_objects.quantity import Quantity
from src.domain.value_objects.sku import SKU

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)


def map_category_row(record: asyncpg.Record) -> Category:
    """Transforma un asyncpg.Record en una entidad Category.

    Args:
        record: asyncpg.Record con columnas id, name, description, created_at.

    Returns:
        Category con campos mapeados desde la fila de base de datos.
    """
    return Category(
        id=record["id"],
        name=record["name"],
        description=record["description"],
        created_at=record["created_at"],
    )


def map_product_row(record: asyncpg.Record) -> Product:
    """Transforma un asyncpg.Record en una entidad Product.

    Construye el Value Object SKU desde el string almacenado en DB.

    Args:
        record: asyncpg.Record con columnas id, sku, name, description,
                unit_of_measure, category_id, min_stock_threshold, created_at.

    Returns:
        Product con SKU como Value Object.

    Raises:
        InvalidSKUError: Si el SKU en DB no cumple las reglas de formato.
    """
    return Product(
        id=record["id"],
        sku=SKU(record["sku"]),
        name=record["name"],
        description=record["description"],
        unit_of_measure=record["unit_of_measure"],
        category_id=record["category_id"],
        min_stock_threshold=record["min_stock_threshold"],
        created_at=record["created_at"],
    )


def map_movement_row(record: asyncpg.Record) -> Movement:
    """Transforma un asyncpg.Record en una entidad Movement.

    Parsea el string movement_type al Enum MovementType y construye
    el Value Object Quantity desde el integer almacenado.

    Args:
        record: asyncpg.Record con columnas id, product_id, movement_type,
                quantity, metadata, reference, created_at.

    Returns:
        Movement con tipos de dominio correctos.

    Raises:
        ValueError: Si movement_type no es un valor valido del Enum.
        InvalidQuantityError: Si quantity <= 0 (no deberia ocurrir con
            CHECK constraint).
    """
    metadata_raw = record["metadata"]
    if metadata_raw is None:
        metadata: dict[str, object] = {}
    elif isinstance(metadata_raw, dict):
        metadata = metadata_raw
    else:
        try:
            metadata = json.loads(metadata_raw)
        except json.JSONDecodeError:
            logger.warning(
                "Corrupted metadata for movement id=%s, defaulting to empty dict",
                record.get("id"),
            )
            metadata = {}

    return Movement(
        id=record["id"],
        product_id=record["product_id"],
        movement_type=MovementType(record["movement_type"]),
        quantity=Quantity(record["quantity"]),
        metadata=metadata,
        reference=record["reference"],
        created_at=record["created_at"],
    )
