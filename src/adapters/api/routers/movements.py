"""Router de movimientos — registro y consulta de movimientos de stock.

Expone endpoints para crear movimientos (entradas, salidas, ajustes,
transferencias) y consultar el historial de movimientos de un producto.

Endpoints:
    POST   /v1/movements                    — Crear movimiento
    GET    /v1/movements/{movement_id}      — Obtener movimiento por ID
    GET    /v1/movements?product_id=&...    — Listar movimientos de un producto
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.adapters.api.dependencies import (
    get_movement_repo,
    get_record_movement_use_case,
)
from src.application.dtos.movement_dtos import (
    CreateMovementInput,
    MovementListOutput,
    MovementOutput,
)
from src.application.use_cases.record_movement import RecordMovementUseCase
from src.domain.ports.movement_repository import IMovementRepository

router = APIRouter(prefix="/movements", tags=["movements"])


@router.post(
    "",
    response_model=MovementOutput,
    status_code=201,
    summary="Crear movimiento de stock",
    description="Registra un nuevo movimiento (IN, OUT, ADJUSTMENT, TRANSFER). "
    "Para OUT y TRANSFER, valida que el stock no quede negativo.",
)
async def create_movement(
    body: CreateMovementInput,
    use_case: Annotated[RecordMovementUseCase, Depends(get_record_movement_use_case)],
) -> MovementOutput:
    """Crea un nuevo movimiento de stock."""
    from src.domain.value_objects.movement_type import MovementType

    movement = await use_case.execute(
        product_id=body.product_id,
        movement_type=MovementType(body.movement_type.value),
        quantity=body.quantity,
        metadata=body.metadata,
        reference=body.reference,
    )
    assert movement.id is not None
    return MovementOutput(
        id=movement.id,
        product_id=movement.product_id,
        movement_type=movement.movement_type.value,
        quantity=movement.quantity.value,  # type: ignore[arg-type]
        metadata=movement.metadata,
        reference=movement.reference,
        created_at=movement.created_at,
    )


@router.get(
    "/{movement_id}",
    response_model=MovementOutput,
    summary="Obtener movimiento por ID",
)
async def get_movement(
    movement_id: int,
    repo: Annotated[IMovementRepository, Depends(get_movement_repo)],
) -> MovementOutput:
    """Recupera un movimiento por su ID."""
    movement = await repo.get_by_id(movement_id)
    if movement is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Movement not found")
    return MovementOutput(
        id=movement.id,  # type: ignore[arg-type]
        product_id=movement.product_id,
        movement_type=movement.movement_type.value,
        quantity=movement.quantity.value,  # type: ignore[arg-type]
        metadata=movement.metadata,
        reference=movement.reference,
        created_at=movement.created_at,
    )


@router.get(
    "",
    response_model=MovementListOutput,
    summary="Listar movimientos de un producto",
)
async def list_movements(
    repo: Annotated[IMovementRepository, Depends(get_movement_repo)],
    product_id: int = Query(description="ID del producto."),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximo de resultados."),
    offset: int = Query(default=0, ge=0, description="Desplazamiento."),
) -> MovementListOutput:
    """Lista movimientos de un producto con paginacion."""
    movements = await repo.list_by_product(product_id, limit=limit, offset=offset)
    total = await repo.count_by_product(product_id)
    return MovementListOutput(
        items=[
            MovementOutput(
                id=m.id,  # type: ignore[arg-type]
                product_id=m.product_id,
                movement_type=m.movement_type.value,
                quantity=m.quantity.value,  # type: ignore[arg-type]
                metadata=m.metadata,
                reference=m.reference,
                created_at=m.created_at,
            )
            for m in movements
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
