# Grafos de Dependencia entre Specs

```mermaid
graph TD
    %% F0: Preparación
    S01[Spec-01: Estructura]
    S02[Spec-02: Entorno Dev]
    S03[Spec-03: Calidad/CI]
    S04[Spec-04: Doc Inicial]

    %% F1: Infraestructura
    S10[Spec-10: Config DB]
    S11[Spec-11: Esquema/Mig]
    S12[Spec-12: Índices/Opt]

    %% F2: Núcleo
    S20[Spec-20: Entidades]
    S21[Spec-21: Reglas]
    S22[Spec-22: Protocolos]

    %% F3: Adaptadores
    S30[Spec-30: Repositorio]
    S31[Spec-31: Vistas Mat.]
    S32[Spec-32: UoW/Trans]

    %% F4: API
    S40[Spec-40: Use Cases]
    S41[Spec-41: DTOs]
    S42[Spec-42: Rutas FastAPI]

    %% F5: Scheduler
    S50[Spec-50: APScheduler]
    S51[Spec-51: Retry/Conc]
    S52[Spec-52: Logging]

    %% F6: Testing
    S60[Spec-60: Unit Tests]
    S61[Spec-61: Integ Tests]
    S62[Spec-62: E2E/Latency]
    S63[Spec-63: Security]

    %% F7: Despliegue
    S70[Spec-70: Docker Prod]
    S71[Spec-71: README/Demo]
    S72[Spec-72: CI/CD]

    %% Dependencies (Prerrequisito -> Dependiente)
    S01 --> S02
    S02 --> S03
    S01 --> S03
    S01 --> S04
    S02 --> S10
    S10 --> S11
    S11 --> S12
    S11 --> S20
    S20 --> S21
    S20 --> S22
    S12 --> S30
    S22 --> S30
    S30 --> S31
    S12 --> S31
    S30 --> S32
    S21 --> S40
    S22 --> S40
    S32 --> S40
    S40 --> S41
    S40 --> S42
    S41 --> S42
    S31 --> S50
    S42 --> S50
    S40 --> S51
    S50 --> S51
    S42 --> S52
    S51 --> S52
    S21 --> S60
    S22 --> S60
    S40 --> S60
    S30 --> S61
    S31 --> S61
    S60 --> S61
    S42 --> S62
    S61 --> S62
    S42 --> S63
    S52 --> S63
    S42 --> S70
    S50 --> S70
    S62 --> S70
    S62 --> S71
    S70 --> S71
    S03 --> S72
    S60 --> S72
    S70 --> S72
```

> **Notas:**
> - El grafo es un **DAG** sin ciclos.
> - Cada flecha indica `Prerrequisito -> Dependiente`. Un spec solo puede iniciar cuando todos sus nodos entrantes estén completados.
> - La estructura sigue Clean Architecture: dependencia hacia el dominio.
> - Al añadir/modificar specs, actualizar este diagrama y verificar que no se introduzcan ciclos.
