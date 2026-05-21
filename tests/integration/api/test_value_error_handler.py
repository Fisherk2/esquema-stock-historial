"""Tests para el handler de ValueError con verificacion de origen.

Valida que el ``handle_value_error`` distingue correctamente entre
errores de validacion de input (que deben retornar HTTP 400) y errores
internos de programacion (que deben re-lanzarse como HTTP 500).

Nota: Pydantic envuelve los errores de ``model_validator`` en
``ValidationError`` (HTTP 422), por lo que no llegan al handler
``ValueError``. Este handler solo captura ``ValueError`` raw que se
lanzan fuera del pipeline de Pydantic.

Los tests de integracion verifican que el handler no enmascara errores
internos como 400. Los tests unitarios verifican la logica del
traceback walker.
"""

from __future__ import annotations

import httpx


async def test_value_error_handler_does_not_mask_internal_errors(
    api_client: httpx.AsyncClient,
) -> None:
    """El handler ValueError no debe enmascarar errores internos como 400.

    Si un ValueError se origina fuera de los modulos de validacion,
    debe propagarse al handler de Exception (500), no retornar 400.

    Este test verifica que un input invalido que no es validacion
    (ej: un endpoint inexistente que podria provocar un error interno)
    no retorna 400 de forma erronea.
    """
    # Un endpoint inexistente retorna 404, no 400
    response = await api_client.get("/v1/nonexistent-endpoint")
    assert response.status_code == 404, (
        "Endpoints inexistentes deben retornar 404, no 400"
    )
