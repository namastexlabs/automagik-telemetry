#!/usr/bin/env python3
"""
Basic Example - Automagik Telemetry Python SDK

This example demonstrates the simplest way to get started with the Python SDK.
It shows how to initialize the client, track events, metrics, and logs.

Prerequisites:
    pip install automagik-telemetry

For local infrastructure testing:
    cd infra && make start
"""

import os
import time
from automagik_telemetry import AutomagikTelemetry, TelemetryConfig, StandardEvents

# Configure for local infrastructure (uncomment to test locally)
# os.environ["AUTOMAGIK_TELEMETRY_ENABLED"] = "true"
# os.environ["AUTOMAGIK_TELEMETRY_ENDPOINT"] = "http://localhost:4318/v1/traces"
# os.environ["AUTOMAGIK_TELEMETRY_VERBOSE"] = "true"


def main():
    """Run basic telemetry examples."""

    # Initialize telemetry client
    config = TelemetryConfig(
        project_name="basic-example",
        version="1.0.0",
        # Optional: configure for local testing
        # endpoint="http://localhost:4318/v1/traces",
        # backend="otlp",  # or "clickhouse"
        # batch_size=1,  # Send immediately for testing
        # verbose=True,
    )

    telemetry = AutomagikTelemetry(config=config)

    print("🚀 Basic Telemetry Example")
    print("=" * 50)

    # Example 1: Track a simple event
    print("\n1️⃣  Tracking a simple event...")
    telemetry.track_event(
        StandardEvents.FEATURE_USED,
        {
            "feature_name": "basic_example",
            "user_action": "started",
        }
    )
    print("✅ Event tracked!")

    # Example 2: Track a metric
    print("\n2️⃣  Tracking a metric...")
    telemetry.track_metric(
        name="example.response_time",
        value=123.45,
        metric_type="gauge",
        attributes={
            "endpoint": "/api/example",
            "status": "success",
        }
    )
    print("✅ Metric tracked!")

    # Example 3: Track a log
    print("\n3️⃣  Tracking a log message...")
    telemetry.track_log(
        message="Basic example completed successfully",
        level="info",
        attributes={
            "component": "basic_example",
            "duration_ms": 100,
        }
    )
    print("✅ Log tracked!")

    # Example 4: Track custom events
    print("\n4️⃣  Tracking custom events...")
    telemetry.track_event(
        "custom.app.workflow_completed",
        {
            "workflow_name": "onboarding",
            "steps_completed": 5,
            "success": True,
        }
    )
    print("✅ Custom event tracked!")

    # Flush all pending events
    print("\n5️⃣  Flushing all pending events...")
    telemetry.flush()
    print("✅ All events flushed!")

    # Wait a moment for async operations
    time.sleep(1)

    # Check status
    print("\n📊 Telemetry Status:")
    status = telemetry.get_status()
    print(f"   Enabled: {status['enabled']}")
    print(f"   User ID: {status['user_id']}")
    print(f"   Endpoint: {status['endpoint']}")
    print(f"   Queue Sizes: {status['queue_sizes']}")

    print("\n" + "=" * 50)
    print("✨ Example completed!")
    print("\nNext steps:")
    print("- Check Grafana at http://localhost:3000 (if using local infra)")
    print("- Try the omni_example.py for real-world usage")
    print("- Read the docs at https://github.com/namastexlabs/automagik-telemetry")


if __name__ == "__main__":
    main()
