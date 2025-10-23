#!/usr/bin/env python3
"""
Generate realistic test data for Automagik Telemetry dashboard validation.

This script generates:
1. Traces (events) - Feature usage, API calls, operations
2. Metrics - Gauges, counters, histograms
3. Logs - Info, warning, error messages

Usage:
    python3 infra/scripts/generate_test_data.py
"""

import asyncio
import random
import sys
import time
from pathlib import Path

# Add python SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python" / "src"))

from automagik_telemetry import (
    AutomagikTelemetry,
    ClientTelemetryConfig,  # Use ClientTelemetryConfig (has backend parameter)
    LogSeverity,
    MetricType,
    StandardEvents,
)


def print_header(text: str) -> None:
    """Print formatted header."""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")


def generate_traces(client: AutomagikTelemetry, count: int = 20) -> None:
    """Generate sample trace/event data."""
    print(f"📍 Generating {count} trace events...")

    features = [
        "list_contacts",
        "send_message",
        "create_instance",
        "manage_traces",
        "view_dashboard",
        "export_data",
        "configure_settings",
    ]

    api_endpoints = [
        "/api/v1/contacts",
        "/api/v1/messages",
        "/api/v1/instances",
        "/api/v1/traces",
        "/api/v1/analytics",
    ]

    for i in range(count):
        # Feature usage events
        if i % 3 == 0:
            client.track_event(
                StandardEvents.FEATURE_USED,
                {
                    "feature_name": random.choice(features),
                    "user_type": random.choice(["admin", "user", "developer"]),
                    "success": random.choice([True, True, True, False]),  # 75% success
                },
            )

        # API request events
        elif i % 3 == 1:
            client.track_event(
                StandardEvents.API_REQUEST,
                {
                    "endpoint": random.choice(api_endpoints),
                    "method": random.choice(["GET", "POST", "PUT", "DELETE"]),
                    "status_code": random.choice([200, 200, 200, 400, 404, 500]),
                    "duration_ms": random.randint(50, 2000),
                },
            )

        # Command execution events
        else:
            client.track_event(
                StandardEvents.COMMAND_EXECUTED,
                {
                    "command": random.choice(
                        ["list", "create", "delete", "update", "sync"]
                    ),
                    "args_count": random.randint(0, 5),
                    "exit_code": random.choice([0, 0, 0, 1]),  # 75% success
                },
            )

        # Add small delay to spread events over time
        time.sleep(0.1)

    print(f"✅ Generated {count} traces")


def generate_metrics(client: AutomagikTelemetry, count: int = 30) -> None:
    """Generate sample metric data."""
    print(f"\n📊 Generating {count} metrics...")

    for i in range(count):
        # Gauges - current values
        if i % 3 == 0:
            client.track_metric(
                "system.memory.usage",
                random.uniform(40.0, 90.0),  # 40-90% memory usage
                MetricType.GAUGE,
                {"unit": "percent", "host": f"server-{random.randint(1, 3)}"},
            )

            client.track_metric(
                "system.cpu.usage",
                random.uniform(20.0, 80.0),  # 20-80% CPU usage
                MetricType.GAUGE,
                {"unit": "percent", "host": f"server-{random.randint(1, 3)}"},
            )

        # Counters - incrementing values
        elif i % 3 == 1:
            client.track_metric(
                "api.requests.total",
                random.randint(1, 100),
                MetricType.COUNTER,
                {"endpoint": random.choice(["/api/v1/messages", "/api/v1/contacts"])},
            )

            client.track_metric(
                "errors.total",
                random.randint(0, 5),
                MetricType.COUNTER,
                {"severity": random.choice(["warning", "error", "critical"])},
            )

        # Histograms - distributions (latency, response times)
        else:
            # Simulate realistic latency distribution (mostly fast, some slow)
            latency = random.choices(
                [
                    random.uniform(10, 100),  # Fast responses
                    random.uniform(100, 500),  # Medium responses
                    random.uniform(500, 2000),  # Slow responses
                ],
                weights=[70, 25, 5],  # 70% fast, 25% medium, 5% slow
            )[0]

            client.track_metric(
                StandardEvents.OPERATION_LATENCY,
                latency,
                MetricType.HISTOGRAM,
                {
                    "operation": random.choice(
                        ["db_query", "api_call", "cache_lookup", "file_read"]
                    ),
                    "unit": "ms",
                },
            )

        time.sleep(0.1)

    print(f"✅ Generated {count} metrics")


