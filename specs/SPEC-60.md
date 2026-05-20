# SPEC-60: Tests Unitarios — Hypothesis + mypy strict

**Fase:** F6 — Testing Integral
**Dependencias:** Spec-21 (Reglas de Negocio) ✅ Completado, Spec-22 (Protocolos) ✅ Completado, Spec-40 (Casos de Uso) ✅ Completado
**Prioridad:** Alta
**Estado:** Aprobado

---

## Objective

Consolidar y expandir la suite de tests unitarios existente (194 tests) con tres objetivos: (1) añadir **property-based testing** con Hypothesis para domain rules y value objects, capturando edge cases que los tests example-based no detectan; (2) activar **mypy `--strict`** como quality gate de CI, elevando la seguridad de tipos en `src/`; (3) cerrar brechas de cobertura para alcanzar ≥90% en `domain/` y ≥85% en `application/`.

**Principios de diseño:**
- **Hypothesis como complemento, no reemplazo** — los tests example-based existentes se mantienen; Hypothesis añade cobertura de bordes
- **Strategies reutilizables** — módulo centralizado `tests/unit/strategies.py` con strategies para Quantity, SKU, MovementType
- **Determinismo en CI** — `--hypothesis-seed=0` para reproducibilidad; profile `dev` con 1000 ejemplos para exploración local
- **mypy strict solo en `src/`** — tests quedan con `strict=false` (mocks, fixtures dinámicas no benefician de strict)
- **Cero regresiones** — todos los 291 tests existentes deben seguir pasando

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| Hypothesis 6.x+ como dev dependency | Library madura y estable para PBT en Python. Estrategias composables. Sin impacto en producción |
| `max_examples=100` en CI | Balance entre exhaustividad y velocidad. 100 ejemplos por propiedad detecta la mayoría de edge cases sin penalizar CI |
| `--hypothesis-seed=0` en CI | Reproducibilidad total. Si un test falla en CI, falla con el mismo seed localmente |
| Profile `dev` con `max_examples=1000` | Para exploración local más profunda antes de commit |
| mypy `strict=true` solo en `src/` | Los tests usan mocks, `AsyncMock`, fixtures dinámicas que complican anotaciones estrictas sin beneficio claro |
| `type: ignore` solo con justificación | Si mypy strict falla en un caso legítimo, se añade `# type: ignore[xxx]` con comentario explicativo |
| Strategies en módulo separado | Evita duplicación de lógica de generación entre archivos de test. Un solo lugar para mantener las strategies |
| Coverage domain/ ≥90% (subido de >85%) | Con Hypothesis se generan más caminos; el umbral sube para reflejar la mayor confianza |

---

## Hypothesis Configuration

### `pyproject.toml` additions

```toml
[tool.pytest.ini_options]
# ... existing config ...
addopts = "-v --tb=short --hypothesis-seed=0"

[tool.hypothesis]
max_examples = 100
```

### Hypothesis profiles

```python
# En tests/unit/strategies.py o conftest.py
from hypothesis import settings, Phase

# Profile CI: 100 ejemplos, seed fijo (reproducible)
settings.register_profile("ci", max_examples=100, phases=[Phase.generate, Phase.target, Phase.shrink])

# Profile dev: 1000 ejemplos, más exhaustivo
settings.register_profile("dev", max_examples=1000, phases=[Phase.generate, Phase.target, Phase.shrink])

# Default: usa CI profile
settings.load_profile("ci")
```

---

## Hypothesis Strategies

### `tests/unit/strategies.py`

Módulo centralizado de strategies reutilizables para domain value objects y rules:

