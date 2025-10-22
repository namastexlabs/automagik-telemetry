# OpenTelemetry Telemetry System

[![Python SDK CI](https://github.com/namastexlabs/automagik-telemetry/actions/workflows/python-ci.yml/badge.svg)](https://github.com/namastexlabs/automagik-telemetry/actions/workflows/python-ci.yml)
[![TypeScript SDK CI](https://github.com/namastexlabs/automagik-telemetry/actions/workflows/typescript-ci.yml/badge.svg)](https://github.com/namastexlabs/automagik-telemetry/actions/workflows/typescript-ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Complete OpenTelemetry setup for automagik-agents with traces and metrics collection.

## 📢 SDK Update Notice

**Class Rename:** The main client class has been renamed from `TelemetryClient` to `AutomagikTelemetry` for clarity and consistency across the Automagik ecosystem.

- **New name:** `AutomagikTelemetry` (recommended)
- **Old name:** `TelemetryClient` (still works as an alias for backwards compatibility)

No action required - both names work identically. See examples below using the new name.

## 🎯 Overview

This repository contains:
- ✅ **Production OpenTelemetry Collector** running on LXC container 155
- ✅ **Prometheus Integration** for metrics storage and querying
- ✅ **Cloudflare Tunnel** for secure HTTPS access
- ✅ **Development Tools** for local testing and debugging

## 🚀 Quick Start

### Test the System

```bash
# Run the test script
python3 test_telemetry_local.py

# Expected output: 4/4 tests passed ✅
```

### Check Results

```bash
# Query Prometheus for test metrics (wait 30s after sending)
curl -s "http://192.168.112.122:9090/api/v1/label/__name__/values" | jq -r '.data[] | select(. | test("test_"))'

# Should return:
# - test_api_requests_total
# - test_memory_usage_mb_MB
# - test_response_time_ms_milliseconds_*
```

## 📡 System Architecture

```
Application → OTLP/HTTP → OTel Collector → Prometheus → Grafana
                              ↓
                          Debug Logs
```

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **OTel Collector** | Container 155 (192.168.112.155) | Receives and processes telemetry |
| **Prometheus** | Container 122 (192.168.112.122:9090) | Stores metrics |
| **Grafana** | Container 122 (192.168.112.122:3000) | Visualizes metrics |
| **Cloudflare Tunnel** | telemetry.namastex.ai | Secure HTTPS access |

## 📚 Documentation

- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Command cheat sheet, endpoints, common patterns
- **[TELEMETRY_DEVELOPMENT_GUIDE.md](TELEMETRY_DEVELOPMENT_GUIDE.md)** - Complete development guide with:
  - Architecture deep dive
  - Local development setup
  - Adding metrics to automagik-agents
  - Testing strategies
  - Debugging guide
  - Performance considerations

## 🔧 Development Setup

### Option 1: Use Production Collector (Recommended)

```python
# Already configured in automagik-agents
endpoint = "https://telemetry.namastex.ai"
```

### Option 2: Local Collector

```bash
# Run local OTel Collector with Docker
docker run -p 4318:4318 -p 4317:4317 \
  otel/opentelemetry-collector-contrib:0.128.0
```

## 🧪 Testing Tools

### Python Test Script

```bash
# Test against production
python3 test_telemetry_local.py

# Test against local collector
python3 test_telemetry_local.py http://localhost:4318
```

### Bash Test Script

```bash
# Send sample traces and metrics
bash test_telemetry_health.sh

# Test custom endpoint
bash test_telemetry_health.sh http://localhost:4318
```

## 📊 Current Status

### ✅ Working

- Traces collection from automagik-agents
- Metrics collection (tested with test script)
- Prometheus remote write integration
- Debug logging to journald
- Health check endpoint
- Cloudflare HTTPS tunnel

### ⚠️ To Implement

- **Metrics in automagik-agents**: Currently only sends traces
  - See `TELEMETRY_DEVELOPMENT_GUIDE.md` → "Adding Metrics Support"
  - Implementation example provided in guide

## 🔐 Configuration

### Endpoints

```bash
# Production (HTTPS via Cloudflare)
TRACES:  https://telemetry.namastex.ai/v1/traces
METRICS: https://telemetry.namastex.ai/v1/metrics
HEALTH:  https://telemetry.namastex.ai/health

# Direct (HTTP)
TRACES:  http://192.168.112.155:4318/v1/traces
METRICS: http://192.168.112.155:4318/v1/metrics
HEALTH:  http://192.168.112.155:13133/health
```

### Environment Variables

```bash
# Disable telemetry
export AUTOMAGIK_OMNI_DISABLE_TELEMETRY=true

# Development mode (auto-disables)
export ENVIRONMENT=development
```

## 🐛 Debugging

### Check Collector

```bash
ssh root@dl380-g10

# Service status
pct exec 155 -- systemctl status otelcol-contrib

# Live logs
pct exec 155 -- journalctl -u otelcol-contrib -f

# Recent logs
pct exec 155 -- journalctl -u otelcol-contrib -n 100 --no-pager
```

### Check Prometheus

```bash
# List metrics
curl -s "http://192.168.112.122:9090/api/v1/label/__name__/values" | jq

# Query metric
curl -s 'http://192.168.112.122:9090/api/v1/query?query=test_api_requests_total' | jq
```

### Verify Connectivity

```bash
# Health check
curl https://telemetry.namastex.ai/health

# Test endpoint (should return 405 on GET)
curl https://telemetry.namastex.ai/v1/traces
```

## 📦 Files

### Documentation
- `README.md` - This file (overview)
- `QUICK_REFERENCE.md` - Command cheat sheet
- `TELEMETRY_DEVELOPMENT_GUIDE.md` - Complete developer guide

### Testing Scripts
- `test_telemetry_local.py` - Python test script (traces + metrics)
- `test_telemetry_health.sh` - Bash test script (OTLP payloads)

### Management Scripts
- `view_telemetry_logs.sh` - View collector logs
- `secure_telemetry.sh` - Add basic auth (not active)
- `add_telemetry_hostname.sh` - Cloudflare tunnel config

### Configuration
- `otel-prometheus-config.yaml` - Active collector config
- `otel-grafana-config.yaml` - Config template with Tempo/Loki
- `otelcol-health-config.yaml` - Minimal health check config

## 🎓 Usage Examples

### Send Trace (Current Implementation)

```python
from automagik_telemetry import AutomagikTelemetry

client = AutomagikTelemetry(project_name="my-app", version="1.0.0")
client.track_event("api.request", {"endpoint": "/api/v1/runs", "method": "POST"})
```

**Note:** `TelemetryClient` is still supported as a backwards compatibility alias.

### Send Metrics (To Implement)

```python
# Counter
client.track_counter("api.requests", value=1, attributes={
    "endpoint": "/api/v1/runs",
    "status": 200
})

# Gauge
client.track_gauge("system.memory_mb", value=512.5)

# Histogram
client.track_histogram("api.response_time_ms", value=125.3)
```

See `TELEMETRY_DEVELOPMENT_GUIDE.md` for complete implementation details.

## 🚨 Common Issues

### No Metrics in Prometheus

**Cause**: Application not sending metrics (only traces)

**Solution**: Implement metrics in `automagik-omni/src/core/telemetry.py`

See guide → "Adding Metrics Support"

### Connection Refused

**Solutions**:
1. Check collector is running: `pct exec 155 -- systemctl status otelcol-contrib`
2. Restart if needed: `pct exec 155 -- systemctl restart otelcol-contrib`
3. Verify endpoints are correct

### Data Not Appearing

**Check**:
1. Wait 15-30 seconds for batching
2. Check collector logs for errors
3. Verify Prometheus is receiving data

## 🤝 Contributing

When adding telemetry to your application:

1. **Always use async sending** (already in TelemetryClient)
2. **Add meaningful attributes** for filtering
3. **Use appropriate metric types**:
   - Counter: Things that only go up (requests, errors)
   - Gauge: Things that go up/down (memory, connections)
   - Histogram: Distributions (response times, sizes)
4. **Test locally first** with `test_telemetry_local.py`
5. **Check Prometheus** to verify data is arriving

## 📞 Support

1. Check `QUICK_REFERENCE.md` for common commands
2. Review `TELEMETRY_DEVELOPMENT_GUIDE.md` for detailed info
3. Check collector logs: `pct exec 155 -- journalctl -u otelcol-contrib -f`
4. Test connectivity: `curl https://telemetry.namastex.ai/health`

---

**Last Updated**: 2025-10-21

**Version**: OpenTelemetry Collector 0.128.0

**Status**: ✅ Production Ready (traces + metrics infrastructure)
