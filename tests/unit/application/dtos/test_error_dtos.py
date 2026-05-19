"""Tests para DTOs de error."""
from __future__ import annotations

from src.application.dtos.error_dtos import ErrorDetail, ErrorResponse


class TestErrorResponse:
    """Tests para ErrorResponse."""

    def test_format_with_details(self) -> None:
        """Verifica formato con details."""
        detail = ErrorDetail(
            code="INSUFFICIENT_STOCK",
            message="Not enough stock",
            details={"product_id": 1, "requested": 10, "available": 3},
        )
        response = ErrorResponse(error=detail)
        assert response.error.code == "INSUFFICIENT_STOCK"
        assert response.error.details is not None
        assert response.error.details["product_id"] == 1

    def test_format_without_details(self) -> None:
        """Verifica formato sin details."""
        detail = ErrorDetail(code="NOT_FOUND", message="Resource not found")
        response = ErrorResponse(error=detail)
        assert response.error.details is None

    def test_serializes_to_expected_format(self) -> None:
        """Verifica que serializa al formato {error: {code, message}}."""
        detail = ErrorDetail(code="VALIDATION_ERROR", message="Invalid input")
        response = ErrorResponse(error=detail)
        json_str = response.model_dump_json()
        assert '"error"' in json_str
        assert '"code":"VALIDATION_ERROR"' in json_str
        assert '"message":"Invalid input"' in json_str
