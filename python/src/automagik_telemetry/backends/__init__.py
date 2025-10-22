"""
Telemetry backends for different storage systems.

Available backends:
- otlp: Standard OpenTelemetry Protocol (default)
- clickhouse: Direct ClickHouse insertion via HTTP API
"""

from .clickhouse import ClickHouseBackend

__all__ = ["ClickHouseBackend"]
