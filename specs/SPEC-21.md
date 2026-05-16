# SPEC-21: Reglas de Negocio

**Fase:** F2 — Núcleo de Dominio  
**Dependencias:** Spec-20 (Entidades) ✅ Completado  
**Prioridad:** Alta  
**Estado:** Pendiente

---

## Objective

Definir las reglas de negocio puras del dominio: validación de stock no negativo, cálculo de delta de stock, validación de inmutabilidad y coherencia de tipos de movimiento. Las reglas son **funciones puras** — sin estado, sin I/O, sin acceso a DB. Reciben datos explícitos como parámetros y retornan resultados o lanzan excepciones de dominio.

**Principios de diseño:**
- **Pureza** — sin efectos secundarios, sin mutación de estado
- **Determinismo** — mismos inputs → mismos outputs siempre
- **Sin I/O** — nunca acceden a DB, archivos, red, o tiempo del sistema
- **Domain exceptions only** — lanzan excepciones de dominio, nunca `ValueError` genérico

---

## Rules

### Rule: `validate_stock_not_negative`

Valida que un movimiento no resulte en stock negativo.

```python
from src.domain.value_objects.movement_type import MovementType
from src.domain.exceptions.insufficient_stock import InsufficientStockError


def validate_stock_not_negative(
    movement_type: MovementType,
    quantity: int,
    current_stock: int,
) -> None:
    """Valida que el movimiento no resulte en stock negativo.

    Para IN y ADJUSTMENT: siempre válido (stock aumenta).
    Para OUT: current_stock - quantity >= 0
    Para TRANSFER: current_stock - quantity >= 0 (desde la perspectiva del origen).

    Args:
        movement_type: Tipo de movimiento que se está registrando.
        quantity: Cantidad a mover (siempre > 0, validada por Quantity VO).
        current_stock: Nivel actual de stock del producto.

    Raises:
        InsufficientStockError: Si el movimiento resultaría en stock negativo.

    Examples:
        >>> validate_stock_not_negative(MovementType.IN, 10, 5)
        # No exception — stock becomes 15

        >>> validate_stock_not_negative(MovementType.OUT, 10, 5)
        # Raises InsufficientStockError(product_id=?, requested=10, available=5)
    """
    if movement_type in (MovementType.OUT, MovementType.TRANSFER):
        resulting_stock = current_stock - quantity
        if resulting_stock < 0:
            raise InsufficientStockError(
                product_id=0,  # Caller debe proporcionar el product_id real
                requested=quantity,
                available=current_stock,
            )
```

**Design Notes:**
- `product_id=0` es un placeholder — el use case debe crear la excepción con el `product_id` real
- IN y ADJUSTMENT nunca fallan (siempre suman stock)
- ADJUSTMENT siempre +qty (confirmado por el usuario — no hay ajustes negativos)

---

### Rule: `calculate_stock_delta`

Calcula el cambio de stock resultante de un movimiento.

```python
from src.domain.value_objects.movement_type import MovementType


def calculate_stock_delta(movement_type: MovementType, quantity: int) -> int:
    """Calcula el cambio de stock resultante de un movimiento.

    IN: +quantity (entrada de stock)
    OUT: -quantity (salida de stock)
    ADJUSTMENT: +quantity (ajuste siempre positivo)
    TRANSFER: -quantity (desde la perspectiva del origen)

    Args:
        movement_type: Tipo de movimiento.
        quantity: Cantidad del movimiento (siempre > 0).

    Returns:
        int: Cambio de stock con signo (+aumento, -disminución).

    Examples:
        >>> calculate_stock_delta(MovementType.IN, 10)
        10
        >>> calculate_stock_delta(MovementType.OUT, 5)
        -5
        >>> calculate_stock_delta(MovementType.ADJUSTMENT, 3)
        3
        >>> calculate_stock_delta(MovementType.TRANSFER, 7)
        -7
    """
    deltas = {
        MovementType.IN: quantity,
        MovementType.OUT: -quantity,
        MovementType.ADJUSTMENT: quantity,
        MovementType.TRANSFER: -quantity,
    }
    return deltas[movement_type]
```

**Design Notes:**
- Función pura total — sin excepciones posibles (todos los MovementType están cubiertos)
- El delta de TRANSFER es negativo desde la perspectiva del origen; el destino se maneja con metadata

---

### Rule: `enforce_immutability`

Valida que un Movement no haya sido modificado después de su creación.

