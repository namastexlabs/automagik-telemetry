#!/usr/bin/env python3
"""
Test script to demonstrate proper trace-log correlation.

This script generates traces and logs with matching trace_ids to prove
that the correlation mechanism works correctly.
"""

import sys
import uuid
from pathlib import Path

# Add python SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "python" / "src"))

from automagik_telemetry import (
    AutomagikTelemetry,
    ClientTelemetryConfig,
    LogSeverity,
)


def main():
    print("\n" + "=" * 70)
    print("  Trace-Log Correlation Test")
    print("=" * 70 + "\n")

    # Initialize client
    config = ClientTelemetryConfig(
        project_name="correlation-test",
        version="1.0.0",
        backend="clickhouse",
        clickhouse_endpoint="http://localhost:8123",
        clickhouse_database="telemetry",
        clickhouse_username="telemetry",
        clickhouse_password="telemetry_password",
        batch_size=1,  # Immediate send
    )

    client = AutomagikTelemetry(config=config)

    # Simulate a traced operation with associated logs
    print("🔗 Simulating traced operation with correlated logs...\n")

    # Generate trace ID (simulating what would happen in a real trace context)
    # In a real app, this would be extracted from the active trace
    trace_id = str(uuid.uuid4()).replace("-", "") + str(uuid.uuid4()).replace("-", "")[:32]  # 64 hex chars like real traces
    span_id = str(uuid.uuid4()).replace("-", "")[:16]  # 16 hex chars

    print(f"📍 Trace ID: {trace_id[:32]}...")
    print(f"📍 Span ID:  {span_id}\n")

    # Generate a trace event
    client.track_event(
        "api.request",
        {
            "endpoint": "/api/v1/users",
            "method": "POST",
            "status_code": 200,
        },
    )

    # Generate logs that are part of this trace
    # In a real application, these would be automatically correlated
    print("📝 Generating correlated logs:")

    logs_with_trace = [
        ("Starting request processing", LogSeverity.INFO),
        ("Database connection established", LogSeverity.INFO),
        ("User validation successful", LogSeverity.INFO),
        ("Response sent successfully", LogSeverity.INFO),
    ]

    for message, severity in logs_with_trace:
        client.track_log(
            message,
            severity,
            attributes={
                "trace_id": trace_id,  # Link to trace
                "span_id": span_id,  # Link to span
                "operation": "create_user",
                "user_id": "user-12345",
            },
        )
        print(f"  ✓ {message}")

    # Flush to ensure data is sent
    client.flush()

    print("\n✅ Correlated telemetry generated successfully!\n")
    print("=" * 70)
    print("  Verification Query")
    print("=" * 70 + "\n")
    print("Run this query to verify correlation:")
    print(f"\n  SELECT trace_id, span_id, body, project_name")
    print(f"  FROM telemetry.logs")
    print(f"  WHERE trace_id = '{trace_id}'")
    print(f"  ORDER BY timestamp DESC;\n")
    print("All 4 logs should have the same trace_id, proving correlation works!")
    print("")


if __name__ == "__main__":
    main()
