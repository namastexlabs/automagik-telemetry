# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Automagik Telemetry** is a privacy-first, zero-dependency OpenTelemetry SDK with dual implementations in Python and TypeScript. The project provides production-ready telemetry for traces, metrics, and logs with 100% test coverage across both SDKs.

### Key Architectural Principles

1. **Zero Dependencies**: Both SDKs use only standard library HTTP clients
2. **Privacy-First**: Opt-in by default, auto-disabled in development environments
3. **Dual Backend Support**:
   - OTLP backend for production SaaS (default)
   - ClickHouse backend for self-hosted deployments (direct insertion)
4. **100% Test Coverage**: Enforced in CI for both SDKs
5. **Identical APIs**: Python and TypeScript SDKs provide feature parity

## Repository Structure

```
.
├── python/               # Python SDK (3.12+)
│   ├── src/automagik_telemetry/
│   │   ├── client.py    # Main telemetry client
│   │   ├── config.py    # Configuration management
│   │   ├── schema.py    # OTLP schema definitions
│   │   ├── privacy.py   # PII detection and sanitization
│   │   ├── opt_in.py    # Opt-in/opt-out handling
│   │   └── backends/
│   │       └── clickhouse.py  # ClickHouse backend
│   └── tests/           # 100% coverage test suite
│
├── typescript/          # TypeScript SDK (Node.js 18+)
│   ├── src/
│   │   ├── client.ts    # Main telemetry client
│   │   ├── config.ts    # Configuration management
│   │   ├── schema.ts    # OTLP schema definitions
│   │   ├── privacy.ts   # PII detection and sanitization
│   │   ├── opt-in.ts    # Opt-in/opt-out handling
│   │   └── backends/
│   │       ├── index.ts       # OTLP backend
│   │       └── clickhouse.ts  # ClickHouse backend
│   └── tests/           # 100% coverage test suite
│
├── infra/               # Self-hosting infrastructure
│   ├── docker-compose.yml
│   ├── Makefile         # Infrastructure commands
│   └── scripts/
│
├── docs/                # Comprehensive documentation
└── examples/            # Example implementations
```

## Development Commands

### Python SDK

```bash
cd python

# Install dependencies (editable install)
pip install -e ".[dev]"

# Run tests (must maintain 100% coverage)
pytest

# Run tests with coverage report
pytest --cov=automagik_telemetry --cov-report=html --cov-report=term-missing

# Run only unit tests (exclude integration tests)
pytest -m "not integration"

# Type checking (strict mode enforced)
mypy src

# Linting and formatting
ruff check src tests
ruff format src tests

# Run specific test file
pytest tests/test_client.py -v

# Run with verbose output
pytest -vv
```

### TypeScript SDK

```bash
cd typescript

# Install dependencies
pnpm install

# Build the SDK
pnpm build

# Run tests (must maintain 100% coverage)
pnpm test

# Run tests with coverage report
pnpm test -- --coverage

# Run only unit tests (exclude integration tests)
pnpm test:unit

# Run integration tests (requires local infrastructure)
pnpm test:integration

# Linting
pnpm lint

# Format code
pnpm format

# Type checking
pnpm exec tsc --noEmit
```

### Infrastructure (Self-Hosting)

```bash
cd infra

# Start all services (ClickHouse, Collector, Grafana)
make start

# Check service health
make health

# Send test data
make test

# View logs
make logs

# Stop services
make stop

# Clean all data (destructive)
make clean
```

## Testing Requirements

### Coverage Enforcement

Both SDKs **MUST maintain 100% test coverage**. CI will fail if coverage drops below 100%.

- Python: `pytest --cov-fail-under=100`
- TypeScript: Coverage verified in CI with assertions

### Test Categories

1. **Unit Tests**: Test individual functions and classes
2. **Integration Tests**: Test OTLP/ClickHouse communication (marked with `-m integration`)
3. **Performance Tests**: Benchmark overhead (marked with `-m performance`)
4. **Edge Cases**: Test error handling, network failures, opt-out scenarios

