"""Router de categorias — creacion y consulta de categorias.

Endpoints:
    POST   /v1/categories    — Crear categoria
    GET    /v1/categories    — Listar categorias
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends

from src.adapters.api.dependencies import (
    get_category_repo,
    get_create_category_use_case,
)
from src.application.dtos.category_dtos import (
    CategoryOutput,
    CreateCategoryInput,
)
from src.application.use_cases.create_category import CreateCategoryUseCase

if TYPE_CHECKING:
    from src.domain.ports.category_repository import ICategoryRepository

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post(
    "",
    response_model=CategoryOutput,
    status_code=201,
    summary="Crear categoria",
)
async def create_category(
    body: CreateCategoryInput,
    use_case: Annotated[CreateCategoryUseCase, Depends(get_create_category_use_case)],
) -> CategoryOutput:
    """Crea una nueva categoria."""
    category = await use_case.execute(
        name=body.name,
        description=body.description,
    )
    return CategoryOutput(
        id=category.id,
        name=category.name,
        description=category.description,
        created_at=category.created_at,
    )


@router.get(
    "",
    response_model=list[CategoryOutput],
    summary="Listar categorias",
)
async def list_categories(
    repo: Annotated[ICategoryRepository, Depends(get_category_repo)],
) -> list[CategoryOutput]:
    """Lista todas las categorias (sin paginacion)."""
    categories = await repo.list_all()
    return [
        CategoryOutput(
            id=c.id,
            name=c.name,
            description=c.description,
            created_at=c.created_at,
        )
        for c in categories
    ]
