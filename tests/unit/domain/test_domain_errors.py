"""Tests unitarios para InsufficientStockError e ImmutabilityViolationError.

Valida que ambas excepciones heredan de DomainError y almacenan sus
atributos especificos correctamente.

Ejemplo::

    pytest tests/unit/domain/test_domain_errors.py -v
"""

from __future__ import annotations


class TestInsufficientStockError:
    """Tests para InsufficientStockError."""

    def test_inherits_from_domain_error(self) -> None:
        """Verifica que hereda de DomainError."""
        from src.domain.exceptions.domain_error import DomainError
        from src.domain.exceptions.insufficient_stock import InsufficientStockError

        assert issubclass(InsufficientStockError, DomainError)

    def test_has_product_id_attribute(self) -> None:
        """Verifica que almacena product_id."""
        from src.domain.exceptions.insufficient_stock import InsufficientStockError

        err = InsufficientStockError(product_id=1, requested=10, available=5)
        assert err.product_id == 1

    def test_has_requested_attribute(self) -> None:
        """Verifica que almacena requested."""
        from src.domain.exceptions.insufficient_stock import InsufficientStockError

        err = InsufficientStockError(product_id=1, requested=10, available=5)
        assert err.requested == 10

    def test_has_available_attribute(self) -> None:
        """Verifica que almacena available."""
        from src.domain.exceptions.insufficient_stock import InsufficientStockError

        err = InsufficientStockError(product_id=1, requested=10, available=5)
        assert err.available == 5

    def test_has_descriptive_message(self) -> None:
        """Verifica que el mensaje describe el error de stock."""
        from src.domain.exceptions.insufficient_stock import InsufficientStockError

        err = InsufficientStockError(product_id=1, requested=10, available=5)
        assert "1" in str(err) or "10" in str(err) or "5" in str(err)


class TestImmutabilityViolationError:
    """Tests para ImmutabilityViolationError."""

    def test_inherits_from_domain_error(self) -> None:
        """Verifica que hereda de DomainError."""
        from src.domain.exceptions.domain_error import DomainError
        from src.domain.exceptions.immutability_violation import (
            ImmutabilityViolationError,
        )

        assert issubclass(ImmutabilityViolationError, DomainError)

    def test_has_entity_type_attribute(self) -> None:
        """Verifica que almacena entity_type."""
        from src.domain.exceptions.immutability_violation import (
            ImmutabilityViolationError,
        )

        err = ImmutabilityViolationError(entity_type="Movement", entity_id=42)
        assert err.entity_type == "Movement"

    def test_has_entity_id_attribute(self) -> None:
        """Verifica que almacena entity_id."""
        from src.domain.exceptions.immutability_violation import (
            ImmutabilityViolationError,
        )

        err = ImmutabilityViolationError(entity_type="Movement", entity_id=42)
        assert err.entity_id == 42
