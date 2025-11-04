"""
Telemetry backends for different storage systems.

Available backends:
- otlp: Standard OpenTelemetry Protocol (default)
- clickhouse: Direct ClickHouse insertion via HTTP API
"""

from .base import TelemetryBackend
from .clickhouse import ClickHouseBackend
from .otlp import OTLPBackend

__all__ = ["TelemetryBackend", "ClickHouseBackend", "OTLPBackend"]