def generate_logs(client: AutomagikTelemetry, count: int = 25) -> None:
    """Generate sample log data."""
    print(f"\n📝 Generating {count} logs...")

    log_messages = {
        LogSeverity.INFO: [
            "User successfully authenticated",
            "Configuration loaded from environment",
            "Database connection established",
            "Service started successfully",
            "Cache warmed up with 1000 entries",
        ],
        LogSeverity.WARN: [
            "High memory usage detected (85%)",
            "Slow database query detected (>500ms)",
            "Rate limit approaching threshold",
            "Deprecated API endpoint called",
        ],
        LogSeverity.ERROR: [
            "Failed to connect to external service",
            "Database query timeout",
            "Invalid user input received",
            "File not found: config.json",
        ],
        LogSeverity.FATAL: [
            "Out of memory - service crashing",
            "Critical database connection lost",
        ],
    }

    severity_weights = [60, 25, 12, 3]  # INFO, WARN, ERROR, FATAL distribution

    for i in range(count):
        severity = random.choices(
            [LogSeverity.INFO, LogSeverity.WARN, LogSeverity.ERROR, LogSeverity.FATAL],
            weights=severity_weights,
        )[0]

        message = random.choice(log_messages[severity])

        attributes = {
            "source": random.choice(["api", "worker", "scheduler", "webhook"]),
            "request_id": f"req-{random.randint(10000, 99999)}",
        }

        # Add error-specific attributes
        if severity in [LogSeverity.ERROR, LogSeverity.FATAL]:
            attributes["error_code"] = random.choice(
                ["ERR_TIMEOUT", "ERR_NOT_FOUND", "ERR_PERMISSION", "ERR_INTERNAL"]
            )

        client.track_log(message, severity, attributes)

        time.sleep(0.1)

    print(f"✅ Generated {count} logs")


def generate_errors(client: AutomagikTelemetry, count: int = 5) -> None:
    """Generate sample error events."""
    print(f"\n⚠️  Generating {count} error events...")

    error_types = [
        ValueError("Invalid phone number format"),
        ConnectionError("Failed to connect to WhatsApp"),
        TimeoutError("Request timeout after 30 seconds"),
        KeyError("Missing required field: 'message'"),
        RuntimeError("Unexpected state in message queue"),
    ]

    for i in range(count):
        error = random.choice(error_types)
        context = {
            "user_id": f"user-{random.randint(1, 100)}",
            "session_id": f"session-{random.randint(1000, 9999)}",
            "endpoint": random.choice(["/api/v1/messages", "/api/v1/contacts"]),
        }

        client.track_error(error, context)
        time.sleep(0.2)

    print(f"✅ Generated {count} errors")


def main() -> None:
    """Main function to generate all test data."""
    print_header("Automagik Telemetry - Dashboard Test Data Generator")

    # Get backend from environment variable (defaults to clickhouse for local dev)
    import os

    backend = os.getenv("AUTOMAGIK_TELEMETRY_BACKEND", "clickhouse")

    print(f"🚀 Project: api-gateway")
    print(f"🔧 Backend: {backend}")
    print(f"🎯 Generating comprehensive test data for dashboard validation\n")

    # Initialize telemetry client with ClickHouse backend for local dev
    # Use credentials from docker-compose.yml by default
    config = ClientTelemetryConfig(
        project_name="api-gateway",
        version="1.0.0",
        backend=backend,
        clickhouse_endpoint=os.getenv(
            "AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT", "http://localhost:8123"
        ),
        clickhouse_database=os.getenv(
            "AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE", "telemetry"
        ),
        clickhouse_username=os.getenv(
            "AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME", "telemetry"
        ),
        clickhouse_password=os.getenv(
            "AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD", "telemetry_password"
        ),
        batch_size=10,  # Batch for efficiency
        compression_enabled=True,
    )

    client = AutomagikTelemetry(config=config)

    # Enable telemetry (in case it's disabled by default)
    client.enable()

    print(f"📡 Telemetry Status: {'Enabled' if client.is_enabled() else 'Disabled'}")
    print(f"📊 Backend Type: {client.backend_type}\n")

    try:
        # Generate different types of telemetry data
        generate_traces(client, count=20)
        generate_metrics(client, count=30)
        generate_logs(client, count=25)
        generate_errors(client, count=5)

        # Flush any remaining batched data
        print("\n🔄 Flushing remaining data...")
        client.flush()

        print_header("✅ Test Data Generation Complete!")
        print("You can now check your Grafana dashboard at http://localhost:3000")
        print("Default credentials: admin/admin\n")
        print("📈 Summary:")
        print("  - 20 trace events (feature usage, API calls, commands)")
        print("  - 30 metrics (gauges, counters, histograms)")
        print("  - 25 log messages (info, warn, error, fatal)")
        print("  - 5 error events")
        print(f"\n  Total: ~80 telemetry data points generated")

    except Exception as e:
        print(f"\n❌ Error generating test data: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
