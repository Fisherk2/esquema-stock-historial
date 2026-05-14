# Contribuir

¡Gracias por tu interés en contribuir! Este proyecto es una colección de skills de ingeniería de grado de producción para agentes de codificación AI.

---

## Añadir una Nueva Skill

1. Crea un directorio bajo `skills/` con un nombre en kebab-case
2. Añade un `SKILL.md` siguiendo el formato en [docs/ai-agent-setup/skill-anatomy.md](docs/ai-agent-setup/skill-anatomy.md)
3. Incluye frontmatter YAML con los campos `name` y `description`
4. Asegúrate de que la `description` indique brevemente qué hace la skill (tercera persona), seguida de las condiciones de activación "Use when"
5. **Actualiza la documentación de skills disponibles** para reflejar la nueva skill:
   - **`docs/ai-agent-setup/getting-started.md`** — Actualiza la referencia del número de skills en la sección "Next Steps"
   - **`skills/using-agent-skills/SKILL.md`** — Añade la skill al árbol de "Skill Discovery" (bajo la subsección "Skill Extras") y a la tabla "Quick Reference" con la fase "Extra"
   - **`USER_GUIDE.md`**: Añade la skill a la tabla "Skill Extras" y actualiza el árbol de estructura del proyecto en "Project Structure".
     - Si la skill es una **Skill Extra** (no forma parte del flujo base), **no modifiques el título "All X Base Skills"** — ese número solo cambia cuando se añade o elimina una skill del flujo base (DEFINE → PLAN → BUILD → VERIFY → REVIEW → SHIP + meta‑skill).

### Estándar de Calidad de las Skills

Las skills deben ser:

- **Específicas** — Pasos accionables, no consejos vagos
- **Verificables** — Criterios de salida claros con requisitos de evidencia
- **Probadas en batalla** — Basadas en flujos de trabajo de ingeniería reales, no ideales teóricos
- **Mínimas** — Solo el contenido necesario para guiar al agente correctamente

### Estructura

Toda nueva skill debe tener:

- `SKILL.md` en el directorio de la skill
- Frontmatter YAML con `name` y `description` válidos

Las nuevas skills deben seguir generalmente la anatomía estándar:

- **Overview** — Qué hace esta skill y por qué importa
- **When to Use** — Condiciones de activación
- **Process** — Flujo de trabajo paso a paso
- **Common Rationalizations** — Excusas que los agentes usan para saltarse pasos, con refutaciones
- **Red Flags** — Señales de advertencia de que la skill se está aplicando incorrectamente
- **Verification** — Cómo confirmar que la skill se aplicó correctamente

### Qué No Hacer

- No dupliques contenido entre skills — referencia otras skills en su lugar
- No añadas skills que sean consejos vagos en lugar de procesos accionables
- No crees archivos de soporte a menos que el contenido supere las 100 líneas
- No pongas material de referencia dentro de los directorios de skills — usa `references/` en su lugar

---

## Añadir un Nuevo Agente

Para añadir un nuevo agente especializado, sigue estos pasos:

### Pasos

1. Crea `agents/<nombre-agente>.md` con el mismo formato de frontmatter que los agentes existentes
2. Define el rol, alcance, formato de salida y reglas
3. Añade un bloque **Composition** al final (Invoke directly when / Invoke via / Do not invoke from another persona)
4. Añade el agente a la tabla en [AGENTS_GUIDE.md](AGENTS_GUIDE.md)
5. **Actualiza la sección `## Agent Personas` en [USER_GUIDE.md](USER_GUIDE.md)** con el nuevo agente
6. Si el agente habilita un nuevo patrón de orquestación, documéntalo en `references/orchestration-patterns.md`

### Reglas para Agentes

- Un agente es un único rol con un único formato de salida. Si necesitas un segundo rol, crea un segundo agente.
- **Los agentes no invocan a otros agentes.** La composición es trabajo de los comandos o del usuario.
- Un agente puede invocar skills (el *cómo*).
- Todo archivo de agente termina con un bloque "Composition" indicando dónde encaja.

### Estructura de un Agente

```
agents/
  <nombre-agente>.md    # Formato frontmatter:
                        # ---
                        # name: nombre-agente
                        # role: Título del rol
                        # perspective: Perspectiva especializada
                        # ---
                        #
                        # [Contenido del agente]
                        #
                        # ## Composition
                        # [Dónde se invoca este agente]
```

### Ejemplo de Frontmatter

```yaml
---
name: code-reviewer
role: Senior Staff Engineer
perspective: Realiza revisiones de código de cinco ejes con el estándar de un ingeniero senior
---
```

### Agentes Existentes

| Agente | Rol | Propósito |
|--------|-----|----------|
| [analysis](agents/analysis.md) | Architect of Specifications | Transforma ideas y requisitos en planes de ejecución detallados sin generar código |
| [code-reviewer](agents/code-reviewer.md) | Senior Staff Engineer | Revisión de cinco ejes antes del merge |
| [security-auditor](agents/security-auditor.md) | Security Engineer | Detección de vulnerabilidades, auditoría OWASP |
| [test-engineer](agents/test-engineer.md) | QA Engineer | Estrategia de pruebas, análisis de cobertura, patrón Prove-It |

### Qué No Hacer

- No crear agentes que invoquen a otros agentes
- No añadir múltiples roles en un solo agente
- No duplicar funcionalidad existente

### Referencias

Para más información sobre orquestación de agentes, patrones válidos e inválidos, y ejemplos de composición, ver:
- [AGENTS_GUIDE.md](AGENTS_GUIDE.md) — Guía completa de agentes y orquestación
- [references/orchestration-patterns.md](references/orchestration-patterns.md) — Catálogo de patrones de orquestación

---

## Modificar Skills Existentes

- Mantén los cambios enfocados y mínimos
- Preserva la estructura y el tono existentes
- Verifica que el frontmatter YAML siga siendo válido después de las ediciones

---

## Reportar Problemas

Abre un issue si encuentras:

- Una skill que da orientación incorrecta o desactualizada
- Cobertura faltante para un flujo de trabajo de ingeniería común
- Inconsistencias entre skills

---

## Licencia

Al contribuir, aceptas que tus contribuciones serán licenciadas bajo la Licencia MIT.