```python
"""Hypothesis strategies reutilizables para domain value objects y rules.

Centraliza la generación de datos de prueba para property-based testing.
Todas las strategies producen valores válidos por defecto; usar
st.integers(max_value=0) para casos inválidos.
"""
from __future__ import annotations

from hypothesis import strategies as st

from src.domain.value_objects.movement_type import MovementType


# ── Value Object Strategies ──────────────────────────────────────────────

valid_quantity_strategy = st.integers(min_value=1, max_value=999_999)
"""Strategy: enteros positivos para Quantity.value."""

invalid_quantity_strategy = st.one_of(
    st.integers(max_value=0),       # Cero o negativo
    st.just(0),                      # Caso específico: cero
)
"""Strategy: enteros no-positivos que deben rechazarse como Quantity."""

valid_sku_strategy = st.from_regex(r'[A-Za-z0-9\-_]{1,50}', fullmatch=True)
"""Strategy: strings que cumplen el regex de SKU."""

invalid_sku_strategy = st.one_of(
    st.text(min_size=51),            # Excede longitud máxima
    st.from_regex(r'[!@#$%^&*()]+'), # Caracteres no permitidos
    st.just(""),                      # Vacío
)
"""Strategy: strings que NO cumplen el regex de SKU."""

movement_type_strategy = st.sampled_from(list(MovementType))
"""Strategy: uno de los 4 MovementType values."""


# ── Domain Rule Strategies ──────────────────────────────────────────────

stock_delta_strategy = st.tuples(
    movement_type_strategy,
    valid_quantity_strategy,
)
"""Strategy: tupla (MovementType, Quantity) para calculate_stock_delta."""

product_id_strategy = st.integers(min_value=1, max_value=999_999)
"""Strategy: IDs de producto positivos."""

current_stock_strategy = st.integers(min_value=0, max_value=999_999)
"""Strategy: stock actual no-negativo."""
```

---

## Property-Based Test Examples

### Value Objects: Quantity

```python
# tests/unit/domain/test_quantity.py (adiciones Hypothesis)
from hypothesis import given
from tests.unit.strategies import valid_quantity_strategy, invalid_quantity_strategy

@given(qty=valid_quantity_strategy)
def test_quantity_valid_values(qty: int) -> None:
    """Property: todo entero positivo crea un Quantity válido."""
    q = Quantity(value=qty)
    assert q.value == qty

@given(qty=invalid_quantity_strategy)
def test_quantity_rejects_non_positive(qty: int) -> None:
    """Property: ningún entero ≤ 0 debe crear un Quantity válido."""
    with pytest.raises(InvalidQuantityError):
        Quantity(value=qty)
```

### Value Objects: SKU

```python
# tests/unit/domain/test_sku.py (adiciones Hypothesis)
from tests.unit.strategies import valid_sku_strategy, invalid_sku_strategy

@given(raw=valid_sku_strategy)
def test_sku_valid_format(raw: str) -> None:
    """Property: todo string que cumpla el regex crea un SKU válido."""
    sku = SKU(value=raw)
    assert sku.value == raw

@given(raw=invalid_sku_strategy)
def test_sku_rejects_invalid_format(raw: str) -> None:
    """Property: strings fuera del regex son rechazados."""
    with pytest.raises(InvalidSKUError):
        SKU(value=raw)
```

### Domain Rules: Stock Delta

```python
# tests/unit/domain/test_rules.py (adiciones Hypothesis)
from tests.unit.strategies import movement_type_strategy, valid_quantity_strategy

@given(
    mtype=movement_type_strategy,
    qty=valid_quantity_strategy,
)
def test_calculate_stock_delta_sign(mtype: MovementType, qty: int) -> None:
    """Property: IN/ADJUSTMENT → delta positivo, OUT/TRANSFER → delta negativo."""
    delta = calculate_stock_delta(mtype, qty)
    if mtype in (MovementType.IN, MovementType.ADJUSTMENT):
        assert delta > 0
        assert delta == qty
    else:
        assert delta < 0
        assert delta == -qty

@given(qty=valid_quantity_strategy)
def test_calculate_stock_delta_never_zero_for_valid_qty(qty: int) -> None:
    """Property: con cantidad válida (>0), el delta nunca es cero."""
    for mtype in MovementType:
        delta = calculate_stock_delta(mtype, qty)
        assert delta != 0
```

---

## mypy strict Activation

### `pyproject.toml` changes