### Running Integration Tests

Integration tests require local infrastructure:

```bash
# Start infrastructure
cd infra && make start

# Python integration tests
cd python && pytest -m integration

# TypeScript integration tests
cd typescript && pnpm test:integration
```

## Code Architecture

### Telemetry Client Flow

1. **Initialization**: Load config from environment variables or code
2. **Privacy Check**: Validate opt-in status (environment, opt-out file)
3. **Backend Selection**: Initialize OTLP or ClickHouse backend
4. **Event Tracking**: Queue events in memory (batching)
5. **Flush**: Send batched events to backend (auto-flush every 5s)
6. **Retry Logic**: Exponential backoff for failed requests

### Backend Abstraction

Both SDKs support two backends:

1. **OTLP Backend** (default): Sends OTLP/JSON over HTTP to OpenTelemetry Collector
   - Endpoint: `https://telemetry.namastex.ai/v1/traces`
   - Supports traces, metrics, logs
   - Production-ready with retry logic

2. **ClickHouse Backend**: Direct insertion to ClickHouse database
   - Endpoint: `http://localhost:8123` (default)
   - Optimized for self-hosted deployments
   - Batched INSERT queries with compression

### Configuration Hierarchy

Configuration is loaded in this order (later overrides earlier):

1. Default values in `TelemetryConfig`
2. Environment variables (e.g., `AUTOMAGIK_TELEMETRY_ENDPOINT`)
3. Code configuration (constructor parameters)

### Privacy System

- **Auto-disable**: Disabled in `ENVIRONMENT=development` or `ENVIRONMENT=test`
- **Opt-out file**: `~/.automagik-no-telemetry` file disables telemetry
- **PII Detection**: Automatic detection and redaction of sensitive data
- **No tracking of**: passwords, tokens, API keys, emails, phone numbers

## SDK Differences (Python vs TypeScript)

### Naming Conventions

- **Python**: `snake_case` (e.g., `track_event`, `project_name`, `flush_interval`)
- **TypeScript**: `camelCase` (e.g., `trackEvent`, `projectName`, `flushInterval`)

### Default Batch Sizes

- **Python**: `batch_size=1` (immediate send, low latency)
- **TypeScript**: `batchSize=100` (batched send, optimized for performance)

### Time Units

- **Python**: `flush_interval` in **seconds** (float)
- **TypeScript**: `flushInterval` in **milliseconds** (number)

### Async Patterns

- **Python**: Provides both sync and async methods
  - `track_event()` (sync)
  - `track_event_async()` (async, uses asyncio.to_thread)
- **TypeScript**: All methods return void but are internally async (fire-and-forget)

## Common Development Tasks

### Adding New Features

1. Implement feature in Python SDK (`python/src/`)
2. Write tests to maintain 100% coverage (`python/tests/`)
3. Implement identical feature in TypeScript SDK (`typescript/src/`)
4. Write tests to maintain 100% coverage (`typescript/tests/`)
5. Update documentation (`docs/`)
6. Update main README.md if user-facing

### Modifying OTLP Schema

When changing OTLP payload structure:

1. Update `python/src/automagik_telemetry/schema.py`
2. Update `typescript/src/schema.ts`
3. Update integration tests to verify new schema
4. Test against local collector: `cd infra && make start && make test`

### Adding Backend Support

To add a new backend (e.g., PostgreSQL, MongoDB):

1. Create `python/src/automagik_telemetry/backends/<backend>.py`
2. Create `typescript/src/backends/<backend>.ts`
3. Implement backend interface (send traces, metrics, logs)
4. Add backend selection in client initialization
5. Add integration tests
6. Update documentation

### Releasing New Versions

