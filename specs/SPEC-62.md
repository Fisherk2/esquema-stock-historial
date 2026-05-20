# SPEC-62: Tests E2E & Latencia <100ms

**Fase:** F6 — Testing Integral
**Dependencias:** Spec-42 (Rutas FastAPI) ✅ Completado, Spec-61 (Integración Edge Cases) — Pre-requisito inmediato
**Prioridad:** Alta
**Estado:** Aprobado

---

## Objective

Implementar la suite de tests E2E (end-to-end) que valida el **core product promise** del sistema: consultas de stock histórico en **<100ms**. Esta fase introduce `pytest-benchmark` para medir latencia de endpoints críticos, tests de flujos HTTP completos (crear categoría → producto → movimiento → consultar stock), y validación de contratos OpenAPI contra esquemas Pydantic. Los tests E2E usan la misma infraestructura de testcontainers que los tests de integración, pero con foco en latencia, flujos transversales, y contratos de API.

**Principios de diseño:**
- **SLA gate: p95 < 100ms** — el 95% de las consultas de stock deben responder en menos de 100ms
- **In-process benchmark** — `pytest-benchmark` mide latencia dentro del proceso de test (no red externa)
- **Flujos transversales** — no testean un endpoint aislado sino la secuencia completa de operaciones
- **Contratos OpenAPI** — las respuestas JSON deben coincidir con los esquemas Pydantic definidos
- **Cero regresiones** — todos los tests existentes deben pasar

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| `pytest-benchmark` (no Locust/k6) | In-process, sin servidor externo. Determinista. Se integra con pytest. Suficiente para medir latencia del handler + DB |
| **p95 < 100ms** como gate | p95 permite 5% de outliers (overhead de testcontainers). max y p99 son demasiado estrictos para CI con contenedores |
| `httpx.AsyncClient` + `ASGITransport` | Ya usado en integración. Misma infraestructura, sin servidor separado |
| E2E reutiliza `db_pool`/`db_clean` | Un solo contenedor PostgreSQL para toda la sesión. Consistente con integración |
| Benchmark con `--benchmark-min-rounds=5` | Mínimo 5 rondas para estadística significativa. Warmup de 1 ronda |
| Custom pytest hook para SLA gate | Hook `pytest_benchmark_update_machine_info` o `conftest.py` que falla si p95 > 100ms |

---

## Benchmark Configuration

### `pyproject.toml` additions

```toml
[tool.pytest.ini_options]
# ... existing config ...
markers = [
    "benchmark: marks tests as benchmark (deselect with '-m \"not benchmark\"')",
    "e2e: marks tests as end-to-end",
]
```

### `tests/e2e/conftest.py`

```python
"""Fixtures compartidos para tests E2E.

Proporciona el fixture ``api_client`` reutilizado de integración,
más configuración de benchmark para medición de latencia.

El SLA gate se implementa como un custom pytest hook que verifica
que el p95 de los benchmarks de stock esté bajo 100ms.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
from httpx import ASGITransport

from src.main import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    import asyncpg


@pytest.fixture
async def api_client(
    db_pool: asyncpg.Pool, db_clean: asyncpg.Pool
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Fixture E2E: cliente HTTP async contra la app con datos limpios.

    Reutiliza la misma infraestructura que los tests de integración:
    testcontainers PostgreSQL, migraciones, seed data.
    """
    from src.adapters.api.dependencies import get_db_pool

    app = create_app()

    async def _override_db_pool() -> asyncpg.Pool:
        return db_pool

    app.dependency_overrides[get_db_pool] = _override_db_pool

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ── SLA Gate: p95 < 100ms para stock queries ─────────────────────────────

STOCK_SLA_MS = 100.0


def pytest_benchmark_update_machine_info(config, machine_info):
    """Hook: añade info del entorno de benchmark."""
    machine_info["testcontainers"] = True


@pytest.hookimpl(hookwrapper=True)
def pytest_benchmark_compare_stats(config, bench_id, compare, current):
    """Hook: verifica SLA después de cada benchmark de stock."""
    yield
    # Solo verificar SLA en benchmarks de stock
    if "stock" in bench_id and current:
        stats = current.stats
        if stats and hasattr(stats, "p95"):
            p95_ms = stats.p95 * 1000  # Convertir segundos a ms
            if p95_ms > STOCK_SLA_MS:
                pytest.fail(
                    f"SLA violation: {bench_id} p95={p95_ms:.1f}ms > {STOCK_SLA_MS}ms"
                )
```

---

## E2E Test: Latencia de Stock

