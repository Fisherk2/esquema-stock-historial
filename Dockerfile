# Stage 1: Builder — instala dependencias en un prefix aislado
# para que el stage runtime no incluya pip ni caché de compilación.
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY . .

# Stage 2: Runtime — imagen mínima solo con Python y las dependencias
# instaladas. Sin herramientas de build, sin caché de pip.
# Ejecuta como usuario no-root (app) para seguridad.
FROM python:3.12-slim AS runtime

# OCI Image Spec labels — metadata estándar para registries
LABEL org.opencontainers.image.title="Stock Historial" \
      org.opencontainers.image.description="Sistema de gestión de inventario con Source of Truth Inmutable" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/Fisherk2/esquema-stock-historial" \
      org.opencontainers.image.licenses="MIT"

# Crear usuario no-root antes de COPY
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --shell /bin/bash --create-home app

WORKDIR /app

# Copiar dependencias y código con ownership correcto
COPY --from=builder --chown=app:app /install /usr/local
COPY --from=builder --chown=app:app /app .

# PYTHONUNBUFFERED: logs en tiempo real (sin buffer en stdout/stderr)
# PYTHONDONTWRITEBYTECODE: evita archivos .pyc en contenedor
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Ejecutar como usuario no-root
USER app

# Healthcheck usa el endpoint /v1/health para verificar que la app responde
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/v1/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
