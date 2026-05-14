# Getting Started

> **Looking for the complete reference guide?** See [USER_GUIDE.md](../../USER_GUIDE.md) for the full documentation.

**Production-grade engineering skills for AI coding agents.** Skills encode workflows, quality gates, and best practices that senior engineers use when building software.

## Quick Start (5 Steps)

### 1. Install Context7

```bash
npx ctx7@latest setup
```

This gives you access to the latest documentation and API references for any library or framework you'll be using.

### 2. Load the Meta-Skill

Start with `@skills/using-agent-skills/SKILL.md` to discover which skill applies to your current task. This meta-skill contains:

- A **flowchart** that maps task types to the appropriate skill
- **Core operating behaviors** (surface assumptions, manage confusion, push back when warranted)
- **Failure modes** to avoid
- **Lifecycle sequences** for complete features

### 3. Choose a Skill

Browse the `skills/` directory. Each skill contains:
- **When to use** — triggers that indicate this skill applies
- **Process** — step-by-step workflow
- **Verification** — how to confirm the work is done

### 4. Load the Skill

Copy the `SKILL.md` content into your agent's system prompt, rules file, or conversation.

### 5. Start with Essentials

1. **spec-driven-development** — Define what to build
2. **test-driven-development** — Prove it works
3. **code-review-and-quality** — Verify quality before merge

## Recommended Setup

### Full Lifecycle

For comprehensive coverage, follow this workflow:

```
Starting a project:  /spec → /plan
During development:   /build → /test
Before merge:        /review
Before deploy:       /ship
```

### Context-Aware Loading

Don't load all skills at once — it wastes context. Load skills relevant to the current task:

- Working on UI? → Load `frontend-ui-engineering`
- Debugging? → Load `debugging-and-error-recovery`
- Setting up CI? → Load `ci-cd-and-automation`

## Tips

1. **Start with `/spec`** for any non-trivial work
2. **Always use `/test`** when writing code
3. **Don't skip verification steps** — they're the whole point
4. **Use `/review`** before merging — different perspectives catch issues
5. **Use `/ship`** for production deployments — includes parallel review

## Next Steps

For detailed information on:
- **All 21 base skills** → See [USER_GUIDE.md](../../USER_GUIDE.md#all-21-base-skills)
- **Agent personas** → See [AGENTS_GUIDE.md](../../AGENTS_GUIDE.md)
- **OpenCode setup** → See [opencode-setup.md](opencode-setup.md)
- **Creating new skills** → See [USER_GUIDE.md](../../USER_GUIDE.md#creating-a-new-skill)
