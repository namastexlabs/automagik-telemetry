# 🏗️ Automagik Telemetry Infrastructure

📚 See [Documentation Index](../docs/INDEX.md) for complete guides

Self-hosted telemetry infrastructure for local development and production deployments.

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- 4GB+ RAM recommended
- Ports 3000, 4317, 4318, 8123, 9000 available

### Start Everything

```bash
cd infra
make start
```

That's it! Services will start in the background.

### Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / admin |
| **ClickHouse** | http://localhost:8123 | telemetry / telemetry_password |
| **OTLP Collector** | http://localhost:4318 | - |

### Send Test Data

```bash
make test
```

Then view the data in Grafana:

```bash
make dashboard
```

### Backend Selection

You can use either backend depending on your needs:

**Option 1: OTLP Backend (Default - For Production)**
```bash
export AUTOMAGIK_TELEMETRY_BACKEND=otlp
export AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces
```

**Option 2: ClickHouse Direct Backend (Recommended for Local Dev)**
```bash
export AUTOMAGIK_TELEMETRY_BACKEND=clickhouse
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://localhost:8123
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE=telemetry
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME=telemetry
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD=telemetry_password
```

> **Note**: The ClickHouse direct backend bypasses the OTLP collector entirely, writing directly to ClickHouse. This is more reliable for local development due to bugs in the OTLP ClickHouse exporter.

## 📋 Available Commands

```bash
make help              # Show all available commands
make start             # Start all services
make stop              # Stop all services
make restart           # Restart all services
make logs              # View logs from all services
make status            # Show service status
make health            # Check service health
make dashboard         # Open Grafana in browser
make test              # Send test telemetry data
make query             # Interactive ClickHouse query
make query-traces      # Show recent traces
make query-stats       # Show statistics
make clean             # Remove all data (destructive!)
make reset             # Reset data but keep services running
```

## 🏛️ Architecture

### Overview

Automagik Telemetry supports **two backend options** for sending telemetry data:

1. **OTLP Backend** (Production): Standard OpenTelemetry Protocol via Collector
2. **ClickHouse Direct Backend** (Local/Self-hosted): Direct insertion bypassing the collector

```
┌─────────────────────────────────────────────────────────────┐
│                    DUAL BACKEND ARCHITECTURE                 │
└─────────────────────────────────────────────────────────────┘

PATH 1: OTLP Backend (Production - Default)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────┐
│   SDK       │  Your Application
│  (Python/   │  backend="otlp"
│  TypeScript)│
└──────┬──────┘
       │ OTLP/HTTP
       ↓
┌──────────────┐
│ OTLP         │  OpenTelemetry Collector
│ Collector    │  Receives & processes telemetry
│ :4318 :4317  │
└──────┬───────┘
       │
       ↓
┌──────────────┐
│ ClickHouse   │  OLAP Database
│ :8123 :9000  │  Stores telemetry data
└──────┬───────┘
       │
       ↓
┌──────────────┐
│ Grafana      │  Visualization
│ :3000        │  Dashboards & Analytics
└──────────────┘


PATH 2: ClickHouse Direct Backend (Local/Self-hosted)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────┐
│   SDK       │  Your Application
│  (Python/   │  backend="clickhouse"
│  TypeScript)│
└──────┬──────┘
       │ Direct HTTP API
       │ (JSONEachRow format)
       ↓
┌──────────────┐
│ ClickHouse   │  OLAP Database
│ :8123 :9000  │  Direct insertion ✅
└──────┬───────┘
       │
       ↓
┌──────────────┐
│ Grafana      │  Visualization
│ :3000        │  Dashboards & Analytics
└──────────────┘
```

### Why Two Backends?

**OTLP Backend** is the default for production:
- Industry-standard OpenTelemetry Protocol
- Collector handles buffering, retries, and backpressure
- Works with any OTLP-compatible backend
- Suitable for cloud deployments

