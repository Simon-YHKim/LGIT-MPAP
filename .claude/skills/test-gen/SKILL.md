---
name: test-gen
description: Use when the user asks to write tests, add test coverage, or create a test for a function or module—triggers include "테스트 작성", "write tests", "add test coverage", "test this function", "unit tests", "regression test". Produces meaningful deterministic tests covering the golden path, edge cases, and error paths.
version: 1.0.0
author: general-dev
---

# Test Generation Skill

Write tests that catch real bugs, not tests that exercise lines for coverage's sake.

## Workflow

1. **Discover the test framework**
   - Look for `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc.
   - Find existing test files and **match their style** (naming, structure, helpers, fixtures)
   - Identify the runner command (`pytest`, `npm test`, `cargo test`, `go test`)

2. **Read the code under test**
   - Understand its public contract (inputs, outputs, side effects)
   - List the branches and edge cases
   - Note any external dependencies that need mocking

3. **Plan the test cases** — Cover:
   - **Happy path** — typical valid input
   - **Edge cases** — empty, null, zero, negative, max size, unicode
   - **Error paths** — invalid input, network failure, permission denied
   - **Boundary conditions** — off-by-one, just-below/just-above thresholds
   - **Regression** — if fixing a bug, write a test that fails before the fix

4. **Write the tests**
   - One assertion per concept (multiple `expect` calls are fine if they test the same behavior)
   - Use descriptive names: `test_returns_empty_list_when_user_has_no_orders`
   - Arrange-Act-Assert structure
   - No magic numbers — name your fixtures
   - Tests must be **deterministic** — no real time, no random, no network

5. **Run and verify**
   - All new tests pass
   - Existing tests still pass
   - Try mutating the code under test — do your tests catch the mutation?

## Principles

- **Test behavior, not implementation.** Refactoring shouldn't break tests.
- **One concept per test.** A failing test should point at one specific cause.
- **Fast and isolated.** No shared state between tests, no I/O unless necessary.
- **No flaky tests.** If you can't make it deterministic, don't write it.

## Anti-patterns

- 🚫 Tests that mirror the implementation line-by-line
- 🚫 Mocking everything until the test no longer tests real behavior
- 🚫 `assert True` or tests with no assertions
- 🚫 Sleeping in tests to "wait for" async behavior — use proper sync primitives
- 🚫 Tests that only pass when run in a specific order
