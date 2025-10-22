# 🏗️ Automagik Telemetry Infrastructure

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

```
┌─────────────┐
│   SDK       │  Your Application
│  (Python/   │
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
```

### Components

#### 1. **OTLP Collector** (Port 4318/4317)

Receives telemetry data using OpenTelemetry Protocol:
- **HTTP endpoint**: `http://localhost:4318/v1/traces`
- **gRPC endpoint**: `http://localhost:4317`
- Batches and processes events
- Exports to ClickHouse

Configuration: `collector/otel-collector-config.yaml`

#### 2. **ClickHouse** (Port 8123/9000)

High-performance OLAP database:
- Stores all telemetry traces
- Aggregates metrics hourly
- 90-day data retention (configurable)
- Optimized for analytics queries

Schema: `clickhouse/init-db.sql`

#### 3. **Grafana** (Port 3000)

Visualization and dashboards:
- Pre-configured ClickHouse datasource
- Telemetry overview dashboard
- Custom dashboards can be added

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

### Custom Endpoint

Point your SDK to the local collector:

**Python:**
```python
from automagik_telemetry import TelemetryClient

client = TelemetryClient(
    project_name="my-app",
    version="1.0.0",
    endpoint="http://localhost:4318/v1/traces"
)
```

**TypeScript:**
```typescript
import { TelemetryClient } from '@automagik/telemetry';

const client = new TelemetryClient({
  projectName: 'my-app',
  version: '1.0.0',
  endpoint: 'http://localhost:4318/v1/traces'
});
```

**Environment Variable:**
```bash
export AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces
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

## 📚 Additional Resources

- [ClickHouse Documentation](https://clickhouse.com/docs)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Grafana Documentation](https://grafana.com/docs/)
- [OTLP Specification](https://opentelemetry.io/docs/specs/otlp/)

## 🆘 Support

- GitHub Issues: [Create an issue](https://github.com/namastexlabs/automagik-telemetry/issues)
- Discord: [Join our community](https://discord.gg/xcW8c7fF3R)
- Documentation: [Full docs](https://github.com/namastexlabs/automagik-telemetry)

## 📄 License

MIT License - see [LICENSE](../LICENSE) for details.
