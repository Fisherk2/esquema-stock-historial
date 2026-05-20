"""Hypothesis strategies reutilizables para domain value objects y rules.

Centraliza la generación de datos de prueba para property-based testing.
Todas las strategies producen valores válidos por defecto; usar
``st.integers(max_value=0)`` para casos inválidos.

Ejemplo::

    from hypothesis import given
    from tests.unit.strategies import valid_quantity_strategy

    @given(qty=valid_quantity_strategy)
    def test_quantity_valid_values(qty: int) -> None:
        q = Quantity(value=qty)
        assert q.value == qty
"""

from __future__ import annotations

from hypothesis import settings
from hypothesis import strategies as st

from src.domain.value_objects.movement_type import MovementType

# ── Hypothesis profiles ────────────────────────────────────────────────

settings.register_profile(
    "ci",
    max_examples=100,
)
settings.register_profile(
    "dev",
    max_examples=1000,
)

# Default: usa CI profile para reproducibilidad y velocidad
settings.load_profile("ci")

# ── Value Object Strategies ──────────────────────────────────────────────

valid_quantity_strategy: st.SearchStrategy[int] = st.integers(
    min_value=1, max_value=999_999
)
"""Strategy: enteros positivos para Quantity.value."""

invalid_quantity_strategy: st.SearchStrategy[int] = st.integers(
    min_value=-999_999, max_value=0
)
"""Strategy: enteros no-positivos que deben rechazarse como Quantity."""

valid_sku_strategy: st.SearchStrategy[str] = st.from_regex(
    r"[A-Za-z0-9\-_]{1,50}", fullmatch=True
)
"""Strategy: strings que cumplen el regex de SKU."""

invalid_sku_strategy: st.SearchStrategy[str] = st.one_of(
    st.text(min_size=51, max_size=100),  # Excede longitud máxima
    st.from_regex(r"^[!@#$%^&*() ]+$"),  # Caracteres no permitidos
    st.just(""),  # Vacío
)
"""Strategy: strings que NO cumplen el regex de SKU."""

movement_type_strategy: st.SearchStrategy[MovementType] = st.sampled_from(
    list(MovementType)
)
"""Strategy: uno de los 4 MovementType values."""

# ── Domain Rule Strategies ──────────────────────────────────────────────

stock_delta_strategy: st.SearchStrategy[tuple[MovementType, int]] = st.tuples(
    movement_type_strategy,
    valid_quantity_strategy,
)
"""Strategy: tupla (MovementType, Quantity) para calculate_stock_delta."""

product_id_strategy: st.SearchStrategy[int] = st.integers(
    min_value=1, max_value=999_999
)
"""Strategy: IDs de producto positivos."""

current_stock_strategy: st.SearchStrategy[int] = st.integers(
    min_value=0, max_value=999_999
)
"""Strategy: stock actual no-negativo."""
