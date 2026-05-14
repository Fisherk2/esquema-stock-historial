# Reglas de Proceso

## Workflow Spec-Driven

1. **Especificación antes que Código:** Ningún archivo de implementación (`*.py`, `*.sql`) se creará sin un `specs/SPEC-XX.md` validado con contratos, payloads y criterios de aceptación.
2. **Orden Estricto del DAG:** Un spec solo pasa a `En Progreso` cuando **todas** sus dependencias estén `Completado`. Saltar dependencias rompe la trazabilidad y se rechaza automáticamente.
3. **Dirección de Dependencias (Clean Architecture):** El código siempre apunta hacia el dominio. `infrastructure` → `application` → `domain`. Se aplica DIP mediante `typing.Protocol` y mocks en testing.
4. **Inmutabilidad y Append-Only:** La tabla `movements` es sagrada. `UPDATE`/`DELETE` directos están prohibidos. Correcciones mediante movimientos compensatorios (`type: ADJUSTMENT`).
5. **SQL Explícito y Optimización:** Las consultas analíticas usan CTEs/Window Functions nativas. Prohibido usar ORM para queries de stock histórico. Cada query compleja debe incluir su `EXPLAIN ANALYZE`.
6. **Testing con Testcontainers:** Las pruebas de integración **no** mockean PostgreSQL. Se usa `testcontainers.postgres` para comportamiento 1:1 con producción.
7. **Commits y Versionado:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`). Cada merge a `main` debe cerrar un spec completo.
8. **Revisión de Deuda Técnica:** Si un spec lleva >48h en pendiente o bloqueado, se detienen specs dependientes y se escala a análisis de riesgo.

## Notas para la IA Agéntica

1. Inyectar siempre las restricciones de arquitectura (SRP, DIP, Inmutabilidad, SQL explícito, Testcontainers). Si una solicitud contradice estos principios, rechazar explícitamente y proponer alternativa alineada.
2. Antes de escribir implementación, verificar que el spec exista, tenga contratos definidos, y que sus dependencias estén completadas. Si falta información, solicitar aclaración.
3. Mantener registro mental del estado actual de cada spec. Al generar código, actualizar implícitamente el checklist y notificar al usuario.
4. Aplicar conceptos de Clean Architecture, Spec-Driven Development y SOLID para justificar decisiones técnicas.
5. Si una query supera `<100ms` en pruebas E2E, validar `EXPLAIN` primero, luego ajustar índices parciales o acotar rangos de fecha. Documentar en el spec.
6. Mantener tono técnico, pedagógico y directo. Usar Mermaid para diagramas, tablas para contratos, y bloques de código con sintaxis destacada.
