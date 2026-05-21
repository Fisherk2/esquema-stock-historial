# SPEC-60: Unit Tests — Hypothesis + mypy strict

**Phase:** F6 — Integral Testing
**Dependencies:** Spec-21 (Business Rules) ✅ Completed, Spec-22 (Protocols) ✅ Completed, Spec-40 (Use Cases) ✅ Completed
**Priority:** High
**Status:** Approved

---

## Objective

Consolidate and expand the existing unit test suite (194 tests) with three objectives: (1) add **property-based testing** with Hypothesis for domain rules and value objects, capturing edge cases that example-based tests do not detect; (2) enable **mypy `--strict`** as a CI quality gate, raising type safety in `src/`; (3) close coverage gaps to reach ≥90% in `domain/` and ≥85% in `application/`.

**Design principles:**
- **Hypothesis as a complement, not a replacement** — existing example-based tests are kept; Hypothesis adds edge coverage
- **Reusable strategies** — centralized module `tests/unit/strategies.py` with strategies for Quantity, SKU, MovementType
- **Determinism in CI** — `--hypothesis-seed=0` for reproducibility; `dev` profile with 1000 examples for local exploration
- **mypy strict only on `src/`** — tests remain with `strict=false` (mocks, dynamic fixtures do not benefit from strict)
- **Zero regressions** — all 291 existing tests must continue passing

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| Hypothesis 6.x+ as dev dependency | Mature and stable library for PBT in Python. Composable strategies. No production impact |
| `max_examples=100` in CI | Balance between exhaustiveness and speed. 100 examples per property detects most edge cases without penalizing CI |
| `--hypothesis-seed=0` in CI | Total reproducibility. If a test fails in CI, it fails with the same seed locally |
| `dev` profile with `max_examples=1000` | For deeper local exploration before commit |
| mypy `strict=true` only on `src/` | Tests use mocks, `AsyncMock`, dynamic fixtures that complicate strict annotations without clear benefit |
| `type: ignore` only with justification | If mypy strict fails on a legitimate case, add `# type: ignore[xxx]` with an explanatory comment |
| Strategies in a separate module | Avoids duplication of generation logic between test files. A single place to maintain strategies |
| Coverage domain/ ≥90% (raised from >85%) | With Hypothesis more paths are generated; the threshold rises to reflect greater confidence |

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
# In tests/unit/strategies.py or conftest.py
from hypothesis import settings, Phase

# CI profile: 100 examples, fixed seed (reproducible)
settings.register_profile("ci", max_examples=100, phases=[Phase.generate, Phase.target, Phase.shrink])

# dev profile: 1000 examples, more exhaustive
settings.register_profile("dev", max_examples=1000, phases=[Phase.generate, Phase.target, Phase.shrink])

# Default: uses CI profile
settings.load_profile("ci")
```

---

## Hypothesis Strategies

### `tests/unit/strategies.py`

Centralized module of reusable strategies for domain value objects and rules:

```python
"""Reusable Hypothesis strategies for domain value objects and rules.

Centralizes test data generation for property-based testing.
All strategies produce valid values by default; use
st.integers(max_value=0) for invalid cases.
"""
from __future__ import annotations

from hypothesis import strategies as st

from src.domain.value_objects.movement_type import MovementType


# ── Value Object Strategies ──────────────────────────────────────────────

valid_quantity_strategy = st.integers(min_value=1, max_value=999_999)
"""Strategy: positive integers for Quantity.value."""

invalid_quantity_strategy = st.one_of(
    st.integers(max_value=0),       # Zero or negative
    st.just(0),                      # Specific case: zero
)
"""Strategy: non-positive integers that should be rejected as Quantity."""

valid_sku_strategy = st.from_regex(r'[A-Za-z0-9\-_]{1,50}', fullmatch=True)
"""Strategy: strings that match the SKU regex."""

invalid_sku_strategy = st.one_of(
    st.text(min_size=51),            # Exceeds maximum length
    st.from_regex(r'[!@#$%^&*()]+'), # Disallowed characters
    st.just(""),                      # Empty
)
"""Strategy: strings that do NOT match the SKU regex."""

movement_type_strategy = st.sampled_from(list(MovementType))
"""Strategy: one of the 4 MovementType values."""


# ── Domain Rule Strategies ──────────────────────────────────────────────

stock_delta_strategy = st.tuples(
    movement_type_strategy,
    valid_quantity_strategy,
)
"""Strategy: tuple (MovementType, Quantity) for calculate_stock_delta."""

product_id_strategy = st.integers(min_value=1, max_value=999_999)
"""Strategy: positive product IDs."""

