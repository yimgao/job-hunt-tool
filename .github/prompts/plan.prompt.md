---
agent: agent
description: Create a phased implementation plan before writing any code
---

# Implementation Planner

Before writing any code for this feature/task, produce a structured plan.

## Steps

1. **Clarify the goal** — restate the requirement in one sentence; flag any ambiguities.
2. **Research first** — search `doc/` and existing code for reusable patterns, utilities, or services. Do not reinvent.
3. **Identify dependencies** — external packages, API endpoints, DB changes, env vars needed.
4. **Break into phases** — structure work as ordered phases, each independently shippable:
   - Phase 1: DB schema / models
   - Phase 2: Service logic + unit tests
   - Phase 3: API endpoints + integration tests
   - Phase 4: Frontend / UI (if applicable) + E2E tests
5. **Identify risks** — anything that could block progress or cause regressions.
6. **Define done** — exact acceptance criteria (tests passing, coverage ≥ 80%, no lint errors, docs updated).

## Output Format

```
## Goal
[One-sentence summary]

## Reuse Opportunities
- [Existing service/pattern/schema]

## Dependencies
- [Package / API / DB change / env var]

## Phases
### Phase 1 — [Name]
- [ ] Task A
- [ ] Task B

### Phase 2 — [Name]
...

## Risks
- [Risk and mitigation]

## Definition of Done
- [ ] All tests pass (≥80% coverage)
- [ ] No new lint errors
- [ ] Matching doc/ updated
```

Apply JobHunt-Flow coding standards: type annotations, Pydantic schemas, immutable patterns, explicit error handling.