```toml
[tool.mypy]
python_version = "3.12"
strict = true                    # CHANGED: false → true
warn_return_any = true           # Ya estaba
warn_unused_configs = true       # Ya estaba
disallow_untyped_defs = true     # CHANGED: false → true
disallow_incomplete_defs = true  # CHANGED: false → true
check_untyped_defs = true        # Ya estaba
no_implicit_optional = true      # Ya estaba
warn_redundant_casts = true      # Ya estaba
warn_unused_ignores = true       # Ya estaba
mypy_path = "src"

[[tool.mypy.overrides]]
# Tests: strict=false — mocks y fixtures dinámicas no se benefician
module = "tests.*"
strict = false
disallow_untyped_defs = false
disallow_incomplete_defs = false
```

### Expected mypy strict issues

Al activar `strict=true`, se espera encontrar los siguientes tipos de problemas en `src/`:

1. **Funciones sin tipo de retorno explícito** → Añadir `-> None`, `-> str`, etc.
2. **`Any` implícito en `*args`/`**kwargs`** → Añadir `*args: Any, **kwargs: Any`
3. **Atributos de dataclass sin tipo** → Añadir anotaciones de tipo
4. **Imports condicionales (`TYPE_CHECKING`)** → Asegurar que los tipos runtime también se resuelven
5. **`type: ignore` existentes** → Revisar si son necesarios bajo strict; eliminar los obsoletos

### Makefile addition

```makefile
typecheck:
	mypy src/ --strict
```

---

## Edge Cases for Use Cases

### `tests/unit/application/use_cases/` — Additions

Añadir tests de edge cases que no están cubiertos en los 194 tests existentes:

| Use Case | Edge Case | Expected Behavior |
|----------|-----------|-------------------|
| `RecordMovementUseCase` | Producto no encontrado | `ProductNotFoundError` propagada |
| `RecordMovementUseCase` | Movimiento OUT con stock=0 | `InsufficientStockError` con details |
| `RecordMovementUseCase` | TRANSFER sin origin/destination en metadata | `ValueError` por metadata inválida |
| `CreateProductUseCase` | SKU duplicado | `DuplicateSKUError` propagada |
| `CreateProductUseCase` | Categoría no encontrada | Error de FK / validación |
| `ListProductsUseCase` | Offset > total de productos | Lista vacía, total correcto |
| `ListProductsUseCase` | Limit=0 | Lista vacía, total correcto |
| `QueryCurrentStockUseCase` | Producto sin movimientos | Stock = 0.0 |
| `QueryStockAtDateUseCase` | Fecha futura | Stock = 0.0 (no hay movimientos futuros) |
| `CreateCategoryUseCase` | Nombre duplicado | `UniqueViolation` → error mapping |

---

## Coverage Target Updates

### `pyproject.toml` changes

```toml
[tool.coverage.report]
fail_under = 80  # Global: sin cambio
show_missing = true
skip_empty = true

# Nuevos thresholds por paquete (usando coverage.py fail_under por paquete)
# Se valida manualmente con: pytest --cov=src.domain --cov-fail-under=90
# Se valida manualmente con: pytest --cov=src.application --cov-fail-under=85
```

> **Nota:** coverage.py no soporta `fail_under` por paquete nativamente. Los thresholds por paquete se validan como asserts en el CI script o con un custom pytest plugin. El gate global de 80% se mantiene en `pyproject.toml`.

---

## Files

| File | Description | Action |
|------|-------------|--------|
| `tests/unit/strategies.py` | Hypothesis strategies centralizadas | NEW |
| `tests/unit/domain/test_quantity.py` | + property-based tests | MODIFY |
| `tests/unit/domain/test_sku.py` | + property-based tests | MODIFY |
| `tests/unit/domain/test_rules.py` | + property-based tests para stock_delta | MODIFY |
| `tests/unit/domain/test_product.py` | + edge cases | MODIFY |
| `tests/unit/domain/test_movement.py` | + edge cases | MODIFY |
| `tests/unit/application/use_cases/test_record_movement.py` | + edge cases | MODIFY |
| `tests/unit/application/use_cases/test_create_product.py` | + edge cases | MODIFY |
| `tests/unit/application/use_cases/test_list_products.py` | + edge cases | MODIFY |
| `tests/unit/application/use_cases/test_query_current_stock.py` | + edge cases | MODIFY |
| `tests/unit/application/use_cases/test_query_stock_at_date.py` | + edge cases | MODIFY |
| `tests/unit/application/use_cases/test_create_category.py` | + edge cases | MODIFY |
| `pyproject.toml` | mypy strict=true, Hypothesis config, addopts seed | MODIFY |
| `requirements.txt` | +hypothesis | MODIFY |
| `Makefile` | +typecheck command | MODIFY |
| `src/**/*.py` | Type hints para mypy strict | MODIFY (type annotations only) |

