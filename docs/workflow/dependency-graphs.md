# Dependency Graphs between Specs

```mermaid
graph TD
    %% F0: Preparation
    S01[Spec-01: Structure]
    S02[Spec-02: Development Environment]
    S03[Spec-03: Quality/CI]
    S04[Spec-04: Initial Docs]

    %% F1: Infrastructure
    S10[Spec-10: DB Configuration]
    S11[Spec-11: Schema/Migrations]
    S12[Spec-12: Indexes/Optimization]

    %% F2: Core
    S20[Spec-20: Entities]
    S21[Spec-21: Business Rules]
    S22[Spec-22: Protocols]

    %% F3: Adapters
    S30[Spec-30: Repository]
    S31[Spec-31: Materialized Views]
    S32[Spec-32: UoW/Transactions]

    %% F4: API
    S40[Spec-40: Use Cases]
    S41[Spec-41: DTOs]
    S42[Spec-42: FastAPI Routes]

    %% F5: Scheduler
    S50[Spec-50: APScheduler]
    S51[Spec-51: Retry/Concurrency]
    S52[Spec-52: Logging]

    %% F6: Testing
    S60[Spec-60: Unit Tests]
    S61[Spec-61: Integration Tests]
    S62[Spec-62: E2E/Latency]
    S63[Spec-63: Security]

    %% F7: Deployment
    S70[Spec-70: Docker Prod]
    S71[Spec-71: README/Demo]
    S72[Spec-72: CI/CD]

    %% Dependencies (Prerequisite -> Dependent)
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

> **Notes:**
> - The graph is a **DAG** without cycles.
> - Each arrow indicates `Prerequisite -> Dependent`. A spec can only start when all its incoming nodes are completed.
> - The structure follows Clean Architecture: dependency flows towards the domain.
> - When adding/modifying specs, update this diagram and verify that no cycles are introduced.
