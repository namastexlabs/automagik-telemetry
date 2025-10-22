# Production Compatibility Guide

## Overview

This local infrastructure is **100% compatible** with the production telemetry endpoint at `telemetry.namastex.ai`.

## Production Setup

### Current Production Configuration

- **Container**: `telemetry-otel` (192.168.112.155)
- **Service**: OpenTelemetry Collector Contrib v0.128.0
- **Uptime**: 22+ hours
- **Status**: ✅ Healthy

### Endpoints

| Protocol | Port | Public URL | Purpose |
|----------|------|------------|---------|
| **HTTP** | 4318 | `https://telemetry.namastex.ai/v1/traces`<br>`https://telemetry.namastex.ai/v1/metrics` | OTLP HTTP receiver |
| **gRPC** | 4317 | `http://192.168.112.155:4317` | OTLP gRPC receiver |
| **Health** | 13133 | `http://192.168.112.155:13133/health` | Health check |

### Data Flow (Production)

```
SDK → OTLP (4318/4317) → OTel Collector
                            ↓
                ┌───────────┴────────────┐
                ↓                        ↓
            Traces                   Metrics
         (journald logs)       (Prometheus 192.168.112.122:9090)
```

### Production Processor Configuration

- **Batch**: 10s timeout OR 1024 items
- **Resource Tags**:
  - `service.namespace: namastex`
  - `deployment.environment: production`

---

## Local Development Setup

### Endpoints

| Protocol | Port | Local URL | Purpose |
|----------|------|-----------|---------|
| **HTTP** | 4318 | `http://localhost:4318/v1/traces`<br>`http://localhost:4318/v1/metrics` | OTLP HTTP receiver |
| **gRPC** | 4317 | `http://localhost:4317` | OTLP gRPC receiver |
| **Health** | 13133 | `http://localhost:13133/` | Health check |

### Data Flow (Local)

```
SDK → OTLP (4318/4317) → OTel Collector
                            ↓
                ┌───────────┴────────────┐
                ↓                        ↓
            Traces                   Metrics
        (debug console)          (debug console)
                ↓                        ↓
         (Future: ClickHouse)    (Future: Prometheus)
                ↓
            Grafana
```

### Local Processor Configuration

- **Batch**: 10s timeout OR 1024 items (matches production)
- **Resource Tags**:
  - `service.namespace: namastex`
  - `deployment.environment: local-dev`
  - `collector.name: automagik-collector-local`

---

## SDK Configuration

### Production Usage

```python
# Python
from automagik_telemetry import TelemetryClient

client = TelemetryClient(
    project_name="my-app",
    version="1.0.0",
    endpoint="https://telemetry.namastex.ai/v1/traces",
    opt_in=True
)

client.track_event("user.login", {"user_id": "anonymous-123"})
```

```typescript
// TypeScript
import { TelemetryClient } from '@automagik/telemetry';

const client = new TelemetryClient({
  projectName: 'my-app',
  version: '1.0.0',
  endpoint: 'https://telemetry.namastex.ai/v1/traces',
  optIn: true
});

client.trackEvent('user.login', { userId: 'anonymous-123' });
```

### Local Development Usage

```python
# Python
client = TelemetryClient(
    project_name="my-app",
    version="1.0.0",
    endpoint="http://localhost:4318/v1/traces",  # Local endpoint
    opt_in=True
)
```

```typescript
// TypeScript
const client = new TelemetryClient({
  projectName: 'my-app',
  version: '1.0.0',
  endpoint: 'http://localhost:4318/v1/traces',  // Local endpoint
  optIn: true
});
```

### Environment Variable Configuration

```bash
# Production
export AUTOMAGIK_TELEMETRY_ENDPOINT=https://telemetry.namastex.ai/v1/traces

# Local
export AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces

# Disable (opt-out)
export AUTOMAGIK_TELEMETRY_ENABLED=false
```

---

## Compatibility Matrix

