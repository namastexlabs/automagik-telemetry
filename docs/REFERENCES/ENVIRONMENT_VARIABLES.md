# Environment Variables Quick Reference

> **⚡ Fast lookup guide** for all Automagik Telemetry environment variables. Copy-paste ready examples with platform-specific notes.

---

## 📋 Complete Variables Table

### Telemetry Control

| Variable | Type | Default | Description | Example |
|----------|------|---------|-------------|---------|
| `AUTOMAGIK_TELEMETRY_ENABLED` | boolean | `false` | Enable/disable telemetry globally | `export AUTOMAGIK_TELEMETRY_ENABLED=true` |
| `AUTOMAGIK_TELEMETRY_VERBOSE` | boolean | `false` | Enable debug logging to console | `export AUTOMAGIK_TELEMETRY_VERBOSE=true` |
| `AUTOMAGIK_TELEMETRY_BACKEND` | string | `"otlp"` | Backend type: `"otlp"` or `"clickhouse"` | `export AUTOMAGIK_TELEMETRY_BACKEND=clickhouse` |

**Boolean Values:**
- ✅ **Truthy:** `"true"`, `"1"`, `"yes"`, `"on"` (case-insensitive)
- ❌ **Falsy:** `"false"`, `"0"`, `"no"`, `"off"`, or empty

---

### OTLP Backend Configuration

| Variable | Type | Default | Description | Example |
|----------|------|---------|-------------|---------|
| `AUTOMAGIK_TELEMETRY_ENDPOINT` | string | `https://telemetry.namastex.ai/v1/traces` | Main OTLP traces endpoint | `export AUTOMAGIK_TELEMETRY_ENDPOINT=https://custom.example.com/v1/traces` |
| `AUTOMAGIK_TELEMETRY_METRICS_ENDPOINT` | string | Auto-derived from base endpoint | Override metrics endpoint separately | `export AUTOMAGIK_TELEMETRY_METRICS_ENDPOINT=https://custom.example.com/v1/metrics` |
| `AUTOMAGIK_TELEMETRY_LOGS_ENDPOINT` | string | Auto-derived from base endpoint | Override logs endpoint separately | `export AUTOMAGIK_TELEMETRY_LOGS_ENDPOINT=https://custom.example.com/v1/logs` |
| `AUTOMAGIK_TELEMETRY_TIMEOUT` | int | Python: `5` (sec)<br>TypeScript: `5000` (ms) | HTTP request timeout | Python: `export AUTOMAGIK_TELEMETRY_TIMEOUT=10`<br>TypeScript: `export AUTOMAGIK_TELEMETRY_TIMEOUT=10000` |

**🔍 Endpoint Format:**
- Must include protocol: `http://` or `https://`
- Can include path: `/v1/traces`, `/v1/metrics`, `/v1/logs`
- Auto-derives metrics/logs endpoints from base

**📍 Endpoint Hierarchy:**
1. **Base endpoint** (`AUTOMAGIK_TELEMETRY_ENDPOINT`): Primary endpoint for traces
   - If you set `https://telemetry.example.com/v1/traces`, the SDK extracts the base (`https://telemetry.example.com`)
   - Metrics endpoint auto-derives to: `https://telemetry.example.com/v1/metrics`
   - Logs endpoint auto-derives to: `https://telemetry.example.com/v1/logs`

2. **Specific overrides**: Use when routing different signal types to different backends
   - `AUTOMAGIK_TELEMETRY_METRICS_ENDPOINT`: Send metrics to a dedicated metrics service
   - `AUTOMAGIK_TELEMETRY_LOGS_ENDPOINT`: Send logs to a dedicated logging service
   - Example: Route metrics to Prometheus, logs to Loki, traces to Tempo

**💡 When to Use Specific Endpoints:**
- **Same backend for all signals**: Only set `AUTOMAGIK_TELEMETRY_ENDPOINT` (most common)
- **Separate backends per signal type**: Set individual endpoints for advanced routing
  ```bash
  # Route to different OTLP receivers
  export AUTOMAGIK_TELEMETRY_ENDPOINT=https://tempo.example.com/v1/traces
  export AUTOMAGIK_TELEMETRY_METRICS_ENDPOINT=https://prometheus.example.com/v1/metrics
  export AUTOMAGIK_TELEMETRY_LOGS_ENDPOINT=https://loki.example.com/v1/logs
  ```

