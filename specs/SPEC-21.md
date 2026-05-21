# SPEC-21: Reglas de Negocio

**Phase:** F2 — Domain Core
**Dependencies:** Spec-20 (Entities) ✅ Completed
**Priority:** High
**Status:** Pending

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

Validates that a movement does not result in negative stock.

```python
from src.domain.value_objects.movement_type import MovementType
from src.domain.exceptions.insufficient_stock import InsufficientStockError


def validate_stock_not_negative(
    movement_type: MovementType,
    quantity: int,
    current_stock: int,
) -> None:
    """Validates that the movement does not result in negative stock.

    For IN and ADJUSTMENT: always valid (stock increases).
    For OUT: current_stock - quantity >= 0
    For TRANSFER: current_stock - quantity >= 0 (from origin perspective).

    Args:
        movement_type: Type of movement being registered.
        quantity: Quantity to move (always > 0, validated by Quantity VO).
        current_stock: Current stock level of the product.

    Raises:
        InsufficientStockError: If the movement would result in negative stock.

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
- `product_id=0` is a placeholder — the use case must create the exception with the real `product_id`
- IN and ADJUSTMENT never fail (always add stock)
- ADJUSTMENT always +qty (confirmed by user — no negative adjustments)

---

### Rule: `calculate_stock_delta`

Calculates the stock change resulting from a movement.

```python
from src.domain.value_objects.movement_type import MovementType


def calculate_stock_delta(movement_type: MovementType, quantity: int) -> int:
    """Calculates the stock change resulting from a movement.

    IN: +quantity (stock entry)
    OUT: -quantity (stock exit)
    ADJUSTMENT: +quantity (always positive adjustment)
    TRANSFER: -quantity (from origin perspective)

    Args:
        movement_type: Tipo de movimiento.
        quantity: Cantidad del movimiento (siempre > 0).

    Returns:
        int: Stock change with sign (+increase, -decrease).

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
- Total pure function — no possible exceptions (all MovementType covered)
- TRANSFER delta is negative from origin perspective; destination is handled via metadata

---

### Rule: `enforce_immutability`

Validates that a Movement has not been modified after its creation.

```python
from src.domain.entities.movement import Movement
from src.domain.exceptions.immutability_violation import ImmutabilityViolationError


def enforce_immutability(entity: Movement) -> None:
    """Validates that a Movement has not been modified.

    Since Movement is a frozen dataclass, Python prevents mutations
    at runtime automatically. This function serves as:
    1. Explicit documentation of the immutability rule.
    2. Extension point for additional immutability validations
       (e.g., verifying that the movement already has an id assigned).

    Args:
        entity: Movement instance to validate.

    Raises:
        ImmutabilityViolationError: If an immutability violation is detected.

    Note:
        In practice, this function never raises exceptions because
        frozen=True prevents mutations at the language level. Its main
        purpose is to document the rule and serve as a hook for
        future validations.
    """
    # frozen dataclass already prevents mutations at runtime
    # This function explicitly documents the rule
    pass
```

**Design Notes:**
- Real immutability is guaranteed by `frozen=True` on the dataclass
- This function exists as explicit documentation of the rule
- Can be extended in the future to validate that the movement has an assigned `id` (persisted)

---

### Rule: `validate_movement_type_consistency`

Validates that metadata is consistent with the movement type.

> **Note:** This function is called from `Movement.__post_init__` when building
> the entity. It is the **single source of truth** for this validation.
> Use cases do NOT call this function directly (avoids duplication).

```python
from typing import Any

from src.domain.value_objects.movement_type import MovementType


def validate_movement_type_consistency(
    movement_type: MovementType,
    metadata: dict[str, Any],
) -> None:
    """Validates that metadata is consistent with the movement type.

    TRANSFER: must contain 'origin' and 'destination' in metadata.
    ADJUSTMENT: must contain 'reason' in metadata.
    IN/OUT: metadata is optional (no validation required).

    Args:
        movement_type: Movement type.
        metadata: Dictionary of contextual data.

    Raises:
        ValueError: If metadata is inconsistent with the movement type.
    """
    if movement_type == MovementType.TRANSFER and (
        "origin" not in metadata or "destination" not in metadata
    ):
        raise ValueError("TRANSFER requires 'origin' and 'destination' in metadata")
    elif movement_type == MovementType.ADJUSTMENT and "reason" not in metadata:
        raise ValueError("ADJUSTMENT requires 'reason' in metadata")
```

**Design Notes:**
- Called from `Movement.__post_init__` — **single source of truth**
- Uses `ValueError` because it's an input validation error (not a business rule)
- Mutually exclusive conditions use `elif` (not two independent `if`s)
- IN and OUT do not require metadata — the function returns silently

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
- [ ] `validate_movement_type_consistency` is called from `Movement.__post_init__` (single source of truth)
- [ ] `enforce_immutability` exists as explicit documentation of the immutability rule
- [ ] `domain/rules/` imports only from `domain/` (no external dependencies)
- [ ] Use cases do NOT call `validate_movement_type_consistency` directly (avoids duplication)
- [ ] `make lint` passes with zero errors on all rule files
- [ ] Unit tests with parametrized cases for each rule (covering all MovementType variants)

---

## Open Questions

1. Should `validate_stock_not_negative` accept `product_id` as a parameter instead of using `0` as placeholder?
2. ~~Should `ValueError` in `validate_movement_type_consistency` be replaced with a domain exception?~~ → **Resolved:** Keep `ValueError` because it's input validation. Called from `Movement.__post_init__` as single source of truth.
3. ~~Should `enforce_immutability` be removed entirely?~~ → **Resolved:** Kept as explicit documentation of the rule.