current_stock_strategy = st.integers(min_value=0, max_value=999_999)
"""Strategy: non-negative current stock."""
```

---

## Property-Based Test Examples

### Value Objects: Quantity

```python
# tests/unit/domain/test_quantity.py (Hypothesis additions)
from hypothesis import given
from tests.unit.strategies import valid_quantity_strategy, invalid_quantity_strategy

@given(qty=valid_quantity_strategy)
def test_quantity_valid_values(qty: int) -> None:
    """Property: every positive integer creates a valid Quantity."""
    q = Quantity(value=qty)
    assert q.value == qty

@given(qty=invalid_quantity_strategy)
def test_quantity_rejects_non_positive(qty: int) -> None:
    """Property: no integer ≤ 0 should create a valid Quantity."""
    with pytest.raises(InvalidQuantityError):
        Quantity(value=qty)
```

### Value Objects: SKU

```python
# tests/unit/domain/test_sku.py (Hypothesis additions)
from tests.unit.strategies import valid_sku_strategy, invalid_sku_strategy

@given(raw=valid_sku_strategy)
def test_sku_valid_format(raw: str) -> None:
    """Property: every string matching the regex creates a valid SKU."""
    sku = SKU(value=raw)
    assert sku.value == raw

@given(raw=invalid_sku_strategy)
def test_sku_rejects_invalid_format(raw: str) -> None:
    """Property: strings outside the regex are rejected."""
    with pytest.raises(InvalidSKUError):
        SKU(value=raw)
```

### Domain Rules: Stock Delta

```python
# tests/unit/domain/test_rules.py (Hypothesis additions)
from tests.unit.strategies import movement_type_strategy, valid_quantity_strategy

@given(
    mtype=movement_type_strategy,
    qty=valid_quantity_strategy,
)
def test_calculate_stock_delta_sign(mtype: MovementType, qty: int) -> None:
    """Property: IN/ADJUSTMENT → positive delta, OUT/TRANSFER → negative delta."""
    delta = calculate_stock_delta(mtype, qty)
    if mtype in (MovementType.IN, MovementType.ADJUSTMENT):
        assert delta > 0
        assert delta == qty
    else:
        assert delta < 0
        assert delta == -qty

@given(qty=valid_quantity_strategy)
def test_calculate_stock_delta_never_zero_for_valid_qty(qty: int) -> None:
    """Property: with valid quantity (>0), delta is never zero."""
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
warn_return_any = true           # Already present
warn_unused_configs = true       # Already present
disallow_untyped_defs = true     # CHANGED: false → true
disallow_incomplete_defs = true  # CHANGED: false → true
check_untyped_defs = true        # Already present
no_implicit_optional = true      # Already present
warn_redundant_casts = true      # Already present
warn_unused_ignores = true       # Already present
mypy_path = "src"

[[tool.mypy.overrides]]
# Tests: strict=false — mocks and dynamic fixtures do not benefit
module = "tests.*"
strict = false
disallow_untyped_defs = false
disallow_incomplete_defs = false
```

### Expected mypy strict issues

When enabling `strict=true`, the following types of issues are expected in `src/`:

1. **Functions without explicit return type** → Add `-> None`, `-> str`, etc.
2. **Implicit `Any` in `*args`/`**kwargs`** → Add `*args: Any, **kwargs: Any`
3. **Dataclass attributes without type** → Add type annotations
4. **Conditional imports (`TYPE_CHECKING`)** → Ensure runtime types also resolve
5. **Existing `type: ignore`** → Review if still needed under strict; remove obsolete ones

### Makefile addition

```makefile
typecheck:
	mypy src/ --strict
```

---

## Edge Cases for Use Cases

### `tests/unit/application/use_cases/` — Additions

Add edge case tests not covered in the existing 194 tests:

| Use Case | Edge Case | Expected Behavior |
|----------|-----------|-------------------|
| `RecordMovementUseCase` | Product not found | `ProductNotFoundError` propagated |
| `RecordMovementUseCase` | OUT movement with stock=0 | `InsufficientStockError` with details |
| `RecordMovementUseCase` | TRANSFER without origin/destination in metadata | `ValueError` for invalid metadata |
| `CreateProductUseCase` | Duplicate SKU | `DuplicateSKUError` propagated |
| `CreateProductUseCase` | Category not found | FK error / validation |
| `ListProductsUseCase` | Offset > total products | Empty list, correct total |
| `ListProductsUseCase` | Limit=0 | Empty list, correct total |
| `QueryCurrentStockUseCase` | Product without movements | Stock = 0.0 |
| `QueryStockAtDateUseCase` | Future date | Stock = 0.0 (no future movements) |
| `CreateCategoryUseCase` | Duplicate name | `UniqueViolation` → error mapping |

---

## Coverage Target Updates

### `pyproject.toml` changes

```toml
[tool.coverage.report]
fail_under = 80  # Global: no change
show_missing = true
skip_empty = true

