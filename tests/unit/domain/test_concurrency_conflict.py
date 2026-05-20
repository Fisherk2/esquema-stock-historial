"""Tests unitarios para ConcurrencyConflictError (SPEC-51).

Verifica que la excepcion de concurrencia hereda de DomainError,
almacena atributos correctamente y construye mensajes significativos.
"""

from __future__ import annotations


class TestConcurrencyConflictError:
    """Tests para ConcurrencyConflictError."""

    def test_inherits_from_domain_error(self) -> None:
        """Verifica que hereda de DomainError."""
        from src.domain.exceptions.concurrency_conflict import (
            ConcurrencyConflictError,
        )
        from src.domain.exceptions.domain_error import DomainError

        assert issubclass(ConcurrencyConflictError, DomainError)

    def test_has_operation_attribute(self) -> None:
        """Verifica que almacena la operacion en conflicto."""
        from src.domain.exceptions.concurrency_conflict import (
            ConcurrencyConflictError,
        )

        err = ConcurrencyConflictError(operation="refresh_view")
        assert err.operation == "refresh_view"

    def test_has_optional_detail_attribute(self) -> None:
        """Verifica que puede almacenar detalle adicional."""
        from src.domain.exceptions.concurrency_conflict import (
            ConcurrencyConflictError,
        )

        err = ConcurrencyConflictError(
            operation="refresh_view", detail="serialization failure"
        )
        assert err.detail == "serialization failure"

    def test_detail_is_none_when_not_provided(self) -> None:
        """Verifica que detail es None si no se proporciona."""
        from src.domain.exceptions.concurrency_conflict import (
            ConcurrencyConflictError,
        )

        err = ConcurrencyConflictError(operation="refresh_view")
        assert err.detail is None

    def test_message_includes_operation(self) -> None:
        """Verifica que el mensaje incluye la operacion."""
        from src.domain.exceptions.concurrency_conflict import (
            ConcurrencyConflictError,
        )

        err = ConcurrencyConflictError(operation="refresh_view")
        assert "refresh_view" in str(err)

    def test_message_includes_detail_when_provided(self) -> None:
        """Verifica que el mensaje incluye el detalle cuando se proporciona."""
        from src.domain.exceptions.concurrency_conflict import (
            ConcurrencyConflictError,
        )

        err = ConcurrencyConflictError(
            operation="refresh_view", detail="serialization failure"
        )
        assert "serialization failure" in str(err)

    def test_is_catchable_as_domain_error(self) -> None:
        """Verifica que puede capturarse como DomainError."""
        from src.domain.exceptions.concurrency_conflict import (
            ConcurrencyConflictError,
        )
        from src.domain.exceptions.domain_error import DomainError

        raised = False
        try:
            raise ConcurrencyConflictError(operation="test")
        except DomainError:
            raised = True
        assert raised