**ClickHouse Direct Backend** was created for local development:
- ❌ **Problem**: OTLP Collector's ClickHouse exporter has a bug causing crashes
- ✅ **Solution**: Bypass the collector and write directly to ClickHouse
- 🚀 **Benefits**: Simpler, faster, no middleware bugs, full control
- 🎯 **Use case**: Self-hosted deployments, local development

See [CLICKHOUSE_BACKEND_DESIGN.md](./CLICKHOUSE_BACKEND_DESIGN.md) for full technical details.

### Components

#### 1. **OTLP Collector** (Port 4318/4317) - Optional

Receives telemetry data using OpenTelemetry Protocol:
- **HTTP endpoint**: `http://localhost:4318/v1/traces`
- **gRPC endpoint**: `http://localhost:4317`
- Batches and processes events
- Exports to ClickHouse

Configuration: `collector/otel-collector-config.yaml`

**Note**: The collector has a known bug with the ClickHouse exporter. For local development, we recommend using the ClickHouse direct backend instead.

#### 2. **ClickHouse** (Port 8123/9000)

High-performance OLAP database:
- Stores all telemetry traces
- Aggregates metrics hourly
- 90-day data retention (configurable)
- Optimized for analytics queries
- **Supports direct insertion** from SDKs via HTTP API

Schema: `clickhouse/init-db.sql`

**ClickHouse Direct Backend Features:**
- **Zero dependencies**: Uses only standard library HTTP clients
- **Batching**: Queues rows and inserts in batches (default: 100 rows)
- **Compression**: Gzip compression reduces bandwidth by 70-90%
- **Retry logic**: Automatic retries with exponential backoff
- **Schema transformation**: Converts OTLP format to our custom schema
- **Silent failures**: Never crashes your application

**Configuration Options:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `endpoint` | `http://localhost:8123` | ClickHouse HTTP API endpoint |
| `database` | `telemetry` | Database name |
| `table` | `traces` | Table name for traces |
| `username` | `default` | ClickHouse username |
| `password` | `` | ClickHouse password |
| `timeout` | `5` seconds | HTTP request timeout |
| `batch_size` | `100` | Rows to batch before insert |
| `compression_enabled` | `true` | Enable gzip compression |
| `max_retries` | `3` | Maximum retry attempts |

#### 3. **Grafana** (Port 3000)

Visualization and dashboards:
- Pre-configured ClickHouse datasource
- Telemetry overview dashboard
- Custom dashboards can be added
- Works with both OTLP and direct backend data

Dashboards: `grafana/dashboards/`

## 🔧 Configuration

### Environment Variables

Create `.env` file in `infra/` directory:

```bash
# ClickHouse
CLICKHOUSE_PASSWORD=your_secure_password

# Collector
ENVIRONMENT=production

# Grafana
GF_SECURITY_ADMIN_PASSWORD=your_admin_password
```

### Backend Configuration

#### OTLP Backend (Default)

Point your SDK to the local collector:

**Python:**
```python
from automagik_telemetry import AutomagikTelemetry

client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    backend="otlp",  # Default
    endpoint="http://localhost:4318/v1/traces"
)
```

**TypeScript:**
```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const client = new AutomagikTelemetry({
  projectName: 'my-app',
  version: '1.0.0',
  backend: 'otlp',  // Default
  endpoint: 'http://localhost:4318/v1/traces'
});
```

**Environment Variable:**
```bash
export AUTOMAGIK_TELEMETRY_BACKEND=otlp
export AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces
```

#### ClickHouse Direct Backend

For local development, bypass the collector:

**Python:**
```python
from automagik_telemetry import AutomagikTelemetry

client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    backend="clickhouse",
    clickhouse_endpoint="http://localhost:8123",
    clickhouse_database="telemetry",
    clickhouse_username="telemetry",
    clickhouse_password="telemetry_password",
    clickhouse_batch_size=100  # Optional: rows per batch
)
```

