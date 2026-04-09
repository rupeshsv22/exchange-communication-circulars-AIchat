---
name: python-testing
description: Use when writing or modifying pytest tests. Triggers on requests to add tests, fix failing tests, improve coverage, or write test fixtures. Covers pytest, pytest-asyncio, pytest-mock, and factory patterns.
---

# Python Testing

## Conventions
- Use `pytest` with `pytest-asyncio` for async code
- Test files: `tests/test_<module>.py`, mirror source tree
- Use `@pytest.fixture` for setup, scope appropriately (`function`, `module`, `session`)
- Parametrize with `@pytest.mark.parametrize` over loops
- Mock external I/O with `pytest-mock` (`mocker.patch`), never real network in unit tests
- Use `factory_boy` or plain factories for model instances
- Assert specific exceptions with `pytest.raises(SpecificError, match="...")`

## Structure
- Arrange-Act-Assert, blank lines between sections
- One logical assertion per test; multiple `assert` lines OK if same concept
- Test names: `test_<unit>_<scenario>_<expected>`

## Coverage
- Happy path + edge cases + error paths minimum
- Target branches, not just lines
- Run: `pytest -xvs --cov=app --cov-report=term-missing`

## Anti-patterns
- No `time.sleep` — use `freezegun` or async waits
- No shared mutable state across tests
- No testing framework internals