---

## Acceptance Criteria

- [ ] Hypothesis añadido a `requirements.txt` y `pyproject.toml`
- [ ] `tests/unit/strategies.py` con strategies reutilizables para Quantity, SKU, MovementType
- [ ] Property-based tests para: `Quantity` (boundary), `SKU` (regex), `calculate_stock_delta` (signo), `validate_stock_not_negative` (dominio)
- [ ] Edge cases añadidos en use cases: producto inexistente, categoría duplicada, movimiento con metadata inválida, stock=0, fecha futura, offset>total
- [ ] `mypy src/ --strict` pasa sin errores
- [ ] `pyproject.toml` actualizado: `strict = true`, overrides para `tests.*`
- [ ] Coverage `domain/` ≥90%, `application/` ≥85%
- [ ] 0 regresiones en tests existentes (291 → 291+)
- [ ] `make lint` pasa sin errores
- [ ] `--hypothesis-seed=0` configurado en `addopts` para reproducibilidad

---

## Testing Strategy

- **Property-based tests (Hypothesis):** Generan cientos de inputs automáticamente. Detectan edge cases como overflow, boundary values, y combinaciones inesperadas
- **Edge case tests (example-based):** Casos específicos no cubiertos en F2-F4. Cada use case tiene al menos 2 edge cases nuevos
- **Type checking (mypy):** `--strict` en CI como gate. Falla el build si hay tipos inconsistentes
- **Regression:** Todos los 291 tests existentes deben pasar sin modificación

### Ejemplo: Test de edge case en use case

```python
# tests/unit/application/use_cases/test_record_movement.py (adición)
async def test_record_movement_product_not_found() -> None:
    """Edge case: producto no encontrado al registrar movimiento."""
    mock_product_repo = AsyncMock(spec=IProductRepository)
    mock_product_repo.get_by_id.return_value = None  # Producto no existe

    use_case = RecordMovementUseCase(
        movement_repo=mock_movement_repo,
        product_repo=mock_product_repo,
        stock_query_repo=mock_stock_repo,
        uow=mock_uow,
    )

    with pytest.raises(ValueError, match="Product not found"):
        await use_case.execute(
            product_id=999,
            movement_type=MovementType.IN,
            quantity=10,
        )
```

---

## Resolved Questions

| # | Pregunta | Decisión | Rationale |
|---|----------|----------|-----------|
| F6-60-Q1 | ¿Hypothesis max_examples en CI? | **100** | Balance cobertura vs velocidad. 100 ejemplos detecta la mayoría de bugs. Profile dev con 1000 para local |
| F6-60-Q2 | ¿Hypothesis seed fijo? | **Sí, `--hypothesis-seed=0`** | Reproducibilidad total en CI. Si falla, se reproduce localmente con el mismo seed |
| F6-60-Q3 | ¿mypy strict scope? | **Solo `src/`** | Tests usan mocks, AsyncMock, fixtures dinámicas. Strict en tests añade fricción sin beneficio claro |
| F6-60-Q4 | ¿Coverage domain/ threshold? | **≥90%** (subido de >85%) | Con Hypothesis se generan más caminos de código; el umbral sube para reflejar mayor confianza |
| F6-60-Q5 | ¿`type: ignore` permitido? | **Solo con justificación** | `# type: ignore[xxx]  # Reason: ...` — nunca sin comentario explicativo |
| F6-60-Q6 | ¿Strategies en módulo separado? | **Sí, `tests/unit/strategies.py`** | Evita duplicación, facilita mantenimiento, un solo lugar para actualizar si cambian los value objects |
