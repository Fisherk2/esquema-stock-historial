"""Router de productos — creacion y consulta de productos.

Endpoints:
    POST   /v1/products              — Crear producto
    GET    /v1/products              — Listar productos
    GET    /v1/products/{product_id} — Obtener producto por ID
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.adapters.api.dependencies import (
    get_create_product_use_case,
    get_list_products_use_case,
    get_product_repo,
)
from src.application.dtos.product_dtos import (
    CreateProductInput,
    ProductListOutput,
    ProductOutput,
)
from src.application.use_cases.create_product import CreateProductUseCase
from src.application.use_cases.list_products import ListProductsUseCase
from src.domain.ports.product_repository import IProductRepository

router = APIRouter(prefix="/products", tags=["products"])


@router.post(
    "",
    response_model=ProductOutput,
    status_code=201,
    summary="Crear producto",
    description="Crea un nuevo producto en el inventario. "
    "La categoria debe existir previamente.",
)
async def create_product(
    body: CreateProductInput,
    use_case: Annotated[CreateProductUseCase, Depends(get_create_product_use_case)],
) -> ProductOutput:
    """Crea un nuevo producto."""
    product = await use_case.execute(
        sku=body.sku,
        name=body.name,
        unit_of_measure=body.unit_of_measure,
        category_id=body.category_id,
        description=body.description,
        min_stock_threshold=body.min_stock_threshold,
    )
    return ProductOutput(
        id=product.id,
        sku=product.sku.value,
        name=product.name,
        description=product.description,
        unit_of_measure=product.unit_of_measure,
        category_id=product.category_id,
        min_stock_threshold=product.min_stock_threshold,
        created_at=product.created_at,
    )


@router.get(
    "",
    response_model=ProductListOutput,
    summary="Listar productos",
)
async def list_products(
    use_case: Annotated[ListProductsUseCase, Depends(get_list_products_use_case)],
    limit: int = Query(default=100, ge=1, le=1000, description="Maximo de resultados."),
    offset: int = Query(default=0, ge=0, description="Desplazamiento."),
) -> ProductListOutput:
    """Lista productos con paginacion."""
    products, total = await use_case.execute(limit=limit, offset=offset)
    return ProductListOutput(
        items=[
            ProductOutput(
                id=p.id,
                sku=p.sku.value,
                name=p.name,
                description=p.description,
                unit_of_measure=p.unit_of_measure,
                category_id=p.category_id,
                min_stock_threshold=p.min_stock_threshold,
                created_at=p.created_at,
            )
            for p in products
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{product_id}",
    response_model=ProductOutput,
    summary="Obtener producto por ID",
)
async def get_product(
    product_id: int,
    repo: Annotated[IProductRepository, Depends(get_product_repo)],
) -> ProductOutput:
    """Obtiene un producto por su ID."""
    product = await repo.get_by_id(product_id)
    if product is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOutput(
        id=product.id,
        sku=product.sku.value,
        name=product.name,
        description=product.description,
        unit_of_measure=product.unit_of_measure,
        category_id=product.category_id,
        min_stock_threshold=product.min_stock_threshold,
        created_at=product.created_at,
    )
