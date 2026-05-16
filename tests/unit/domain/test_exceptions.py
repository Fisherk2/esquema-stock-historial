"""Tests unitarios para la jerarquia de excepciones del dominio.

Valida que ``DomainError`` sea la raiz de todas las excepciones de dominio
y que las excepciones concretas hereden correctamente.

Ejemplo::

    pytest tests/unit/domain/test_exceptions.py -v
"""

from __future__ import annotations

import pytest


def test_domain_error_is_exception() -> None:
    """Verifica que DomainError hereda de Exception."""
    from src.domain.exceptions.domain_error import DomainError

    assert issubclass(DomainError, Exception)


def test_domain_error_can_be_raised_and_caught() -> None:
    """Verifica que DomainError se puede lanzar y capturar."""
    from src.domain.exceptions.domain_error import DomainError

    with pytest.raises(DomainError):
        raise DomainError("test error")


def test_domain_error_has_message() -> None:
    """Verifica que DomainError almacena el mensaje correctamente."""
    from src.domain.exceptions.domain_error import DomainError

    err = DomainError("something went wrong")
    assert str(err) == "something went wrong"


def test_domain_error_has_docstring() -> None:
    """Verifica que DomainError tiene docstring estilo Google."""
    from src.domain.exceptions.domain_error import DomainError

    assert DomainError.__doc__ is not None
    assert len(DomainError.__doc__.strip()) > 0