### `tests/e2e/test_stock_latency.py`

```python
"""Tests E2E de latencia para consultas de stock.

Valida el SLA core del sistema: consultas de stock actual e histórico
deben responder en p95 < 100ms. Usa pytest-benchmark para medición
estadística con múltiples rondas.

El SLA se mide in-process (httpx.AsyncClient + ASGITransport),
sin overhead de red. En producción con red, se espera que la
latencia se mantenga <100ms gracias a la vista materializada.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import httpx


# ── Helpers ──────────────────────────────────────────────────────────────

async def _setup_product_with_movements(client: httpx.AsyncClient) -> int:
    """Crea categoría, producto y movimientos para tests de latencia."""
    # Crear categoría
    resp = await client.post("/v1/categories", json={
        "name": f"bench-cat-{id(client)}",
        "description": "Benchmark category",
    })
    cat_id = resp.json()["id"]

    # Crear producto
    resp = await client.post("/v1/products", json={
        "sku": f"BENCH-{id(client)}",
        "name": "Benchmark Product",
        "unit_of_measure": "unit",
        "category_id": cat_id,
        "min_stock_threshold": 10,
    })
    product_id = resp.json()["id"]

    # Crear movimientos
    for _ in range(10):
        await client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 50,
            "reference": "bench",
        })

    return product_id


# ── SLA Tests ────────────────────────────────────────────────────────────

class TestStockLatency:
    """SLA: consultas de stock en p95 < 100ms."""

    @pytest.mark.benchmark(group="stock-current")
    async def test_current_stock_latency(
        self, benchmark, api_client: httpx.AsyncClient
    ) -> None:
        """SLA: GET /v1/stock/{id}/current en p95 < 100ms."""
        product_id = await _setup_product_with_movements(api_client)

        # Benchmark: medir latencia de la consulta
        result = benchmark(
            lambda: asyncio.run(
                api_client.get(f"/v1/stock/{product_id}/current")
            )
        )
        assert result.status_code == 200
        data = result.json()
        assert "current_stock" in data
        assert data["current_stock"] == 500.0  # 10 × 50 IN

    @pytest.mark.benchmark(group="stock-at-date")
    async def test_stock_at_date_latency(
        self, benchmark, api_client: httpx.AsyncClient
    ) -> None:
        """SLA: GET /v1/stock/{id}/at-date?date=... en p95 < 100ms."""
        from datetime import datetime, timezone

        product_id = await _setup_product_with_movements(api_client)
        now = datetime.now(timezone.utc).isoformat()

        result = benchmark(
            lambda: asyncio.run(
                api_client.get(f"/v1/stock/{product_id}/at-date?date={now}")
            )
        )
        assert result.status_code == 200
        data = result.json()
        assert "stock" in data

    @pytest.mark.benchmark(group="stock-current")
    async def test_current_stock_no_movements_latency(
        self, benchmark, api_client: httpx.AsyncClient
    ) -> None:
        """SLA: stock de producto sin movimientos también < 100ms."""
        # Crear categoría y producto sin movimientos
        resp = await api_client.post("/v1/categories", json={
            "name": f"empty-cat-{id(api_client)}",
        })
        cat_id = resp.json()["id"]

        resp = await api_client.post("/v1/products", json={
            "sku": f"EMPTY-{id(api_client)}",
            "name": "No Movements Product",
            "unit_of_measure": "unit",
            "category_id": cat_id,
        })
        product_id = resp.json()["id"]

        result = benchmark(
            lambda: asyncio.run(
                api_client.get(f"/v1/stock/{product_id}/current")
            )
        )
        assert result.status_code == 200
        assert result.json()["current_stock"] == 0.0
```

---

## E2E Test: Flujos Completos

### `tests/e2e/test_full_flows.py`

