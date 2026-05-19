"""RecordMovementUseCase — orquesta registro de movimientos de stock.

El caso de uso mas complejo. Verifica existencia del producto, valida
stock para movimientos que reducen inventario (OUT, TRANSFER), valida
consistencia de metadata, y persiste dentro de una transaccion atomica
(Unit of Work).

La validacion de stock se ejecuta dos veces: fail-fast antes del UoW
(sin adquirir connexion) y dentro del UoW (proteccion race conditions).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.domain.rules.movement_consistency import validate_movement_type_consistency
from src.domain.rules.stock_validation import validate_stock_not_negative
from src.domain.value_objects.movement_type import MovementType

if TYPE_CHECKING:
    from src.domain.entities.movement import Movement
    from src.domain.ports.movement_repository import IMovementRepository
    from src.domain.ports.product_repository import IProductRepository
    from src.domain.ports.stock_query_repository import IStockQueryRepository
    from src.domain.ports.unit_of_work import IUnitOfWork


class RecordMovementUseCase:
    """Registra un nuevo movimiento de stock de forma atomica.

    Flujo:
        1. Verificar que el producto existe.
        2. Si el tipo de movimiento es OUT o TRANSFER:
           a. Consultar stock actual del producto.
           b. Validar que el stock no quede negativo.
        3. Validar consistencia de metadata (TRANSFER requiere
           origin/destination, ADJUSTMENT requiere reason).
        4. Construir la entidad Movement.
        5. Persistir dentro de una transaccion (UoW).
        6. Retornar el movimiento persistido.

    Args:
        movement_repo: Repositorio de movimientos.
        product_repo: Repositorio de productos.
        stock_query_repo: Repositorio de consultas de stock.
        unit_of_work: Unit of Work para transacciones atomicas.
    """

    def __init__(
        self,
        movement_repo: IMovementRepository,
        product_repo: IProductRepository,
        stock_query_repo: IStockQueryRepository,
        unit_of_work: IUnitOfWork,
    ) -> None:
        self._movement_repo = movement_repo
        self._product_repo = product_repo
        self._stock_query_repo = stock_query_repo
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        product_id: int,
        movement_type: MovementType,
        quantity: int,
        metadata: dict[str, str],
        reference: str | None = None,
    ) -> Movement:
        """Ejecuta el caso de uso de registro de movimiento.

        Args:
            product_id: ID del producto al que afecta el movimiento.
            movement_type: Tipo de movimiento (IN, OUT, ADJUSTMENT, TRANSFER).
            quantity: Cantidad positiva de unidades.
            metadata: Diccionario contextual (obligatorio para TRANSFER y ADJUSTMENT).
            reference: Referencia externa opcional (orden, nota, etc.).

        Returns:
            Movement: La entidad movimiento persistida con id asignado.

        Raises:
            ValueError: Si el producto no existe.
            ValueError: Si la metadata es inconsistente con el tipo de movimiento.
            InsufficientStockError: Si el movimiento resultaria en stock negativo.
            InvalidQuantityError: Si quantity <= 0 (validado por el VO Quantity).
        """
        # 1. Verificar que el producto existe
        product = await self._product_repo.get_by_id(product_id)
        if product is None:
            raise ValueError(f"Product {product_id} not found")

        # 2. Fail-fast: validar stock antes de adquirir transaccion
        if movement_type in (MovementType.OUT, MovementType.TRANSFER):
            current_stock = await self._stock_query_repo.get_current_stock(product_id)
            validate_stock_not_negative(
                movement_type, quantity, current_stock, product_id
            )

        # 3. Validar consistencia de metadata
        validate_movement_type_consistency(movement_type, metadata)

        # 4. Construir entidad
        from src.domain.entities.movement import Movement
        from src.domain.value_objects.quantity import Quantity

        movement = Movement(
            id=None,
            product_id=product_id,
            movement_type=movement_type,
            quantity=Quantity(quantity),
            metadata=metadata,
            reference=reference,
            created_at=datetime.now(tz=UTC),
        )

        # 5. Persistir dentro de UoW con re-validacion de stock
        async with self._unit_of_work:
            if movement_type in (MovementType.OUT, MovementType.TRANSFER):
                current_stock = await self._stock_query_repo.get_current_stock(
                    product_id
                )
                validate_stock_not_negative(
                    movement_type, quantity, current_stock, product_id
                )

            result = await self._movement_repo.create(movement)

        return result
