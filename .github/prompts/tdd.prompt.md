---
agent: agent
description: Test-driven development cycle — write the test first, then implement
---

# TDD Workflow

Follow the RED → GREEN → IMPROVE cycle strictly. Do not write implementation code before a failing test exists.

## Cycle

### 1. RED — Write the failing test
- Write a test that describes the desired behavior.
- Run it. It **must fail** before continuing.
- Use Arrange-Act-Assert structure.
- Name tests descriptively: `returns_empty_array_when_no_items_match_filter`, not `test_item_filter`.

### 2. GREEN — Minimal implementation
- Write the **minimum** code needed to make the test pass.
- Do not over-engineer at this stage.
- Run the test again — it **must pass**.

### 3. IMPROVE — Refactor
- Clean up duplication, naming, structure.
- Keep all tests passing after each change.
- Check coverage: target **≥ 80%**.

## Test Layer Checklist

- [ ] **Unit** — pure functions, utilities, isolated services
- [ ] **Integration** — API endpoints, database operations, service boundaries
- [ ] **E2E** — at least one critical user flow covered

## Python/FastAPI Testing

```python
# pytest + pytest-asyncio for async endpoints
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_match_endpoint_returns_report():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/match", json={...})
        assert resp.status_code == 200
        assert "match_score" in resp.json()
```

## Quality Gates

Before marking the feature done:
- [ ] All tests pass
- [ ] Coverage ≥ 80%
- [ ] No skipped/commented-out tests
- [ ] Edge cases covered: empty input, nulls, boundary values, error paths

## Anti-patterns to Avoid

- Writing implementation before tests
- Testing implementation details instead of behavior
- Mocking too deeply (prefer integration tests over excessive mocks)
- Assertions that always pass