# New per-package thresholds (using coverage.py fail_under per package)
# Validated manually with: pytest --cov=src.domain --cov-fail-under=90
# Validated manually with: pytest --cov=src.application --cov-fail-under=85
```

> **Note:** coverage.py does not natively support `fail_under` per package. Per-package thresholds are validated as asserts in the CI script or with a custom pytest plugin. The global 80% gate remains in `pyproject.toml`.

---

## Files

| File | Description | Action |
|------|-------------|--------|
| `tests/unit/strategies.py` | Centralized Hypothesis strategies | NEW |
| `tests/unit/domain/test_quantity.py` | + property-based tests | MODIFY |
| `tests/unit/domain/test_sku.py` | + property-based tests | MODIFY |
| `tests/unit/domain/test_rules.py` | + property-based tests for stock_delta | MODIFY |
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
| `src/**/*.py` | Type hints for mypy strict | MODIFY (type annotations only) |

---

## Acceptance Criteria

- [ ] Hypothesis added to `requirements.txt` and `pyproject.toml`
- [ ] `tests/unit/strategies.py` with reusable strategies for Quantity, SKU, MovementType
- [ ] Property-based tests for: `Quantity` (boundary), `SKU` (regex), `calculate_stock_delta` (sign), `validate_stock_not_negative` (domain)
- [ ] Edge cases added in use cases: non-existent product, duplicate category, movement with invalid metadata, stock=0, future date, offset>total
- [ ] `mypy src/ --strict` passes without errors
- [ ] `pyproject.toml` updated: `strict = true`, overrides for `tests.*`
- [ ] Coverage `domain/` ≥90%, `application/` ≥85%
- [ ] 0 regressions in existing tests (291 → 291+)
- [ ] `make lint` passes without errors
- [ ] `--hypothesis-seed=0` configured in `addopts` for reproducibility

---

## Testing Strategy

- **Property-based tests (Hypothesis):** Automatically generate hundreds of inputs. Detect edge cases like overflow, boundary values, and unexpected combinations
- **Edge case tests (example-based):** Specific cases not covered in F2-F4. Each use case has at least 2 new edge cases
- **Type checking (mypy):** `--strict` in CI as a gate. Build fails if there are inconsistent types
- **Regression:** All 291 existing tests must pass without modification

### Example: Edge case test in use case

```python
# tests/unit/application/use_cases/test_record_movement.py (addition)
async def test_record_movement_product_not_found() -> None:
    """Edge case: product not found when recording movement."""
    mock_product_repo = AsyncMock(spec=IProductRepository)
    mock_product_repo.get_by_id.return_value = None  # Product does not exist

    use_case = RecordMovementUseCase(
        movement_repo=mock_movement_repo,
        product_repo=mock_product_repo,
        stock_query_repo=mock_stock_repo,
        uow=mock_uow,
    )

    with pytest.raises(ProductNotFoundError) as exc_info:
        await use_case.execute(
            product_id=999,
            movement_type=MovementType.IN,
            quantity=10,
            metadata={},
        )

    assert exc_info.value.product_id == 999
```

---

## Resolved Questions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| F6-60-Q1 | Hypothesis max_examples in CI? | **100** | Coverage vs speed balance. 100 examples detect most bugs. Dev profile with 1000 for local |
| F6-60-Q2 | Fixed Hypothesis seed? | **Yes, `--hypothesis-seed=0`** | Total reproducibility in CI. If it fails, reproduce locally with the same seed |
| F6-60-Q3 | mypy strict scope? | **Only `src/`** | Tests use mocks, AsyncMock, dynamic fixtures. Strict on tests adds friction without clear benefit |
| F6-60-Q4 | Coverage domain/ threshold? | **≥90%** (raised from >85%) | With Hypothesis more code paths are generated; threshold rises to reflect greater confidence |
| F6-60-Q5 | Is `type: ignore` allowed? | **Only with justification** | `# type: ignore[xxx]  # Reason: ...` — never without an explanatory comment |
| F6-60-Q6 | Strategies in a separate module? | **Yes, `tests/unit/strategies.py`** | Avoids duplication, eases maintenance, single place to update if value objects change |