```python
from src.domain.entities.movement import Movement
from src.domain.exceptions.immutability_violation import ImmutabilityViolationError


def enforce_immutability(entity: Movement) -> None:
    """Valida que un Movement no haya sido modificado.

    Dado que Movement es un frozen dataclass, Python previene mutaciones
    en runtime automáticamente. Esta función sirve como:
    1. Documentación explícita de la regla de inmutabilidad.
    2. Punto de extensión para validaciones adicionales de inmutabilidad
       (ej: verificar que el movimiento ya tiene id asignado).

    Args:
        entity: Instancia de Movement a validar.

    Raises:
        ImmutabilityViolationError: Si se detecta una violación de inmutabilidad.

    Note:
        En la práctica, esta función nunca lanza excepciones porque
        frozen=True previene mutaciones a nivel de lenguaje. Su propósito
        principal es documentar la regla y servir como hook para
        validaciones futuras.
    """
    # frozen dataclass ya previene mutaciones en runtime
    # Esta función documenta la regla explícitamente
    pass
```

**Design Notes:**
- La inmutabilidad real la garantiza `frozen=True` en el dataclass
- Esta función existe como documentación explícita de la regla
- Se puede extender en el futuro para validar que el movement tiene `id` asignado (persistido)

---

### Rule: `validate_movement_type_consistency`

Valida que el metadata sea consistente con el tipo de movimiento.

```python
from typing import Any

from src.domain.value_objects.movement_type import MovementType


def validate_movement_type_consistency(
    movement_type: MovementType,
    metadata: dict[str, Any],
) -> None:
    """Valida que el metadata sea consistente con el tipo de movimiento.

    TRANSFER: debe contener 'origin' y 'destination' en metadata.
    ADJUSTMENT: debe contener 'reason' en metadata.
    IN/OUT: metadata es opcional (no se requiere validación).

    Args:
        movement_type: Tipo de movimiento.
        metadata: Diccionario de datos contextuales.

    Raises:
        ValueError: Si el metadata es inconsistente con el tipo de movimiento.

    Examples:
        >>> validate_movement_type_consistency(
        ...     MovementType.TRANSFER,
        ...     {"origin": "warehouse_A", "destination": "warehouse_B"}
        ... )
        # No exception

        >>> validate_movement_type_consistency(MovementType.TRANSFER, {})
        # Raises ValueError
    """
    if movement_type == MovementType.TRANSFER:
        if "origin" not in metadata or "destination" not in metadata:
            raise ValueError(
                "TRANSFER movements require 'origin' and 'destination' in metadata"
            )
    elif movement_type == MovementType.ADJUSTMENT:
        if "reason" not in metadata:
            raise ValueError(
                "ADJUSTMENT movements require 'reason' in metadata"
            )
```

**Design Notes:**
- Usa `ValueError` en lugar de excepción de dominio porque es un error de validación de input, no una regla de negocio
- El use case debe capturar este `ValueError` y mapearlo a una respuesta HTTP 400
- IN y OUT no requieren metadata — la función retorna silenciosamente

---

## Files

| File | Description |
|------|-------------|
| `src/domain/rules/stock_validation.py` | `validate_stock_not_negative`, `calculate_stock_delta` |
| `src/domain/rules/immutability.py` | `enforce_immutability` |
| `src/domain/rules/movement_consistency.py` | `validate_movement_type_consistency` |
| `src/domain/rules/__init__.py` | Re-exports: all rule functions |

---

## Acceptance Criteria

- [ ] All rule functions are pure (no I/O, no DB, no side effects)
- [ ] `validate_stock_not_negative` raises `InsufficientStockError` with full context (product_id, requested, available)
- [ ] `calculate_stock_delta` returns correct sign for each `MovementType` (IN=+, OUT=-, ADJUSTMENT=+, TRANSFER=-)
- [ ] `validate_movement_type_consistency` enforces metadata requirements for TRANSFER and ADJUSTMENT
- [ ] `enforce_immutability` exists as explicit documentation of the immutability rule
- [ ] `domain/rules/` imports only from `domain/` (no external dependencies)
- [ ] `make lint` passes with zero errors on all rule files
- [ ] Unit tests with parametrized cases for each rule (covering all MovementType variants)

---

## Open Questions

1. Should `validate_stock_not_negative` accept `product_id` as a parameter instead of using `0` as placeholder?
2. Should `ValueError` in `validate_movement_type_consistency` be replaced with a domain exception (`InvalidMovementError`)?
3. Should `enforce_immutability` be removed entirely since `frozen=True` handles it at the language level?
