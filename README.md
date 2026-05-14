# Plantilla Dev AI

Espacio de trabajo OpenCode para desarrollo asistido por IA con metodología Spec-Driven Development.

## Inicio Rápido

1. Lee [getting-started.md](docs/ai-agent-setup/getting-started.md) para la guía paso a paso
2. Usa `/spec` o `@skills/spec-driven-development/SKILL.md` para crear especificaciones
3. Usa `/implement` o `@skills/incremental-implementation/SKILL.md` para implementar incrementalmente
4. Consulta `@skills/using-agent-skills/SKILL.md` para descubrir qué skill usar
5. Ejecuta `/review` o `@skills/code-review-and-quality/SKILL.md` antes de hacer merge

> Para información detallada, consulta [USER_GUIDE.md](USER_GUIDE.md).

## Flujo de Trabajo

```mermaid
flowchart LR
    subgraph Define["DEFINIR"]
        A["Idea<br/>Refine"]
    end
    
    subgraph Plan["PLANEAR"]
        B["Spec<br/>PRD"]
    end
    
    subgraph Build["CONSTRUIR"]
        C["Code<br/>Impl"]
    end
    
    subgraph Verify["VERIFICAR"]
        D["Test<br/>Debug"]
    end
    
    subgraph Review["REVISAR"]
        E["QA<br/>Gate"]
    end
    
    subgraph Ship["LANZAR"]
        F["Go<br/>Live"]
    end

    A -->|" /spec "| B
    B -->|" /plan "| C
    C -->|" /build "| D
    D -->|" /test "| E
    E -->|" /review "| F
    F -->|" /ship "| G["Go Live"]

    style Define fill:#e1f5fe,stroke:#01579b
    style Plan fill:#e8f5e9,stroke:#1b5e20
    style Build fill:#fff3e0,stroke:#e65100
    style Verify fill:#fce4ec,stroke:#880e4f
    style Review fill:#f3e5f5,stroke:#4a148c
    style Ship fill:#e0f2f1,stroke:#004d40
```

### Ciclo Completo

| Fase | Comando | Skill Esencial |
|------|---------|----------------|
| Iniciar proyecto | `/spec` | `spec-driven-development` |
| Planificar | `/plan` | `planning-and-task-breakdown` |
| Construir | `/build` | `incremental-implementation` |
| Verificar | `/test` | `test-driven-development` |
| Revisar | `/review` | `code-review-and-quality` |
| Simplificar | `/code-simplify` | `code-simplification` |
| Lanzar | `/ship` | `shipping-and-launch` |

## Documentación

| Guía | Descripción |
|-----|-------------|
| [Inicio Rápido](docs/ai-agent-setup/getting-started.md) | Guía de 5 pasos para nuevos usuarios |
| [Guía Completa](USER_GUIDE.md) | Referencia detallada de todos los skills |
| [Guía de Agentes](AGENTS_GUIDE.md) | Personas de agentes y orquestación |
| [Contribuir](CONTRIBUTING.md) | Directrices de contribución (Español) |

## Herramientas de la Plantilla

- **Context7**: Fetch de documentación actualizada para cualquier librería o framework (`npx ctx7@latest setup`)

## Licencia

MIT