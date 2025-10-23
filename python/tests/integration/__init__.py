"""
Integration tests for Automagik Telemetry SDK.

These tests require external services (ClickHouse, OTLP collector) to be running.
They test end-to-end flows and verify data persistence in real databases.

Prerequisites:
- ClickHouse: docker compose up -d clickhouse (from infra/)
- OTLP Collector: docker compose up -d collector (from infra/)

Run all integration tests:
    pytest -v python/tests/integration/

Run specific integration test:
    pytest -v python/tests/integration/test_clickhouse_integration.py

Mark tests as integration tests using:
    @pytest.mark.integration
"""
