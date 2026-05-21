"""Router de categorias — creacion y consulta de categorias.

Endpoints:
    POST   /v1/categories            — Crear categoria
    GET    /v1/categories            — Listar categorias (paginado)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.adapters.api.dependencies import (
    get_category_repo,
    get_create_category_use_case,
)
from src.application.dtos.category_dtos import (
    CategoryOutput,
    CreateCategoryInput,
)
from src.application.use_cases.create_category import CreateCategoryUseCase
from src.domain.ports.category_repository import ICategoryRepository

router = APIRouter(prefix="/categories", tags=["categories"])

# Paginacion por defecto: 100 categorias por pagina (suficiente para
# la mayoria de sistemas; las categorias son tipicamente < 100).
_MAX_LIMIT = 1000
_DEFAULT_LIMIT = 100


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
    if category.id is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to create category: no ID generated",
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
    limit: int = Query(
        default=_DEFAULT_LIMIT,
        ge=1,
        le=_MAX_LIMIT,
        description="Numero maximo de categorias a retornar.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Numero de categorias a saltar.",
    ),
) -> list[CategoryOutput]:
    """Lista categorias con paginacion en base de datos."""
    categories = await repo.list_all(limit=limit, offset=offset)
    return [
        CategoryOutput(
            id=c.id,  # type: ignore[arg-type]
            name=c.name,
            description=c.description,
            created_at=c.created_at,
        )
        for c in categories
    ]