```python
"""Tests E2E de flujos HTTP completos.

Valida las secuencias de operaciones que un usuario real ejecutaría:
1. Crear categoría → producto → movimiento → consultar stock
2. Registrar OUT cuando hay stock insuficiente → error
3. Consultar stock en múltiples fechas → consistencia histórica
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import httpx


class TestFullInventoryFlow:
    """Flujo completo: categoría → producto → movimiento → stock."""

    async def test_create_and_query_stock(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Flujo feliz: crear categoría, producto, movimiento, consultar stock."""
        # 1. Crear categoría
        resp = await api_client.post("/v1/categories", json={
            "name": "Electrónicos",
            "description": "Dispositivos electrónicos",
        })
        assert resp.status_code == 201
        cat_id = resp.json()["id"]

        # 2. Crear producto
        resp = await api_client.post("/v1/products", json={
            "sku": "ELEC-001",
            "name": "Monitor 27\"",
            "unit_of_measure": "unit",
            "category_id": cat_id,
            "min_stock_threshold": 5,
        })
        assert resp.status_code == 201
        product_id = resp.json()["id"]

        # 3. Registrar entrada de stock
        resp = await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 100,
            "reference": "PO-2026-001",
        })
        assert resp.status_code == 201
        movement_id = resp.json()["id"]
        assert movement_id > 0

        # 4. Consultar stock actual
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.status_code == 200
        assert resp.json()["current_stock"] == 100.0

        # 5. Registrar salida
        resp = await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "OUT",
            "quantity": 30,
            "reference": "SO-2026-001",
        })
        assert resp.status_code == 201

        # 6. Verificar stock actualizado
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.status_code == 200
        assert resp.json()["current_stock"] == 70.0

    async def test_insufficient_stock_flow(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Flujo de error: OUT con stock insuficiente → 409."""
        # Setup: categoría + producto con 10 unidades
        cat = await api_client.post("/v1/categories", json={"name": "Test"})
        product = await api_client.post("/v1/products", json={
            "sku": "TEST-INSUF",
            "name": "Test Product",
            "unit_of_measure": "unit",
            "category_id": cat.json()["id"],
        })
        product_id = product.json()["id"]

        await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 10,
        })

        # Intentar OUT de 20 (solo hay 10)
        resp = await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "OUT",
            "quantity": 20,
        })
        assert resp.status_code == 409
        body = resp.json()
        assert "INSUFFICIENT_STOCK" in body["error"]["code"]

    async def test_historical_stock_consistency(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Flujo histórico: stock en diferentes fechas es consistente."""
        # Setup
        cat = await api_client.post("/v1/categories", json={"name": "Hist"})
        product = await api_client.post("/v1/products", json={
            "sku": "HIST-001",
            "name": "Historical Product",
            "unit_of_measure": "unit",
            "category_id": cat.json()["id"],
        })
        product_id = product.json()["id"]

        # Stock actual = 0
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.json()["current_stock"] == 0.0

        # Registrar entrada
        await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 50,
        })

        # Stock actual ahora = 50
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.json()["current_stock"] == 50.0

        # Stock en fecha pasada (antes del movimiento) = 0
        past_date = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        resp = await api_client.get(
            f"/v1/stock/{product_id}/at-date?date={past_date}"
        )
        assert resp.json()["stock"] == 0.0
```

---

## E2E Test: Contratos OpenAPI

### `tests/e2e/test_openapi_contracts.py`

```python
"""Tests E2E de validación de contratos OpenAPI.

Verifica que las respuestas JSON de los endpoints coinciden con
los esquemas Pydantic definidos en src/application/dtos/.
Usa model_validate() para validar cada respuesta contra su DTO.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.application.dtos.movement_dtos import MovementOutput, MovementListOutput
from src.application.dtos.stock_dtos import CurrentStockOutput, StockAtDateOutput
from src.application.dtos.product_dtos import ProductOutput, ProductListOutput
from src.application.dtos.category_dtos import CategoryOutput

if TYPE_CHECKING:
    import httpx


class TestOpenAPIContracts:
    """Las respuestas de la API deben validar contra sus DTOs Pydantic."""

    async def test_movement_response_contract(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """POST /v1/movements retorna MovementOutput válido."""
        # Setup
        cat = await api_client.post("/v1/categories", json={"name": "Contract"})
        product = await api_client.post("/v1/products", json={
            "sku": "CONTRACT-001",
            "name": "Contract Product",
            "unit_of_measure": "unit",
            "category_id": cat.json()["id"],
        })
        product_id = product.json()["id"]

        resp = await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 25,
        })
        assert resp.status_code == 201
        # Validar contra Pydantic model
        movement = MovementOutput.model_validate(resp.json())
        assert movement.id > 0
        assert movement.product_id == product_id
        assert movement.movement_type == "IN"
        assert movement.quantity == 25

    async def test_current_stock_response_contract(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """GET /v1/stock/{id}/current retorna CurrentStockOutput válido."""
        # Setup
        cat = await api_client.post("/v1/categories", json={"name": "Stock"})
        product = await api_client.post("/v1/products", json={
            "sku": "STOCK-CONTRACT",
            "name": "Stock Contract Product",
            "unit_of_measure": "unit",
            "category_id": cat.json()["id"],
        })
        product_id = product.json()["id"]

        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.status_code == 200
        stock = CurrentStockOutput.model_validate(resp.json())
        assert stock.product_id == product_id

    async def test_product_list_response_contract(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """GET /v1/products retorna ProductListOutput válido."""
        resp = await api_client.get("/v1/products")
        assert resp.status_code == 200
        product_list = ProductListOutput.model_validate(resp.json())
        assert isinstance(product_list.items, list)
        assert product_list.total >= 0

    async def test_category_response_contract(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """POST /v1/categories retorna CategoryOutput válido."""
        resp = await api_client.post("/v1/categories", json={
            "name": "Contract Category",
        })
        assert resp.status_code == 201
        category = CategoryOutput.model_validate(resp.json())
        assert category.id > 0
        assert category.name == "Contract Category"
```