**TypeScript:**
```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const client = new AutomagikTelemetry({
  projectName: 'my-app',
  version: '1.0.0',
  backend: 'clickhouse',
  clickhouseEndpoint: 'http://localhost:8123',
  clickhouseDatabase: 'telemetry',
  clickhouseUsername: 'telemetry',
  clickhousePassword: 'telemetry_password',
  clickhouseBatchSize: 100  // Optional: rows per batch
});
```

**Environment Variables:**
```bash
export AUTOMAGIK_TELEMETRY_BACKEND=clickhouse
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://localhost:8123
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_DATABASE=telemetry
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME=telemetry
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD=telemetry_password
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_BATCH_SIZE=100  # Optional
```

#### When to Use Each Backend

| Factor | OTLP Backend | ClickHouse Direct Backend |
|--------|--------------|---------------------------|
| **Use Case** | Production deployments | Local dev, self-hosting |
| **Reliability** | Collector handles retries | SDK handles retries |
| **Performance** | Collector batching | Direct insertion (faster) |
| **Dependencies** | Requires OTLP Collector | Direct to ClickHouse |
| **Flexibility** | Standard OTLP protocol | Custom schema control |
| **Bugs** | ClickHouse exporter bug | No exporter (works) ✅ |

**Recommendation**: Use ClickHouse direct backend for local development to avoid the OTLP exporter bug.

#### Performance Characteristics

**ClickHouse Direct Backend:**

| Metric | Without Batching | With Batching (100 rows) |
|--------|------------------|--------------------------|
| HTTP Requests | 1000 | 10 |
| Network Overhead | ~100KB | ~10KB |
| Typical Latency | ~1000ms | ~100ms |
| With Compression | N/A | ~1-2KB (10x reduction) |

**Memory Usage:**
- Bounded by batch size: `batch_size × avg_row_size`
- Example: 100 rows × 1KB/row = ~100KB maximum
- Memory released immediately after flush

**Network Efficiency:**
- Without compression: ~1KB per row
- With compression: ~100-200 bytes per row (70-90% reduction)
- Batch mode: Single HTTP request per 100 rows (default)

**Data Flow Comparison:**

```
OTLP Backend (3 hops):
SDK → OTLP Protocol → Collector → ClickHouse Exporter → ClickHouse
     (serialize)      (buffer)     (transform)          (insert)
     ~5ms             ~10ms        ~20ms                ~10ms
     Total: ~45ms per batch

Direct Backend (1 hop):
SDK → ClickHouse HTTP API → ClickHouse
     (transform + batch)    (insert)
     ~5ms                   ~10ms
     Total: ~15ms per batch (3x faster!)
```

## 📊 Using Grafana

### Default Dashboard

1. Start services: `make start`
2. Open Grafana: `make dashboard`
3. Login with `admin` / `admin`
4. Navigate to "Automagik Telemetry Overview"

The default dashboard shows:
- Total events count
- Events over time
- Events by project
- Top events table
- Error count

### Creating Custom Dashboards