---

### ClickHouse Backend Configuration

| Variable | Type | Default | Description | Example |
|----------|------|---------|-------------|---------|
| `AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT` | string | `http://localhost:8123` | ClickHouse HTTP API endpoint | `export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://clickhouse.prod.example.com:8123` |
| `AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE` | string | `telemetry` | ClickHouse database name | `export AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE=production_telemetry` |
| `AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE` | string | `traces` | ClickHouse table name | `export AUTOMAGIK_TELEMETRY_CLICKHOUSE_TABLE=app_traces` |
| `AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME` | string | `default` | ClickHouse authentication username | `export AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME=telemetry_writer` |
| `AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD` | string | `""` | ClickHouse authentication password | `export AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD=secret123` |

**🔒 Security Notes:**
- Never commit passwords to version control
- Use secret management for production
- Rotate credentials regularly
- Default ClickHouse port is `8123` (HTTP interface)

---

## 🚀 Quick Setup Examples

### Local Development (OTLP)

```bash
# Enable telemetry for testing
export AUTOMAGIK_TELEMETRY_ENABLED=true
export AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces
export AUTOMAGIK_TELEMETRY_VERBOSE=true
```

---

### Local Development (ClickHouse)

```bash
# Direct ClickHouse backend (simpler stack)
export AUTOMAGIK_TELEMETRY_ENABLED=true
export AUTOMAGIK_TELEMETRY_BACKEND=clickhouse
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://localhost:8123
export AUTOMAGIK_TELEMETRY_VERBOSE=true
```

---

### Production (OTLP)

```bash
# Production OTLP configuration
export ENVIRONMENT=production
export AUTOMAGIK_TELEMETRY_ENABLED=true
export AUTOMAGIK_TELEMETRY_ENDPOINT=https://collector.prod.example.com/v1/traces
export AUTOMAGIK_TELEMETRY_TIMEOUT=10
```

---

### Production (ClickHouse)

```bash
# Production ClickHouse configuration
export ENVIRONMENT=production
export AUTOMAGIK_TELEMETRY_ENABLED=true
export AUTOMAGIK_TELEMETRY_BACKEND=clickhouse
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=https://clickhouse.prod.example.com:8443
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE=production_telemetry
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME=telemetry_user
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD=secret123
```

---

### Disable Telemetry

```bash
# Method 1: Environment variable (temporary)
export AUTOMAGIK_TELEMETRY_ENABLED=false

# Method 2: Opt-out file (permanent)
touch ~/.automagik-no-telemetry

# Method 3: Development environment (auto-disabled)
export ENVIRONMENT=development
```

---

## 🔄 Auto-Disable Environments

Telemetry **automatically disables** in these environments:

### CI/CD Environments

```bash
# Any of these variables set = telemetry disabled
CI=true
GITHUB_ACTIONS=true
TRAVIS=true
JENKINS=true
GITLAB_CI=true
CIRCLECI=true
```

### Development Environments

```bash
# Any of these values = telemetry disabled
ENVIRONMENT=development
ENVIRONMENT=dev
ENVIRONMENT=test
ENVIRONMENT=testing
```

### File-Based Opt-Out

```bash
# Presence of this file = telemetry disabled
~/.automagik-no-telemetry
```

**💡 Override Auto-Disable:**
```bash
# Force enable even in dev/CI
export AUTOMAGIK_TELEMETRY_ENABLED=true
```

---

## 📐 Platform-Specific Notes

### Python

**Time Units:**
- `AUTOMAGIK_TELEMETRY_TIMEOUT`: **seconds** (integer)
- Example: `5` = 5 seconds

**Default Batch Size:**
- `batch_size=1` (immediate send)
- Override in code: `TelemetryConfig(batch_size=100)`

---

### TypeScript