---

## Files

| File | Description | Action |
|------|-------------|--------|
| `tests/e2e/conftest.py` | Fixtures E2E + benchmark config + SLA gate | NEW |
| `tests/e2e/test_stock_latency.py` | SLA <100ms benchmark tests | NEW |
| `tests/e2e/test_full_flows.py` | Flujos HTTP end-to-end completos | NEW |
| `tests/e2e/test_openapi_contracts.py` | Validación contra esquemas Pydantic | NEW |
| `pyproject.toml` | +pytest-benchmark, markers | MODIFY |
| `requirements.txt` | +pytest-benchmark | MODIFY |

---

## Acceptance Criteria

- [ ] `pytest-benchmark` añadido a `requirements.txt` y `pyproject.toml`
- [ ] `tests/e2e/conftest.py` con fixture `api_client` + benchmark config + SLA gate hook
- [ ] Tests de latencia: `/v1/stock/{id}/current` p95 < 100ms
- [ ] Tests de latencia: `/v1/stock/{id}/at-date` p95 < 100ms
- [ ] Tests de latencia: producto sin movimientos también < 100ms
- [ ] Tests de flujos completos: categoría → producto → movimiento → stock
- [ ] Tests de flujos completos: OUT con stock insuficiente → 409
- [ ] Tests de flujos completos: consistencia histórica entre fechas
- [ ] Tests de contratos OpenAPI: respuestas validan contra Pydantic DTOs
- [ ] SLA gate falla si p95 > 100ms en benchmarks de stock
- [ ] 0 regresiones en tests existentes
- [ ] `make lint` pasa sin errores

---

## Testing Strategy

- **Benchmark tests:** miden latencia in-process con `pytest-benchmark`. Mínimo 5 rondas, warmup de 1. SLA gate en p95
- **Full flow tests:** secuencia de operaciones HTTP que simulan uso real. Verifican consistencia de datos
- **OpenAPI contract tests:** validan respuestas JSON contra modelos Pydantic con `model_validate()`
- **Ejecución:** `pytest tests/e2e/ -v` o `pytest tests/e2e/ --benchmark-only` para solo benchmarks

### Ejecución de benchmarks

```bash
# Todos los E2E tests (incluye benchmarks)
pytest tests/e2e/ -v

# Solo benchmarks
pytest tests/e2e/ -v --benchmark-only

# Benchmarks con más rondas para análisis
pytest tests/e2e/ -v --benchmark-only --benchmark-min-rounds=20

# Guardar resultados para comparación
pytest tests/e2e/ -v --benchmark-only --benchmark-json=bench_results.json
```

---

## Resolved Questions

| # | Pregunta | Decisión | Rationale |
|---|----------|----------|-----------|
| F6-62-Q1 | ¿Herramienta de benchmark? | **pytest-benchmark** | In-process, sin servidor externo. Determinista. Se integra con pytest. Locust/k6 son para load testing externo |
| F6-62-Q2 | ¿Percentil SLA? | **p95 < 100ms** | Permite 5% de outliers por overhead de testcontainers. max y p99 son demasiado estrictos para CI con contenedores |
| F6-62-Q3 | ¿Mínimo de rondas? | **5** (warmup=1) | Estadística mínima significativa. 5 rondas × 2 endpoints × 2 casos = 20 mediciones totales en ~5s |
| F6-62-Q4 | ¿SLA gate como pytest hook o assertion? | **Pytest hook** | Falla automáticamente si p95 > 100ms. No requiere assertion manual en cada test. Más limpio |
| F6-62-Q5 | ¿Contratos OpenAPI con schema JSON o Pydantic? | **Pydantic model_validate()** | Los DTOs ya existen. Validar contra ellos es más directo y mantiene una sola fuente de verdad |