1. Open Grafana (http://localhost:3000)
2. Click **+ → Dashboard**
3. Add panel
4. Select **ClickHouse** datasource
5. Write SQL queries against `telemetry.traces` table

Example queries:

```sql
-- Events over time
SELECT
  toStartOfInterval(timestamp, INTERVAL 1 minute) as time,
  count() as events
FROM telemetry.traces
WHERE $__timeFilter(timestamp)
GROUP BY time
ORDER BY time

-- Top events
SELECT
  span_name,
  count() as count
FROM telemetry.traces
WHERE $__timeFilter(timestamp)
GROUP BY span_name
ORDER BY count DESC
LIMIT 10

-- Error rate
SELECT
  toStartOfHour(timestamp) as time,
  countIf(status_code = 'OK') / count() * 100 as success_rate
FROM telemetry.traces
WHERE $__timeFilter(timestamp)
GROUP BY time
ORDER BY time
```

## 🗄️ Database Schema

### `traces` Table

Main table storing all telemetry events:

| Column | Type | Description |
|--------|------|-------------|
| `trace_id` | String | Unique trace identifier |
| `span_id` | String | Unique span identifier |
| `timestamp` | DateTime64 | Event timestamp |
| `service_name` | String | Service/application name |
| `span_name` | String | Event name |
| `status_code` | String | OK or ERROR |
| `duration_ms` | UInt32 | Event duration |
| `project_name` | String | Project identifier |
| `project_version` | String | Project version |
| `environment` | String | deployment environment |
| `attributes` | Map(String, String) | Custom event attributes |

### `metrics_hourly` Table

Aggregated metrics for faster queries:

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | DateTime | Hour bucket |
| `project_name` | String | Project identifier |
| `total_count` | UInt64 | Total events |
| `error_count` | UInt64 | Error count |
| `p50_duration_ms` | Float64 | 50th percentile latency |
| `p95_duration_ms` | Float64 | 95th percentile latency |
| `p99_duration_ms` | Float64 | 99th percentile latency |

## 🔒 Security

### Production Recommendations

1. **Change default passwords** in `.env`
2. **Enable TLS** for all services
3. **Restrict network access** using firewall rules
4. **Use authentication** for ClickHouse and Grafana
5. **Regular backups**: `make backup`

### Network Security

For production, configure firewall rules:

```bash
# Allow only internal network to access services
ufw allow from 10.0.0.0/8 to any port 4318
ufw allow from 10.0.0.0/8 to any port 8123
ufw allow from 10.0.0.0/8 to any port 3000
```

### TLS Configuration

For production, add TLS certificates:

1. Place certificates in `certs/` directory
2. Update `docker-compose.yml` with volume mounts
3. Configure TLS in each service's config file

## 🚀 Production Deployment

### Docker Swarm

```bash
docker stack deploy -c docker-compose.yml telemetry
```

### Kubernetes

Helm chart coming soon! For now, convert using:

```bash
kompose convert -f docker-compose.yml
```

### Cloud Providers

#### AWS

- Use RDS for ClickHouse or EC2 with EBS
- Deploy collector on ECS/EKS
- Use ALB for load balancing

#### GCP

- Use Cloud SQL or GCE with persistent disks
- Deploy on GKE
- Use Cloud Load Balancer

#### Azure

- Use Azure Database for ClickHouse or VMs
- Deploy on AKS
- Use Azure Load Balancer

## 📈 Scaling

### Horizontal Scaling

**Collectors** (stateless):
```yaml
collector:
  deploy:
    replicas: 3
```

**ClickHouse** (sharding):
- Configure ClickHouse cluster
- See [ClickHouse docs](https://clickhouse.com/docs/en/guides/sre/scaling-clusters/)

### Vertical Scaling

Adjust resource limits in `docker-compose.yml`:

```yaml
services:
  clickhouse:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

## 🐛 Troubleshooting

### Services won't start

```bash
# Check logs
make logs

# Check specific service
make logs-clickhouse
make logs-collector
make logs-grafana
```

### No data in Grafana

1. Check collector is receiving data:
   ```bash
   make logs-collector
   ```

2. Check ClickHouse has data:
   ```bash
   make query-traces
   ```

3. Send test data:
   ```bash
   make test
   ```

### High memory usage

1. Reduce batch sizes in `collector/otel-collector-config.yaml`
2. Adjust TTL in `clickhouse/init-db.sql`
3. Configure memory limits in `docker-compose.yml`

### Port conflicts

Edit `docker-compose.yml` to use different ports:

```yaml
ports:
  - "13000:3000"  # Change Grafana to port 13000
```

### ClickHouse Direct Backend Issues

#### Issue: No data appearing when using ClickHouse backend

**Diagnosis:**
```bash
# 1. Check SDK logs (should show "Flushed N rows to ClickHouse")
# In your application logs, look for:
# - "Flushed X rows to ClickHouse"
# - HTTP errors or connection timeouts

# 2. Verify ClickHouse is accessible
curl -u telemetry:telemetry_password http://localhost:8123/ping
# Should return: Ok.

# 3. Check if data reached ClickHouse
make query-traces
# or
docker exec automagik-clickhouse clickhouse-client \
  --user telemetry \
  --password telemetry_password \
  --query "SELECT count() FROM telemetry.traces"
```

**Solutions:**
- Ensure ClickHouse is running: `make status`
- Check credentials match in both SDK and docker-compose.yml
- Verify database exists: `make query`
- Check firewall isn't blocking port 8123

#### Issue: "Authentication failed" errors

**Cause**: Incorrect ClickHouse credentials

**Solution:**
```bash
# Check current credentials in docker-compose.yml
cat docker-compose.yml | grep CLICKHOUSE

# Update your SDK configuration to match:
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_USERNAME=telemetry
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_PASSWORD=telemetry_password
```

#### Issue: "Database doesn't exist" error

**Cause**: ClickHouse database not initialized

**Solution:**
```bash
# Restart services to trigger initialization
make restart

# Or manually create database
docker exec automagik-clickhouse clickhouse-client --query="
CREATE DATABASE IF NOT EXISTS telemetry
"

# Then run init script
docker exec automagik-clickhouse clickhouse-client \
  --database telemetry \
  --queries-file /docker-entrypoint-initdb.d/init-db.sql
```

#### Issue: High latency or slow insertions

**Diagnosis:**
```bash
# Check batch sizes in SDK logs
# Look for: "Flushed X rows to ClickHouse in Y seconds"
```

**Solutions:**
1. **Increase batch size** (default: 100):
   ```python
   client = AutomagikTelemetry(
       backend="clickhouse",
       clickhouse_batch_size=500  # Higher batching = fewer HTTP requests
   )
   ```

2. **Enable compression** (default: enabled):
   ```python
   client = AutomagikTelemetry(
       backend="clickhouse",
       clickhouse_compression_enabled=True  # Reduces network bandwidth
   )
   ```

3. **Check network latency**:
   ```bash
   # Test HTTP latency to ClickHouse
   time curl -u telemetry:telemetry_password http://localhost:8123/ping
   ```

#### Issue: OTLP Collector crash with "data size should be 0 < 540700271"

**Cause**: This is the bug we're avoiding! The OTLP ClickHouse exporter crashes.

**Solution**: Use ClickHouse direct backend instead:
```bash
export AUTOMAGIK_TELEMETRY_BACKEND=clickhouse
export AUTOMAGIK_TELEMETRY_CLICKHOUSE_ENDPOINT=http://localhost:8123
```

**Why this works**: The direct backend bypasses the buggy OTLP exporter entirely.

#### Issue: Data visible in ClickHouse but not in Grafana

**Diagnosis:**
```bash
# 1. Verify data exists
make query-traces

# 2. Check Grafana datasource connection
curl -u admin:admin http://localhost:3000/api/datasources
```

**Solutions:**
1. Restart Grafana: `docker restart automagik-grafana`
2. Refresh dashboard: Open Grafana and click refresh button
3. Check time range: Ensure dashboard time range includes your data
4. Verify datasource is configured correctly in Grafana

#### Issue: SDK not flushing data (app exits before flush)

**Cause**: Batch not full when application terminates

**Solution**: Call `flush()` before exit:

**Python:**
```python
from automagik_telemetry import AutomagikTelemetry

client = AutomagikTelemetry(backend="clickhouse", ...)

# Your application logic
client.track_event("my.event")

# Before exit, flush pending batches
client.flush()  # Forces immediate insertion
```

**TypeScript:**
```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const client = new AutomagikTelemetry({ backend: 'clickhouse', ... });

// Your application logic
client.trackEvent('my.event');

// Before exit, flush pending batches
await client.flush();  // Forces immediate insertion
```

Or reduce batch size for testing:
```python
client = AutomagikTelemetry(
    backend="clickhouse",
    clickhouse_batch_size=1  # Flush every event (not recommended for prod)
)
```

#### Issue: Connection timeouts

**Cause**: Network issues or ClickHouse overloaded

**Solutions:**
1. **Increase timeout**:
   ```python
   client = AutomagikTelemetry(
       backend="clickhouse",
       clickhouse_timeout=10  # Increase from default 5 seconds
   )
   ```

2. **Check ClickHouse health**:
   ```bash
   make health
   docker stats automagik-clickhouse
   ```

3. **Reduce load**: Lower batch size or increase flush interval

#### Debugging Tips

**Enable verbose logging (Python):**
```python
import logging
logging.basicConfig(level=logging.DEBUG)

from automagik_telemetry import AutomagikTelemetry
client = AutomagikTelemetry(backend="clickhouse", ...)
```

**Enable verbose logging (TypeScript):**
```typescript
// Set environment variable before running
process.env.DEBUG = 'automagik:*';

import { AutomagikTelemetry } from '@automagik/telemetry';
const client = new AutomagikTelemetry({ backend: 'clickhouse', ... });
```

**Monitor ClickHouse query log:**
```bash
docker exec automagik-clickhouse clickhouse-client --query="
SELECT
    event_time,
    query,
    exception
FROM system.query_log
WHERE event_time > now() - INTERVAL 10 MINUTE
ORDER BY event_time DESC
LIMIT 20
FORMAT Vertical
"
```

**Test direct insertion:**
```bash
# Test inserting data directly to ClickHouse
curl -u telemetry:telemetry_password \
  -X POST "http://localhost:8123/?query=INSERT%20INTO%20telemetry.traces%20FORMAT%20JSONEachRow" \
  -d '{"trace_id":"test123","span_id":"span123","timestamp":"2025-10-22 00:00:00","service_name":"test","span_name":"test.event","status_code":"OK","duration_ms":100,"project_name":"test","project_version":"1.0.0","environment":"local","attributes":{}}'

# Verify insertion
make query-traces
```

## 📚 Additional Resources

### Documentation
- [ClickHouse Backend Design Document](./CLICKHOUSE_BACKEND_DESIGN.md) - **Read this for full technical details**
- [ClickHouse Documentation](https://clickhouse.com/docs)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Grafana Documentation](https://grafana.com/docs/)
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/)

### ClickHouse Backend Resources
- [Python Backend Implementation](../python/src/automagik_telemetry/backends/clickhouse.py)
- [TypeScript Backend Implementation](../typescript/src/backends/clickhouse.ts)
- [Python Integration Tests](../python/tests/integration/test_clickhouse_integration.py)
- [TypeScript Integration Tests](../typescript/tests/clickhouse.integration.test.ts)

## 📖 Related Documentation

For comprehensive guides and additional information, see:

- **[Self-Hosting Guide](../docs/USER_GUIDES/SELF_HOSTING.md)** - Complete guide for self-hosted deployments
- **[Backend Configuration Guide](../docs/USER_GUIDES/BACKENDS.md)** - Detailed backend configuration options
- **[Architecture Overview](../docs/DEVELOPER_GUIDES/ARCHITECTURE.md)** - System architecture and design decisions
- **[Troubleshooting Guide](../docs/REFERENCES/TROUBLESHOOTING.md)** - Common issues and solutions

## 🆘 Support

- GitHub Issues: [Create an issue](https://github.com/namastexlabs/automagik-telemetry/issues)
- Discord: [Join our community](https://discord.gg/xcW8c7fF3R)
- Documentation: [Full docs](https://github.com/namastexlabs/automagik-telemetry)

## 📄 License

MIT License - see [LICENSE](../LICENSE) for details.
