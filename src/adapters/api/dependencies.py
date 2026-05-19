"""Factory functions para dependency injection de FastAPI.

Cada factory function construye un repositorio o caso de uso inyectando
el pool de conexiones asyncpg. Se usan con ``Depends()`` en los endpoints.
"""

from __future__ import annotations

from typing import Annotated

import asyncpg
from fastapi import Depends, HTTPException

from src.application.use_cases.create_category import CreateCategoryUseCase
from src.application.use_cases.create_product import CreateProductUseCase
from src.application.use_cases.list_products import ListProductsUseCase
from src.application.use_cases.query_current_stock import QueryCurrentStockUseCase
from src.application.use_cases.query_stock_at_date import QueryStockAtDateUseCase
from src.application.use_cases.record_movement import RecordMovementUseCase
from src.domain.ports.category_repository import ICategoryRepository
from src.domain.ports.movement_repository import IMovementRepository
from src.domain.ports.product_repository import IProductRepository
from src.domain.ports.stock_query_repository import IStockQueryRepository
from src.domain.ports.unit_of_work import IUnitOfWork
from src.infrastructure.db.connection import get_pool
from src.infrastructure.db.uow import PostgresUnitOfWork
from src.infrastructure.repositories.category_repository import (
    PostgresCategoryRepository,
)
from src.infrastructure.repositories.movement_repository import (
    PostgresMovementRepository,
)
from src.infrastructure.repositories.product_repository import (
    PostgresProductRepository,
)
from src.infrastructure.repositories.stock_query_repository import (
    PostgresStockQueryRepository,
)

# ─── Pool ───────────────────────────────────────────────────────────────


async def get_db_pool() -> asyncpg.Pool:
    """Obtiene el pool de conexiones asyncpg.

    Raises:
        HTTPException: Si el pool no esta inicializado.
    """
    pool = await get_pool()
    if pool is None:
        raise HTTPException(
            status_code=503,
            detail="Database connection not available",
        )
    return pool


# ─── Repositories ───────────────────────────────────────────────────────


async def get_movement_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> IMovementRepository:
    """Fabrica de repositorio de movimientos."""
    return PostgresMovementRepository(pool)


async def get_product_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> IProductRepository:
    """Fabrica de repositorio de productos."""
    return PostgresProductRepository(pool)


async def get_category_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> ICategoryRepository:
    """Fabrica de repositorio de categorias."""
    return PostgresCategoryRepository(pool)


async def get_stock_query_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> IStockQueryRepository:
    """Fabrica de repositorio de consultas de stock."""
    return PostgresStockQueryRepository(pool)


# ─── Unit of Work ───────────────────────────────────────────────────────


async def get_unit_of_work(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> IUnitOfWork:
    """Fabrica de Unit of Work."""
    return PostgresUnitOfWork(pool)


# ─── Use Cases ──────────────────────────────────────────────────────────


async def get_record_movement_use_case(
    movement_repo: Annotated[IMovementRepository, Depends(get_movement_repo)],
    product_repo: Annotated[IProductRepository, Depends(get_product_repo)],
    stock_query_repo: Annotated[IStockQueryRepository, Depends(get_stock_query_repo)],
    uow: Annotated[IUnitOfWork, Depends(get_unit_of_work)],
) -> RecordMovementUseCase:
    """Fabrica de RecordMovementUseCase."""
    return RecordMovementUseCase(movement_repo, product_repo, stock_query_repo, uow)


async def get_query_current_stock_use_case(
    stock_query_repo: Annotated[IStockQueryRepository, Depends(get_stock_query_repo)],
) -> QueryCurrentStockUseCase:
    """Fabrica de QueryCurrentStockUseCase."""
    return QueryCurrentStockUseCase(stock_query_repo)


async def get_query_stock_at_date_use_case(
    stock_query_repo: Annotated[IStockQueryRepository, Depends(get_stock_query_repo)],
) -> QueryStockAtDateUseCase:
    """Fabrica de QueryStockAtDateUseCase."""
    return QueryStockAtDateUseCase(stock_query_repo)


async def get_create_product_use_case(
    product_repo: Annotated[IProductRepository, Depends(get_product_repo)],
    category_repo: Annotated[ICategoryRepository, Depends(get_category_repo)],
) -> CreateProductUseCase:
    """Fabrica de CreateProductUseCase."""
    return CreateProductUseCase(product_repo, category_repo)


async def get_list_products_use_case(
    product_repo: Annotated[IProductRepository, Depends(get_product_repo)],
) -> ListProductsUseCase:
    """Fabrica de ListProductsUseCase."""
    return ListProductsUseCase(product_repo)


async def get_create_category_use_case(
    category_repo: Annotated[ICategoryRepository, Depends(get_category_repo)],
) -> CreateCategoryUseCase:
    """Fabrica de CreateCategoryUseCase."""
    return CreateCategoryUseCase(category_repo)
