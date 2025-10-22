# Python Integration Tests

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev,integration]"

# Run all integration tests
pytest -v -m integration

# Run specific test file
pytest -v tests/test_integration_fastapi.py
```

## Test Files

| File | Description | Requirements |
|------|-------------|--------------|
| `test_integration_fastapi.py` | FastAPI integration with HTTP servers | fastapi, httpx |
| `test_integration_throughput.py` | High-throughput and sustained load | psutil (optional) |
| `test_integration_otlp.py` | Real OTLP collector communication | Network access |
| `test_integration_memory.py` | Memory leak detection | psutil |

## Common Commands

```bash
# Skip integration tests (unit tests only)
pytest -v -m "not integration"

# Run with output visible
pytest -v -s -m integration

# Run specific test
pytest -v tests/test_integration_otlp.py::test_send_trace_to_collector

# Run with custom endpoint
AUTOMAGIK_TELEMETRY_ENDPOINT=https://custom.endpoint.com pytest -v -m integration
```

## Environment Variables

- `AUTOMAGIK_TELEMETRY_ENABLED=true` - Enable telemetry (required for tests)
- `AUTOMAGIK_TELEMETRY_ENDPOINT` - Override collector endpoint
- `AUTOMAGIK_TELEMETRY_VERBOSE=true` - Enable verbose output

## See Also

Full documentation: `/INTEGRATION_TESTS.md`
