# OpenTelemetry Development & Testing Guide

Complete guide for developers to implement, test, and debug OpenTelemetry telemetry in automagik-agents.

> **⚠️ IMPORTANT NOTE**: This guide shows how to implement a **custom TelemetryClient** for automagik-agents.
> If you're looking to use the **automagik-telemetry SDK** in your application, see the [main README](../README.md) instead.
>
> **Recommended**: Use the automagik-telemetry SDK (`pip install automagik-telemetry`) instead of implementing your own client.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Local Development Setup](#local-development-setup)
4. [Testing Telemetry](#testing-telemetry)
5. [Adding Metrics Support](#adding-metrics-support)
6. [Production Configuration](#production-configuration)
7. [Debugging & Troubleshooting](#debugging--troubleshooting)

---

## Quick Start

### Test Current Telemetry (Traces Only)

```bash
# Send test trace to production
bash /home/cezar/test_telemetry_health.sh

# View live collector logs
ssh root@dl380-g10
pct exec 155 -- journalctl -u otelcol-contrib -f
```

### Current Endpoints

- **Production HTTPS**: `https://telemetry.namastex.ai`
- **Direct HTTP**: `http://192.168.112.155:4318`
- **Health Check**: `http://192.168.112.155:13133/health`

---

## Architecture Overview

```
┌─────────────────────┐
│ automagik-agents    │
│ (Python App)        │
│                     │
│ ┌─────────────────┐ │
│ │ TelemetryClient │ │  Sends OTLP/HTTP
│ │ (traces only)   │ ├──────────────────┐
│ └─────────────────┘ │                  │
└─────────────────────┘                  │
                                         │
                                         ▼
                    ┌────────────────────────────────┐
                    │ OpenTelemetry Collector        │
                    │ (Container 155)                │
                    │                                │
                    │ OTLP Receivers:                │
                    │  - HTTP: :4318                 │
                    │  - gRPC: :4317                 │
                    │                                │
                    │ Processors:                    │
                    │  - Batch                       │
                    │  - Resource (adds metadata)    │
                    │                                │
                    │ Exporters:                     │
                    │  - Debug (logs)                │
                    │  - Prometheus Remote Write     │
                    └────────────────────────────────┘
                              │           │
                              │           │
                   ┌──────────┘           └──────────┐
                   ▼                                  ▼
        ┌──────────────────┐              ┌──────────────────┐
        │ Journald Logs    │              │ Prometheus       │
        │ (systemd)        │              │ (192.168.112.122)│
        └──────────────────┘              └──────────────────┘
                                                    │
                                                    ▼
                                          ┌──────────────────┐
                                          │ Grafana          │
                                          │ (192.168.112.122)│
                                          └──────────────────┘
```

---

## Local Development Setup

### Option 1: Test Against Production Collector

The easiest way to develop is to use the existing production collector:

```python
# In your development environment
export OTEL_EXPORTER_OTLP_ENDPOINT="https://telemetry.namastex.ai"
export OTEL_EXPORTER_OTLP_INSECURE=false

# Or in code:
telemetry_client = TelemetryClient()
telemetry_client.endpoint = "https://telemetry.namastex.ai/v1/traces"
```

### Option 2: Local OpenTelemetry Collector

Run a local collector for development:

```bash
# Create local config
cat > /tmp/otel-local-config.yaml << 'EOF'
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
      grpc:
        endpoint: 0.0.0.0:4317

processors:
  batch:

exporters:
  debug:
    verbosity: detailed

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug]
    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [debug]
EOF

# Run with Docker
docker run -p 4318:4318 -p 4317:4317 \
  -v /tmp/otel-local-config.yaml:/etc/otelcol-contrib/config.yaml \
  otel/opentelemetry-collector-contrib:0.128.0
```

Then configure your app to use `http://localhost:4318`:

```python
telemetry_client.endpoint = "http://localhost:4318/v1/traces"
```

---

## Testing Telemetry

### 1. Test Trace Sending

**Current Implementation** (in `automagik-omni/src/core/telemetry.py`):

```python
from src.core.telemetry import TelemetryClient

# Initialize client
client = TelemetryClient()

# Send API request trace
client.track_api_request(
    endpoint="/api/v1/runs",
    method="POST"
)

# Send feature usage
client.track_feature(
    feature_name="runs",
    category="api_endpoint"
)
```

### 2. Manual Test with cURL

**Test Traces:**

```bash
curl -X POST https://telemetry.namastex.ai/v1/traces \
  -H "Content-Type: application/json" \
  -d '{
    "resourceSpans": [{
      "resource": {
        "attributes": [{
          "key": "service.name",
          "value": {"stringValue": "test-service"}
        }]
      },
      "scopeSpans": [{
        "scope": {
          "name": "test-tracer",
          "version": "1.0.0"
        },
        "spans": [{
          "traceId": "5b8aa5a2d2c872e8321cf37308d69df2",
          "spanId": "051581bf3cb55c13",
          "name": "test-span",
          "kind": "SPAN_KIND_SERVER",
          "startTimeUnixNano": "1609459200000000000",
          "endTimeUnixNano": "1609459200100000000",
          "status": {"code": "STATUS_CODE_OK"}
        }]
      }]
    }]
  }'
```

**Test Metrics (once implemented):**

```bash
curl -X POST https://telemetry.namastex.ai/v1/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "resourceMetrics": [{
      "resource": {
        "attributes": [{
          "key": "service.name",
          "value": {"stringValue": "test-service"}
        }]
      },
      "scopeMetrics": [{
        "scope": {
          "name": "test-meter",
          "version": "1.0.0"
        },
        "metrics": [{
          "name": "api_requests_total",
          "description": "Total API requests",
          "unit": "1",
          "sum": {
            "dataPoints": [{
              "attributes": [],
              "startTimeUnixNano": "1609459200000000000",
              "timeUnixNano": "1609459200000000000",
              "asInt": "42"
            }],
            "aggregationTemporality": "AGGREGATION_TEMPORALITY_CUMULATIVE",
            "isMonotonic": true
          }
        }]
      }]
    }]
  }'
```

### 3. Python Test Script

Create `test_telemetry_local.py`:

```python
#!/usr/bin/env python3
"""
Local telemetry testing script.
Tests both traces and metrics (once metrics are implemented).
"""

import json
import time
import uuid
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


class TelemetryTester:
    def __init__(self, endpoint="https://telemetry.namastex.ai"):
        self.endpoint = endpoint

    def test_trace(self):
        """Test sending a trace."""
        trace_id = uuid.uuid4().hex[:32]
        span_id = uuid.uuid4().hex[:16]

        payload = {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "test-dev"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "scopeSpans": [{
                    "scope": {
                        "name": "test-tracer",
                        "version": "1.0.0"
                    },
                    "spans": [{
                        "traceId": trace_id,
                        "spanId": span_id,
                        "name": "test.operation",
                        "kind": "SPAN_KIND_INTERNAL",
                        "startTimeUnixNano": str(int(time.time() * 1e9)),
                        "endTimeUnixNano": str(int(time.time() * 1e9) + 100000000),
                        "attributes": [
                            {"key": "test.type", "value": {"stringValue": "development"}},
                            {"key": "test.timestamp", "value": {"stringValue": time.strftime("%Y-%m-%d %H:%M:%S")}}
                        ],
                        "status": {"code": "STATUS_CODE_OK"}
                    }]
                }]
            }]
        }

        return self._send_otlp("/v1/traces", payload)

    def test_metric(self):
        """Test sending a metric."""
        payload = {
            "resourceMetrics": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "test-dev"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "scopeMetrics": [{
                    "scope": {
                        "name": "test-meter",
                        "version": "1.0.0"
                    },
                    "metrics": [{
                        "name": "test_counter",
                        "description": "Test counter metric",
                        "unit": "1",
                        "sum": {
                            "dataPoints": [{
                                "attributes": [
                                    {"key": "environment", "value": {"stringValue": "development"}}
                                ],
                                "startTimeUnixNano": str(int(time.time() * 1e9)),
                                "timeUnixNano": str(int(time.time() * 1e9)),
                                "asInt": "1"
                            }],
                            "aggregationTemporality": "AGGREGATION_TEMPORALITY_CUMULATIVE",
                            "isMonotonic": true
                        }
                    }]
                }]
            }]
        }

        return self._send_otlp("/v1/metrics", payload)

    def _send_otlp(self, path, payload):
        """Send OTLP payload."""
        url = f"{self.endpoint}{path}"
        data = json.dumps(payload).encode('utf-8')

        request = Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        try:
            with urlopen(request, timeout=5) as response:
                status = response.status
                body = response.read().decode('utf-8')
                return {
                    'success': True,
                    'status': status,
                    'body': body
                }
        except HTTPError as e:
            return {
                'success': False,
                'status': e.code,
                'error': e.read().decode('utf-8')
            }
        except URLError as e:
            return {
                'success': False,
                'error': str(e.reason)
            }


if __name__ == "__main__":
    tester = TelemetryTester()

    print("🧪 Testing OpenTelemetry Endpoints")
    print("=" * 50)

    # Test traces
    print("\n1️⃣  Testing Traces...")
    result = tester.test_trace()
    if result['success']:
        print(f"   ✅ Trace sent successfully (HTTP {result['status']})")
    else:
        print(f"   ❌ Trace failed: {result.get('error', 'Unknown error')}")

    # Test metrics
    print("\n2️⃣  Testing Metrics...")
    result = tester.test_metric()
    if result['success']:
        print(f"   ✅ Metric sent successfully (HTTP {result['status']})")
    else:
        print(f"   ❌ Metric failed: {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 50)
    print("💡 Check collector logs:")
    print("   ssh root@dl380-g10")
    print("   pct exec 155 -- journalctl -u otelcol-contrib -n 50 --no-pager")
```

Run it:

```bash
cd /home/cezar/automagik-telemetry
python test_telemetry_local.py
```

---

## Adding Metrics Support

Currently `automagik-omni/src/core/telemetry.py` only supports traces. You have two options:

### Option A: Use the automagik-telemetry SDK (Recommended)

Instead of implementing your own client, use the official SDK:

```python
from automagik_telemetry import AutomagikTelemetry, MetricType

# Initialize client
client = AutomagikTelemetry(
    project_name="automagik-omni",
    version="1.0.0"
)

# Track events
client.track_event("api.request", {
    "endpoint": "/api/v1/runs",
    "method": "POST"
})

# Track metrics with metric_type parameter
client.track_metric(
    metric_name="api.requests",
    value=1,
    metric_type=MetricType.COUNTER,
    attributes={"endpoint": "/api/v1/runs", "status": 200}
)

client.track_metric(
    metric_name="api.response_time_ms",
    value=125.3,
    metric_type=MetricType.HISTOGRAM
)

client.track_metric(
    metric_name="system.memory_mb",
    value=512.5,
    metric_type=MetricType.GAUGE
)
```

### Option B: Extend Custom TelemetryClient

If you need to customize the implementation, here's how to add metrics to your custom client:

#### Step 1: Extend TelemetryClient

Add metrics endpoint and methods:

```python
class TelemetryClient:
    def __init__(self):
        self.traces_endpoint = "https://telemetry.namastex.ai/v1/traces"
        self.metrics_endpoint = "https://telemetry.namastex.ai/v1/metrics"  # NEW
        # ... rest of init

    def track_counter(self, name: str, value: int = 1, attributes: Dict[str, Any] = None):
        """
        Track a counter metric (monotonically increasing).

        Example:
            client.track_counter("api.requests", value=1, attributes={
                "endpoint": "/api/v1/runs",
                "method": "POST",
                "status": 200
            })
        """
        if not self.enabled:
            return

        metric_payload = self._create_metric_payload(
            name=name,
            value=value,
            metric_type="counter",
            attributes=attributes or {}
        )

        self._send_async(self.metrics_endpoint, metric_payload)

    def track_gauge(self, name: str, value: float, attributes: Dict[str, Any] = None):
        """
        Track a gauge metric (can go up or down).

        Example:
            client.track_gauge("system.memory_usage_mb", value=512.5, attributes={
                "host": "automagik-01"
            })
        """
        if not self.enabled:
            return

        metric_payload = self._create_metric_payload(
            name=name,
            value=value,
            metric_type="gauge",
            attributes=attributes or {}
        )

        self._send_async(self.metrics_endpoint, metric_payload)

    def _create_metric_payload(self, name: str, value, metric_type: str, attributes: Dict[str, Any]):
        """Create OTLP metric payload."""
        timestamp_nano = str(int(time.time() * 1_000_000_000))

        # Build metric attributes
        metric_attributes = self._create_attributes(attributes)

        # Build data point based on metric type
        if metric_type == "counter":
            data_point = {
                "attributes": metric_attributes,
                "startTimeUnixNano": timestamp_nano,
                "timeUnixNano": timestamp_nano,
                "asInt": str(int(value))
            }
            metric_data = {
                "sum": {
                    "dataPoints": [data_point],
                    "aggregationTemporality": "AGGREGATION_TEMPORALITY_CUMULATIVE",
                    "isMonotonic": True
                }
            }
        elif metric_type == "gauge":
            data_point = {
                "attributes": metric_attributes,
                "timeUnixNano": timestamp_nano,
                "asDouble": float(value)
            }
            metric_data = {
                "gauge": {
                    "dataPoints": [data_point]
                }
            }
        else:
            raise ValueError(f"Unsupported metric type: {metric_type}")

        # Build full OTLP payload
        return {
            "resourceMetrics": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": self.project_name}},
                        {"key": "service.version", "value": {"stringValue": self.project_version}},
                        {"key": "service.namespace", "value": {"stringValue": self.organization}},
                        {"key": "user.id", "value": {"stringValue": self.user_id}},
                        {"key": "session.id", "value": {"stringValue": self.session_id}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": "automagik-agents"}},
                        {"key": "telemetry.sdk.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "scopeMetrics": [{
                    "scope": {
                        "name": f"{self.project_name}.telemetry",
                        "version": "1.0.0"
                    },
                    "metrics": [{
                        "name": name,
                        "description": f"Metric: {name}",
                        "unit": "1",
                        **metric_data
                    }]
                }]
            }]
        }
```

#### Step 2: Use in Your Application

**Using Custom TelemetryClient (Option B):**

```python
from src.core.telemetry import TelemetryClient

client = TelemetryClient()

# Track API requests
@app.post("/api/v1/runs")
async def create_run():
    client.track_counter("api.requests", attributes={
        "endpoint": "/api/v1/runs",
        "method": "POST"
    })
    # ... your logic

    client.track_gauge("api.response_time_ms", value=response_time)
    return result

# Track business metrics
client.track_counter("runs.created", attributes={
    "agent_type": agent_type,
    "status": "success"
})

# Track system metrics
client.track_gauge("system.active_connections", value=len(connections))
```

**Using automagik-telemetry SDK (Option A - Recommended):**

```python
from automagik_telemetry import AutomagikTelemetry, MetricType

client = AutomagikTelemetry(project_name="automagik-omni", version="1.0.0")

# Track API requests
@app.post("/api/v1/runs")
async def create_run():
    client.track_metric(
        metric_name="api.requests",
        value=1,
        metric_type=MetricType.COUNTER,
        attributes={"endpoint": "/api/v1/runs", "method": "POST"}
    )
    # ... your logic

    client.track_metric(
        metric_name="api.response_time_ms",
        value=response_time,
        metric_type=MetricType.GAUGE
    )
    return result

# Track business metrics
client.track_metric(
    metric_name="runs.created",
    value=1,
    metric_type=MetricType.COUNTER,
    attributes={"agent_type": agent_type, "status": "success"}
)

# Track system metrics
client.track_metric(
    metric_name="system.active_connections",
    value=len(connections),
    metric_type=MetricType.GAUGE
)
```

#### Step 3: Test Locally

```bash
# Run your test script
python test_telemetry_local.py

# Verify in collector logs
ssh root@dl380-g10
pct exec 155 -- journalctl -u otelcol-contrib -f | grep -i metric
```

#### Step 4: Query in Prometheus

Once metrics are flowing:

```bash
# Check if metrics arrived
curl -s "http://192.168.112.122:9090/api/v1/label/__name__/values" | jq -r '.data[] | select(. | contains("api"))'

# Query specific metric
curl -s "http://192.168.112.122:9090/api/v1/query?query=api_requests" | jq '.data.result'

# Check metric with labels
curl -s 'http://192.168.112.122:9090/api/v1/query?query=api_requests{endpoint="/api/v1/runs"}' | jq
```

---

## Production Configuration

### Current Production Setup

**OpenTelemetry Collector** (Container 155 - `192.168.112.155`)
- OTLP HTTP: `:4318`
- OTLP gRPC: `:4317`
- Health Check: `:13133/health`
- Public URL: `https://telemetry.namastex.ai`

**Prometheus** (Container 122 - `192.168.112.122`)
- API: `http://192.168.112.122:9090`
- Remote Write: `http://192.168.112.122:9090/api/v1/write`

**Grafana** (Container 122 - `192.168.112.122`)
- UI: `http://192.168.112.122:3000`
- Default credentials: `admin/admin`

### Environment Variables

For `automagik-agents`:

```bash
# Enable/disable telemetry
export AUTOMAGIK_TELEMETRY_ENABLED=true

# Custom endpoint (if needed)
export OTEL_EXPORTER_OTLP_ENDPOINT="https://telemetry.namastex.ai"

# Development mode (disables telemetry)
export ENVIRONMENT=development
```

### Collector Configuration

Current config on container 155 (`/etc/otelcol-contrib/config.yaml`):

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s
    send_batch_size: 1024
  resource:
    attributes:
      - key: service.namespace
        value: "namastex"
        action: upsert
      - key: deployment.environment
        value: "production"
        action: upsert

exporters:
  prometheusremotewrite:
    endpoint: "http://192.168.112.122:9090/api/v1/write"
    tls:
      insecure: true
  debug:
    verbosity: detailed

extensions:
  health_check:
    endpoint: 0.0.0.0:13133
    path: /health

service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [debug]
    metrics:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [prometheusremotewrite, debug]
    logs:
      receivers: [otlp]
      processors: [batch, resource]
      exporters: [debug]
```

---

## Debugging & Troubleshooting

### Check Collector Status

```bash
# SSH to Proxmox host
ssh root@dl380-g10

# Check service status
pct exec 155 -- systemctl status otelcol-contrib

# View live logs
pct exec 155 -- journalctl -u otelcol-contrib -f

# View recent logs (last 100 lines)
pct exec 155 -- journalctl -u otelcol-contrib -n 100 --no-pager

# Search for errors
pct exec 155 -- journalctl -u otelcol-contrib -n 200 --no-pager | grep -i error

# Filter by signal type
pct exec 155 -- journalctl -u otelcol-contrib -f | grep "traces\|metrics\|logs"
```

### Test Collector Health

```bash
# Health check endpoint
curl http://192.168.112.155:13133/health

# Or via public URL
curl https://telemetry.namastex.ai/health
```

### Test Endpoints Manually

```bash
# Test traces endpoint
curl -X POST https://telemetry.namastex.ai/v1/traces \
  -H "Content-Type: application/json" \
  -d '{"resourceSpans":[]}'

# Test metrics endpoint
curl -X POST https://telemetry.namastex.ai/v1/metrics \
  -H "Content-Type: application/json" \
  -d '{"resourceMetrics":[]}'
```

Expected responses:
- `200 OK` - Data accepted
- `405 Method Not Allowed` - GET on POST-only endpoint (normal)
- `400 Bad Request` - Invalid payload format

### Check Prometheus

```bash
# List all metrics
curl -s "http://192.168.112.122:9090/api/v1/label/__name__/values" | jq -r '.data[]'

# Query specific metric
curl -s "http://192.168.112.122:9090/api/v1/query?query=api_requests_total" | jq

# Check scrape targets
curl -s "http://192.168.112.122:9090/api/v1/targets" | jq '.data.activeTargets'

# Test remote write endpoint
curl -X POST "http://192.168.112.122:9090/api/v1/write" \
  -H "Content-Type: application/x-protobuf"
```

### Common Issues

#### 1. **No metrics appearing in Prometheus**

**Cause**: Application not sending metrics (only traces)

**Solution**: Implement metrics in `TelemetryClient` (see "Adding Metrics Support" section)

**Verify**:
```bash
# Check if collector is receiving metrics
pct exec 155 -- journalctl -u otelcol-contrib -n 50 --no-pager | grep -i metric
```

#### 2. **Connection refused**

**Cause**: Collector not running or wrong endpoint

**Solution**:
```bash
# Restart collector
pct exec 155 -- systemctl restart otelcol-contrib

# Check ports
pct exec 155 -- ss -tulpn | grep -E "4317|4318"
```

#### 3. **SSL/TLS errors**

**Cause**: Using HTTPS with self-signed cert or wrong config

**Solution**: Use HTTP for local dev, HTTPS for production through Cloudflare tunnel

```python
# Development
endpoint = "http://192.168.112.155:4318"

# Production
endpoint = "https://telemetry.namastex.ai"
```

#### 4. **High latency / timeout**

**Cause**: Synchronous sending blocking application

**Solution**: Use async sending (already implemented in `_send_async`)

```python
# Good (non-blocking)
client._send_async(endpoint, payload)

# Bad (blocks)
client._send_sync(endpoint, payload)
```

### Debug Mode

Enable verbose logging in your application:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("telemetry")

# In TelemetryClient
logger.debug(f"Sending trace to {self.endpoint}")
logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
```

---

## Performance Considerations

### Batching

The collector batches data automatically (configured to send every 10s or 1024 items):

```yaml
processors:
  batch:
    timeout: 10s
    send_batch_size: 1024
```

### Async Sending

Always use async to avoid blocking:

```python
# Current implementation uses threading
def _send_async(self, endpoint: str, payload: Dict[str, Any]):
    """Send payload in background thread."""
    thread = threading.Thread(target=self._send_sync, args=(endpoint, payload))
    thread.daemon = True
    thread.start()
```

### Sampling (Future Enhancement)

For high-volume applications, consider adding sampling:

**Using automagik-telemetry SDK:**

```python
import random
from automagik_telemetry import AutomagikTelemetry, MetricType

client = AutomagikTelemetry(project_name="my-app", version="1.0.0")

def should_sample(sample_rate=0.1):
    """Sample 10% of requests."""
    return random.random() < sample_rate

if should_sample():
    client.track_metric(
        metric_name="api.requests",
        value=1,
        metric_type=MetricType.COUNTER
    )
```

**Using custom TelemetryClient:**

```python
import random

def should_sample(sample_rate=0.1):
    """Sample 10% of requests."""
    return random.random() < sample_rate

if should_sample():
    client.track_counter("api.requests")
```

---

## Useful Scripts Reference

All scripts are in `/home/cezar/`:

- `test_telemetry_health.sh` - Send test traces/metrics
- `view_telemetry_logs.sh` - View collector logs
- `secure_telemetry.sh` - Add basic auth (not currently enabled)
- `add_telemetry_hostname.sh` - Cloudflare tunnel configuration

---

## Next Steps

1. **Implement metrics** in `automagik-omni/src/core/telemetry.py`
2. **Add instrumentation** to your API endpoints and services
3. **Create Grafana dashboards** to visualize the data
4. **Set up alerts** in Prometheus for critical metrics
5. **Document business metrics** your team cares about

---

## Support

For issues or questions:
- Check collector logs first: `pct exec 155 -- journalctl -u otelcol-contrib -f`
- Verify endpoints are reachable: `curl https://telemetry.namastex.ai/health`
- Test with the provided Python script: `python test_telemetry_local.py`

Happy instrumenting! 🎉