**Time Units:**
- `AUTOMAGIK_TELEMETRY_TIMEOUT`: **milliseconds** (integer)
- Example: `5000` = 5 seconds

**Default Batch Size:**
- `batchSize=100` (batched send)
- Override in code: `{ batchSize: 1 }`

---

## 🎯 Common Patterns

### Dynamic Backend Selection

**Shell Script:**
```bash
#!/bin/bash

# Select backend based on deployment
if [ "$DEPLOYMENT" = "self-hosted" ]; then
  export AUTOMAGIK_TELEMETRY_BACKEND=clickhouse
  export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://clickhouse.internal:8123
else
  export AUTOMAGIK_TELEMETRY_BACKEND=otlp
  export AUTOMAGIK_TELEMETRY_ENDPOINT=https://telemetry.namastex.ai/v1/traces
fi

export AUTOMAGIK_TELEMETRY_ENABLED=true
```

---

### Docker Compose

```yaml
services:
  app:
    environment:
      - AUTOMAGIK_TELEMETRY_ENABLED=true
      - AUTOMAGIK_TELEMETRY_BACKEND=clickhouse
      - AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://clickhouse:8123
      - AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE=telemetry
```

---

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: telemetry-config
data:
  AUTOMAGIK_TELEMETRY_ENABLED: "true"
  AUTOMAGIK_TELEMETRY_BACKEND: "otlp"
  AUTOMAGIK_TELEMETRY_ENDPOINT: "https://collector.prod.example.com/v1/traces"
  AUTOMAGIK_TELEMETRY_TIMEOUT: "10"
```

---

### .env File

```bash
# .env.production
ENVIRONMENT=production
AUTOMAGIK_TELEMETRY_ENABLED=true
AUTOMAGIK_TELEMETRY_BACKEND=clickhouse
AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://clickhouse.prod.example.com:8123
AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE=production_telemetry
AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME=telemetry_user
AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD}
```

---

## ✅ Validation Checklist

### Before Deployment

- [ ] `AUTOMAGIK_TELEMETRY_ENABLED` is set correctly
- [ ] Backend type matches infrastructure (`otlp` or `clickhouse`)
- [ ] Endpoint URL is valid and accessible
- [ ] Authentication credentials are in secret manager (not hardcoded)
- [ ] Timeout values are appropriate for network latency
- [ ] Database/table names match existing infrastructure
- [ ] Test with `AUTOMAGIK_TELEMETRY_VERBOSE=true` first

---

### After Deployment

- [ ] Telemetry data appears in backend (ClickHouse or Collector)
- [ ] No error messages in application logs
- [ ] Performance impact is acceptable (< 1ms overhead)
- [ ] No PII is being sent (review sample data)
- [ ] Batch sizes are tuned for traffic volume

---

## 🔍 Troubleshooting Quick Check

```bash
# Check current environment
echo "Enabled: $AUTOMAGIK_TELEMETRY_ENABLED"
echo "Backend: $AUTOMAGIK_TELEMETRY_BACKEND"
echo "Endpoint: $AUTOMAGIK_TELEMETRY_ENDPOINT"
echo "Verbose: $AUTOMAGIK_TELEMETRY_VERBOSE"
echo "Environment: $ENVIRONMENT"

# Check opt-out file
ls -la ~/.automagik-no-telemetry 2>/dev/null && echo "Opt-out file EXISTS" || echo "Opt-out file NOT FOUND"

# Check CI detection
env | grep -E "^(CI|GITHUB_ACTIONS|TRAVIS|JENKINS|GITLAB_CI|CIRCLECI)=" && echo "CI detected" || echo "Not in CI"
```

---

## 📚 Related Documentation

- [API Reference](./API_REFERENCE.md) - Full SDK API documentation
- [Troubleshooting](./TROUBLESHOOTING.md) - Common issues and solutions
- [Configuration Reference](../USER_GUIDES/CONFIGURATION.md) - Detailed configuration guide
- [ClickHouse Backend Guide](../USER_GUIDES/BACKENDS.md) - ClickHouse backend architecture

---

**Built with ❤️ by [Namastex Labs](https://namastex.ai)**
