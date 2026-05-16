---
description: Conduct a five-axis code review — correctness, readability, architecture, security, performance
agent: analysis
---

Invoke the @skills/code-review-and-quality/SKILL.md.

Review the current changes (staged or recent commits) across all five axes:

1. **Correctness** — Does it match the spec? Edge cases handled? Tests adequate?
2. **Readability** — Clear names? Straightforward logic? Well-organized?
3. **Architecture** — Follows existing patterns? Clean boundaries? Right abstraction level?
4. **Security** — Input validated? Secrets safe? Auth checked? (Use @skills/security-and-hardening/SKILL.md)
5. **Performance** — No N+1 queries? No unbounded ops? (Use @skills/performance-optimization/SKILL.md)

Categorize findings as Critical, Important, or Suggestion.
Output a structured review with specific file:line references and fix recommendations.