1. Update version in `python/pyproject.toml`
2. Update version in `typescript/package.json`
3. Update CHANGELOG.md
4. Commit changes and tag: `git tag v0.1.x`
5. Push tag: `git push origin v0.1.x`
6. GitHub Actions will automatically publish to PyPI and npm

## CI/CD Workflows

### Python CI (`.github/workflows/python-ci.yml`)

- Tests Python 3.12 and 3.13
- Runs ruff linting and mypy type checking
- Enforces 100% test coverage
- Uploads coverage reports

### TypeScript CI (`.github/workflows/typescript-ci.yml`)

- Tests Node.js 18, 20, and 22
- Runs eslint and prettier checks
- Enforces 100% test coverage
- Uploads coverage reports

### Release Workflow (`.github/workflows/release.yml`)

- Triggered by version tags (`v*`)
- Publishes Python SDK to PyPI
- Publishes TypeScript SDK to npm

## Important Implementation Notes

### Environment Detection

Both SDKs auto-disable telemetry in development:

```python
# Python
os.getenv("ENVIRONMENT") in ["development", "test"]

# TypeScript
process.env.ENVIRONMENT === "development" || process.env.ENVIRONMENT === "test"
```

### Compression

Both SDKs support gzip compression (enabled by default):

- **Threshold**: 1024 bytes (configurable)
- **Python**: Uses `gzip` module
- **TypeScript**: Uses `zlib` module

### Retry Logic

Exponential backoff for failed requests:

- **Max retries**: 3 (configurable)
- **Backoff**: 1s base, exponential increase (2^attempt * base)
- **Python**: Uses `time.sleep()`
- **TypeScript**: Uses `setTimeout()` with Promise

### Thread Safety

- **Python**: Uses `threading.Lock` for queue access
- **TypeScript**: Single-threaded, no locking needed

## Performance Benchmarks

Expected performance (measured in tests):

- **Event tracking**: < 1ms overhead per event
- **Batch send**: < 100ms for 100 events
- **Memory usage**: < 10MB for 10,000 queued events
- **Compression**: ~70% size reduction for typical payloads

## Documentation

Key documentation files:

- `docs/INDEX.md` - Documentation hub
- `docs/GETTING_STARTED.md` - Quick start guide
- `docs/USER_GUIDES/CONFIGURATION.md` - Configuration reference
- `docs/USER_GUIDES/BACKENDS.md` - Backend comparison
- `docs/DEVELOPER_GUIDES/ARCHITECTURE.md` - Architecture deep dive
- `docs/REFERENCES/API_REFERENCE.md` - Complete API docs

## Troubleshooting

### Tests Failing with Coverage Issues

If tests pass but coverage fails:

1. Check if new code has corresponding tests
2. Run coverage report: `pytest --cov-report=html` (Python) or `pnpm test -- --coverage` (TypeScript)
3. Open HTML report to see uncovered lines
4. Add tests for uncovered code paths

### Integration Tests Failing

If integration tests fail:

1. Ensure infrastructure is running: `cd infra && make health`
2. Check service logs: `cd infra && make logs`
3. Verify endpoints are accessible (ports 4318, 8123)
4. Restart services: `cd infra && make restart`

### Type Checking Errors

- **Python**: Run `mypy src` and fix type hints
- **TypeScript**: Run `pnpm exec tsc --noEmit` and fix type errors

## Code Style

### Python

- PEP 8 compliant (enforced by ruff)
- Type hints required (mypy strict mode)
- Max line length: 100 characters
- Use `"""docstrings"""` for all public functions

### TypeScript

- ESLint + Prettier (enforced)
- Strict TypeScript mode enabled
- Use JSDoc comments for public APIs
- Prefer explicit types over inference

## Contact and Support

- **GitHub Issues**: https://github.com/namastexlabs/automagik-telemetry/issues
- **Discord**: https://discord.gg/xcW8c7fF3R
- **Documentation**: https://deepwiki.com/namastexlabs/automagik-telemetry