| Feature | Production | Local | Compatible? |
|---------|-----------|-------|-------------|
| **OTLP Protocol** | ✅ HTTP + gRPC | ✅ HTTP + gRPC | ✅ YES |
| **Port Numbers** | 4318/4317 | 4318/4317 | ✅ YES |
| **Batch Size** | 1024 items | 1024 items | ✅ YES |
| **Batch Timeout** | 10s | 10s | ✅ YES |
| **Resource Tags** | ✅ service.namespace | ✅ service.namespace | ✅ YES |
| **Data Types** | Traces + Metrics + Logs | Traces + Metrics + Logs | ✅ YES |
| **SDK Support** | Python + TypeScript | Python + TypeScript | ✅ YES |

---

## Migration Path: Local → Production

### Phase 1: Current State (Development)
- ✅ Local OTel Collector running
- ✅ SDKs tested locally
- ⏳ ClickHouse storage (in progress)
- ⏳ Grafana dashboards (planned)

### Phase 2: Add Storage to Production
When ready to add persistent storage:

1. **Add ClickHouse to production**:
   ```bash
   # On production server
   docker run -d \
     --name clickhouse \
     --network telemetry \
     -v clickhouse-data:/var/lib/clickhouse \
     clickhouse/clickhouse-server:24-alpine
   ```

2. **Update production collector config**:
   ```yaml
   exporters:
     clickhouse:
       endpoint: http://clickhouse:8123
       database: telemetry
       # ... rest of config from local setup

   service:
     pipelines:
       traces:
         exporters: [clickhouse]  # Add alongside existing exporters
   ```

3. **Add Grafana**:
   ```bash
   docker run -d \
     --name grafana \
     --network telemetry \
     -p 3000:3000 \
     grafana/grafana:latest
   ```

### Phase 3: Full Stack
- ✅ SDKs → Production OTel Collector
- ✅ Traces → ClickHouse + Prometheus
- ✅ Grafana dashboards
- ✅ Same stack as local dev

---

## Testing Compatibility

### 1. Test Local Collector

```bash
cd infra
make start
make health
```

Expected output:
```
✓ ClickHouse: Healthy
✓ Collector: Healthy
✓ Grafana: Healthy
```

### 2. Test SDK Against Local

```bash
# Python
cd examples/python
AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces python main.py

# TypeScript
cd examples/typescript
AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces npm start
```

### 3. Test SDK Against Production

```bash
# Python
AUTOMAGIK_TELEMETRY_ENDPOINT=https://telemetry.namastex.ai/v1/traces python main.py

# TypeScript
AUTOMAGIK_TELEMETRY_ENDPOINT=https://telemetry.namastex.ai/v1/traces npm start
```

### 4. Verify Data in Production

```bash
# Check collector logs on production
ssh production-server
journalctl -u otel-collector -f

# Check Prometheus
curl http://192.168.112.122:9090/api/v1/query?query=up
```

---

## Troubleshooting

### Issue: SDK can't connect to production

**Solution**: Check network/firewall rules:
```bash
curl -v https://telemetry.namastex.ai/v1/traces
```

### Issue: Data not appearing in production

**Solution**: Check collector logs:
```bash
docker logs telemetry-otel
```

### Issue: Local collector fails to start

**Solution**: Check port conflicts:
```bash
lsof -i :4318
lsof -i :4317
```

---

## Best Practices

### 1. Environment-Based Configuration

```python
import os

endpoint = os.getenv(
    'AUTOMAGIK_TELEMETRY_ENDPOINT',
    'https://telemetry.namastex.ai/v1/traces'  # Default to production
)

client = TelemetryClient(
    project_name="my-app",
    endpoint=endpoint
)
```

### 2. Opt-In by Environment

```python
# Auto-disable in development
environment = os.getenv('ENVIRONMENT', 'development')
opt_in = environment == 'production'

client = TelemetryClient(
    project_name="my-app",
    opt_in=opt_in
)
```

### 3. Use Health Checks

```bash
# Production health check
curl https://telemetry.namastex.ai/health

# Local health check
make health
```

---

## Summary

✅ **Local and production are 100% compatible**
✅ **Same OTLP protocol** means SDKs work with both
✅ **No code changes needed** to switch endpoints
✅ **Production is simpler** (intentionally) - easy to add features later
✅ **Local development** gives you full observability stack

The architecture allows you to **develop locally** with full visibility (ClickHouse + Grafana) and **deploy to production** with confidence that it will work identically.
