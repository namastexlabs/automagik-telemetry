# Code Coverage Standards

## Overview

This project maintains **100% code coverage** for both Python and TypeScript SDKs. All contributions must maintain this standard.

## Current Coverage Status

### Python
- **Statements**: 100% (931/931)
- **All source files**: 100%
- **Test suite**: 574 tests

### TypeScript
- **Statements**: 100%
- **Lines**: 100%
- **Functions**: 94.5%+
- **Branches**: 96.5%+
- **Test suite**: 402 tests

## Coverage Requirements

### For Contributors

1. **All new code must have 100% test coverage**
2. **Pre-commit hooks will verify coverage on push**
3. **CI/CD will fail if coverage drops below 100%**

### Running Coverage Locally

**Python:**
```bash
cd python
python3 -m pytest --cov=automagik_telemetry --cov-report=html -m "not integration"
# Open htmlcov/index.html to see detailed coverage
```

**TypeScript:**
```bash
cd typescript
npm test
# Open coverage/index.html to see detailed coverage
```

### Writing Tests for Coverage

#### Python Best Practices
- Test all code paths and branches
- Test error handling and exceptions
- Test edge cases and boundary conditions
- Use mocks for external dependencies
- Separate unit tests from integration tests

#### TypeScript Best Practices
- Test all exported functions and classes
- Test error paths and edge cases
- Mock external dependencies
- Use beforeEach/afterEach for test isolation

## Coverage Configuration

### Python (`pyproject.toml`)
```toml
[tool.pytest.ini_options]
addopts = "-v --cov=automagik_telemetry --cov-report=term-missing --cov-fail-under=100"

[tool.coverage.report]
fail_under = 100.0
show_missing = true
```

### TypeScript (`jest.config.js`)
```javascript
coverageThreshold: {
  global: {
    branches: 100,
    functions: 100,
    lines: 100,
    statements: 100,
  },
}
```

## CI/CD Enforcement

Both Python and TypeScript CI workflows enforce 100% coverage:
- `.github/workflows/python-ci.yml`
- `.github/workflows/typescript-ci.yml`

Pull requests without 100% coverage will fail CI checks.

## Troubleshooting

### Finding Uncovered Lines

**Python:**
```bash
pytest --cov=automagik_telemetry --cov-report=term-missing
```
Look for lines listed under "Missing" column.

**TypeScript:**
```bash
npm test
```
Look at "Uncovered Line #s" column in the output.

### Common Coverage Gaps

1. **Error paths**: Ensure all exception handling is tested
2. **Edge cases**: Test boundary conditions
3. **Type conversions**: Test all attribute types
4. **Optional parameters**: Test with and without optional args
5. **Async code**: Test async/await paths

## Maintenance

Coverage is automatically verified:
- ✅ Pre-push hooks (local development)
- ✅ CI/CD on every PR
- ✅ Monthly audits

## Questions?

See `CONTRIBUTING.md` for general contribution guidelines.
