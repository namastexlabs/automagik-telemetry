# Architecture Deep Dive

<p align="center">
  <strong>🏗️ Complete architectural overview of Automagik Telemetry SDK</strong><br>
  System design, data flows, component interactions, and technical decisions
</p>

---

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Patterns](#architecture-patterns)
- [Component Design](#component-design)
- [Data Flow](#data-flow)
- [Backend Architectures](#backend-architectures)
- [Deployment Models](#deployment-models)
- [Performance Characteristics](#performance-characteristics)
- [Security Architecture](#security-architecture)

---

## System Overview

### High-Level Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        APP[Your Application]
        SDK[Automagik Telemetry SDK]
    end

    subgraph "Transport Layer"
        OTLP[OTLP Backend]
        CH[ClickHouse Backend]
    end

    subgraph "Collection Layer"
        COLLECTOR[OpenTelemetry Collector]
        CHDB[(ClickHouse Database)]
    end

    subgraph "Storage Layer"
        PROM[(Prometheus)]
        CHSTORE[(ClickHouse Storage)]
    end

    subgraph "Visualization Layer"
        GRAFANA[Grafana]
    end

    APP -->|track_event| SDK
    SDK -->|Privacy Checks| SDK
    SDK -->|Backend Selection| OTLP
    SDK -->|Backend Selection| CH

    OTLP -->|OTLP/HTTP| COLLECTOR
    CH -->|HTTP API| CHDB

    COLLECTOR -->|Metrics| PROM
    COLLECTOR -->|Traces| CHDB
    CHDB -->|Storage| CHSTORE

    PROM -->|Query| GRAFANA
    CHSTORE -->|Query| GRAFANA

    style SDK fill:#00D9FF,stroke:#333,stroke-width:3px
    style OTLP fill:#FFB84D,stroke:#333,stroke-width:2px
    style CH fill:#FFB84D,stroke:#333,stroke-width:2px
```

### C4 Model: System Context

```mermaid
C4Context
    title System Context Diagram - Automagik Telemetry

    Person(developer, "Developer", "Uses SDK in application")
    System(sdk, "Automagik Telemetry SDK", "Privacy-first telemetry client")
    System_Ext(collector, "OpenTelemetry Collector", "Receives OTLP telemetry")
    System_Ext(clickhouse, "ClickHouse", "OLAP database for analytics")
    System_Ext(prometheus, "Prometheus", "Metrics storage")
    System_Ext(grafana, "Grafana", "Metrics visualization")

    Rel(developer, sdk, "Integrates", "Python/TypeScript")
    Rel(sdk, collector, "Sends telemetry", "OTLP/HTTP")
    Rel(sdk, clickhouse, "Sends telemetry", "HTTP API")
    Rel(collector, prometheus, "Exports metrics", "Remote Write")
    Rel(collector, clickhouse, "Exports traces", "Native Protocol")
    Rel(grafana, prometheus, "Queries", "PromQL")
    Rel(grafana, clickhouse, "Queries", "SQL")
```

### C4 Model: Container Diagram

```mermaid
C4Container
    title Container Diagram - SDK Internal Architecture

    Container(client, "TelemetryClient", "Python/TypeScript", "Main SDK entry point")
    Container(config, "Configuration", "Config Module", "Manages settings & env vars")
    Container(privacy, "Privacy Engine", "Privacy Module", "PII detection & sanitization")
    Container(otlp_backend, "OTLP Backend", "Backend Module", "OTLP protocol implementation")
    Container(ch_backend, "ClickHouse Backend", "Backend Module", "Direct ClickHouse insertion")
    Container(batch, "Batch Processor", "Internal", "Event batching & compression")
    Container(retry, "Retry Handler", "Internal", "Exponential backoff logic")

    Rel(client, config, "Reads configuration")
    Rel(client, privacy, "Sanitizes data")
    Rel(client, otlp_backend, "Sends via OTLP")
    Rel(client, ch_backend, "Sends direct")
    Rel(otlp_backend, batch, "Batches events")
    Rel(ch_backend, batch, "Batches rows")
    Rel(batch, retry, "Handles failures")
```

---

## Architecture Patterns

### Design Principles

| Principle | Implementation | Rationale |
|-----------|---------------|-----------|
| **Privacy-First** | Opt-in by default, environment detection, PII sanitization | User privacy is non-negotiable |
| **Zero Dependencies** | Pure stdlib implementation | No bloat, no version conflicts |
| **Fail-Safe** | Silent failures, graceful degradation | Telemetry never breaks the app |
| **Backend Agnostic** | Pluggable backend architecture | Flexibility for different deployment models |
| **Performance Optimized** | Async by default, batching, compression | Minimal application overhead |

### Architectural Patterns Used

#### 1. **Strategy Pattern** (Backend Selection)

```mermaid
classDiagram
    class TelemetryClient {
        -Backend backend
        +track_event()
        +track_metric()
        +flush()
    }

    class Backend {
        <<interface>>
        +send_trace()
        +send_metric()
        +flush()
    }

    class OTLPBackend {
        +send_trace()
        +send_metric()
        +flush()
    }

    class ClickHouseBackend {
        +send_trace()
        +send_metric()
        +flush()
    }

    TelemetryClient --> Backend
    Backend <|-- OTLPBackend
    Backend <|-- ClickHouseBackend
```

#### 2. **Builder Pattern** (Configuration)

```python
# Fluent configuration API
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    backend="clickhouse",
    clickhouse_endpoint="http://localhost:8123",
    batch_size=100
)
```

#### 3. **Observer Pattern** (Event Tracking)

```mermaid
sequenceDiagram
    participant App
    participant Client
    participant Privacy
    participant Backend
    participant Collector

    App->>Client: track_event("user.login", {...})
    Client->>Privacy: sanitize_attributes({...})
    Privacy-->>Client: sanitized_attrs
    Client->>Backend: send_trace(span)
    Backend->>Backend: add_to_batch()

    alt Batch Full
        Backend->>Collector: HTTP POST (batched)
        Collector-->>Backend: 200 OK
    else Batch Not Full
        Backend->>Backend: queue event
    end
```

#### 4. **Circuit Breaker Pattern** (Retry Logic)

```mermaid
stateDiagram-v2
    [*] --> Closed: Initial State
    Closed --> Open: Max Failures Reached
    Open --> HalfOpen: Timeout Elapsed
    HalfOpen --> Closed: Success
    HalfOpen --> Open: Failure
    Closed --> Closed: Success

    note right of Open: Stop sending requests<br/>Log errors silently
    note right of HalfOpen: Test connection<br/>Single request
    note right of Closed: Normal operation<br/>Send telemetry
```

---

## Component Design

### Core Components

#### 1. TelemetryClient

**Responsibilities:**
- Public API for tracking events, metrics, logs, errors
- Configuration management
- Privacy enforcement
- Backend coordination

**Class Diagram:**

```mermaid
classDiagram
    class AutomagikTelemetry {
        -TelemetryConfig config
        -Backend backend
        -PrivacyEngine privacy
        -bool enabled

        +__init__(project_name, version, **kwargs)
        +track_event(name, attributes)
        +track_metric(name, value, type, attributes)
        +track_log(message, level, attributes)
        +track_error(error, attributes)
        +flush()
        +shutdown()

        -_should_send() bool
        -_create_trace_span() dict
        -_create_metric_data() dict
    }

    class TelemetryConfig {
        +str project_name
        +str version
        +str backend
        +str endpoint
        +int batch_size
        +float flush_interval
        +bool compression_enabled

        +from_env() TelemetryConfig
        +validate()
    }

    class PrivacyEngine {
        +sanitize_attributes(attrs) dict
        +detect_pii(value) bool
        +hash_sensitive(value) str
        +anonymize_user_id(uid) str
    }

    AutomagikTelemetry --> TelemetryConfig
    AutomagikTelemetry --> PrivacyEngine
    AutomagikTelemetry --> Backend
```

#### 2. Backend System

**Component Hierarchy:**

```mermaid
graph TD
    subgraph "Backend Abstraction"
        BASE[Backend Base Class]
    end

    subgraph "OTLP Backend"
        OTLP[OTLPBackend]
        OTLP_BATCH[Batch Processor]
        OTLP_HTTP[HTTP Client]
        OTLP_RETRY[Retry Handler]
    end

    subgraph "ClickHouse Backend"
        CH[ClickHouseBackend]
        CH_TRANSFORM[OTLP → CH Transformer]
        CH_BATCH[Batch Processor]
        CH_COMPRESS[Compression]
        CH_HTTP[HTTP Client]
    end

    BASE --> OTLP
    BASE --> CH

    OTLP --> OTLP_BATCH
    OTLP_BATCH --> OTLP_HTTP
    OTLP_HTTP --> OTLP_RETRY

    CH --> CH_TRANSFORM
    CH_TRANSFORM --> CH_BATCH
    CH_BATCH --> CH_COMPRESS
    CH_COMPRESS --> CH_HTTP
```

#### 3. Privacy Engine

**Data Flow:**

```mermaid
flowchart LR
    INPUT[Raw Attributes]
    DETECT{Contains PII?}
    HASH[Hash Sensitive Data]
    SANITIZE[Remove PII]
    VALIDATE{Valid Data?}
    OUTPUT[Clean Attributes]

    INPUT --> DETECT
    DETECT -->|Yes| HASH
    DETECT -->|No| VALIDATE
    HASH --> SANITIZE
    SANITIZE --> VALIDATE
    VALIDATE -->|Yes| OUTPUT
    VALIDATE -->|No| OUTPUT

    style DETECT fill:#FFB84D
    style HASH fill:#FF6B6B
    style SANITIZE fill:#FF6B6B
    style OUTPUT fill:#51CF66
```

**PII Detection Rules:**

| Data Type | Detection Pattern | Action |
|-----------|------------------|--------|
| Email | `.*@.*\..*` | Hash domain, remove local |
| Phone | `^\+?[\d\s\-\(\)]+$` | Hash or truncate to country code |
| API Key | `(api[_-]?key|token|secret)` in key name | Remove completely |
| IP Address | IPv4/IPv6 patterns | Hash with salt |
| User ID | Configurable patterns | Hash with SHA-256 |
| Message Content | Any `message` or `content` field | Remove if enabled |

---

## Data Flow

### Event Tracking Flow

```mermaid
sequenceDiagram
    autonumber
    participant App as Application
    participant SDK as TelemetryClient
    participant Privacy as PrivacyEngine
    participant Backend as Backend
    participant Queue as BatchQueue
    participant HTTP as HTTPClient
    participant Collector as OTLP Collector

    App->>SDK: track_event("user.login", {user_id: "123"})

    SDK->>SDK: Check if enabled
    alt Disabled
        SDK-->>App: Return silently
    end

    SDK->>Privacy: sanitize_attributes({user_id: "123"})
    Privacy->>Privacy: Detect PII
    Privacy->>Privacy: Hash user_id
    Privacy-->>SDK: {user_id_hash: "a665a45..."}

    SDK->>SDK: Create OTLP span
    SDK->>Backend: send_trace(span_data)

    Backend->>Queue: add_to_batch(span_data)
    Queue->>Queue: Check batch size

    alt Batch Full
        Queue->>HTTP: POST /v1/traces (batch)
        HTTP->>HTTP: Add compression
        HTTP->>Collector: HTTP POST
        Collector-->>HTTP: 200 OK
        HTTP-->>Queue: Success
        Queue->>Queue: Clear batch
    else Batch Not Full
        Queue->>Queue: Queue for later
    end

    Backend-->>SDK: Async completion
    SDK-->>App: Return immediately
```

### Metric Tracking Flow

```mermaid
flowchart TD
    START([track_metric called])
    CHECK_ENABLED{Enabled?}
    CHECK_TYPE{Metric Type?}
    COUNTER[Create Counter]
    GAUGE[Create Gauge]
    HISTOGRAM[Create Histogram]
    SANITIZE[Sanitize Attributes]
    CREATE_OTLP[Create OTLP Metric]
    BATCH[Add to Batch]
    CHECK_BATCH{Batch Full?}
    FLUSH[Flush to Backend]
    QUEUE[Queue Event]
    END([Return])

    START --> CHECK_ENABLED
    CHECK_ENABLED -->|No| END
    CHECK_ENABLED -->|Yes| CHECK_TYPE

    CHECK_TYPE -->|Counter| COUNTER
    CHECK_TYPE -->|Gauge| GAUGE
    CHECK_TYPE -->|Histogram| HISTOGRAM

    COUNTER --> SANITIZE
    GAUGE --> SANITIZE
    HISTOGRAM --> SANITIZE

    SANITIZE --> CREATE_OTLP
    CREATE_OTLP --> BATCH
    BATCH --> CHECK_BATCH

    CHECK_BATCH -->|Yes| FLUSH
    CHECK_BATCH -->|No| QUEUE

    FLUSH --> END
    QUEUE --> END

    style CHECK_ENABLED fill:#FFB84D
    style CHECK_BATCH fill:#FFB84D
    style FLUSH fill:#00D9FF
```

---

## Backend Architectures

### OTLP Backend Architecture

```mermaid
graph TB
    subgraph "SDK (Python/TypeScript)"
        CLIENT[TelemetryClient]
        OTLP_BACKEND[OTLP Backend]
    end

    subgraph "Transport"
        HTTP_CLIENT[HTTP Client]
        COMPRESSION[Gzip Compression]
        RETRY[Retry Logic]
    end

    subgraph "OpenTelemetry Collector"
        RECEIVER[OTLP Receiver<br/>:4318 HTTP<br/>:4317 gRPC]
        PROCESSOR[Batch Processor<br/>Resource Processor]
        EXPORTER[Exporters<br/>Prometheus<br/>ClickHouse<br/>Debug]
    end

    subgraph "Storage"
        PROMETHEUS[(Prometheus)]
        CLICKHOUSE[(ClickHouse)]
    end

    CLIENT --> OTLP_BACKEND
    OTLP_BACKEND --> HTTP_CLIENT
    HTTP_CLIENT --> COMPRESSION
    COMPRESSION --> RETRY
    RETRY -->|OTLP/HTTP| RECEIVER

    RECEIVER --> PROCESSOR
    PROCESSOR --> EXPORTER
    EXPORTER -->|Remote Write| PROMETHEUS
    EXPORTER -->|Native Protocol| CLICKHOUSE

    style OTLP_BACKEND fill:#00D9FF,stroke:#333,stroke-width:2px
    style RECEIVER fill:#FFB84D,stroke:#333,stroke-width:2px
```

**OTLP Backend Features:**

| Feature | Implementation | Benefit |
|---------|---------------|---------|
| **Standard Protocol** | OTLP/HTTP JSON | Industry standard, wide compatibility |
| **Batching** | Configurable batch size | Reduced network overhead |
| **Compression** | Gzip if payload > 1KB | 70-90% bandwidth reduction |
| **Retry Logic** | Exponential backoff (3 attempts) | Resilience to transient failures |
| **Timeout** | 5 seconds default | Prevents hanging requests |
| **Async Sending** | Non-blocking | Zero application latency impact |

### ClickHouse Backend Architecture

```mermaid
graph TB
    subgraph "SDK (Python/TypeScript)"
        CLIENT[TelemetryClient]
        CH_BACKEND[ClickHouse Backend]
        TRANSFORMER[OTLP → ClickHouse<br/>Transformer]
    end

    subgraph "Processing"
        BATCH[Batch Processor<br/>Default: 100 rows]
        COMPRESS[Gzip Compression<br/>>1KB payloads]
        FORMAT[JSONEachRow Formatter]
    end

    subgraph "Transport"
        HTTP[HTTP Client<br/>POST /]
        AUTH[Basic Auth<br/>Optional]
    end

    subgraph "ClickHouse"
        HTTP_API[HTTP API :8123]
        PARSER[JSON Parser]
        TABLE[(traces table)]
    end

    CLIENT --> CH_BACKEND
    CH_BACKEND --> TRANSFORMER

    TRANSFORMER -->|Flatten OTLP| BATCH
    BATCH -->|100 rows| FORMAT
    FORMAT --> COMPRESS
    COMPRESS --> HTTP
    HTTP --> AUTH
    AUTH -->|INSERT INTO| HTTP_API

    HTTP_API --> PARSER
    PARSER --> TABLE

    style CH_BACKEND fill:#00D9FF,stroke:#333,stroke-width:2px
    style TRANSFORMER fill:#51CF66,stroke:#333,stroke-width:2px
    style HTTP_API fill:#FFB84D,stroke:#333,stroke-width:2px
```

**ClickHouse Backend Features:**

| Feature | Implementation | Benefit |
|---------|---------------|---------|
| **Direct Insertion** | No middleware | Simpler architecture, faster |
| **Schema Control** | Custom table schema | Full control over data model |
| **Batching** | 100 rows default | Optimal ClickHouse performance |
| **Compression** | Gzip for large payloads | Reduced network usage |
| **Transformation** | OTLP → Flat rows | ClickHouse-optimized schema |
| **Zero Dependencies** | Pure stdlib | Lightweight, no external deps |

### Backend Comparison: Data Path

```mermaid
graph LR
    subgraph "OTLP Path"
        SDK1[SDK] -->|OTLP JSON| COLLECTOR[Collector]
        COLLECTOR -->|Transform| STORAGE1[Storage]
    end

    subgraph "ClickHouse Path"
        SDK2[SDK] -->|Transform| SDK2
        SDK2 -->|JSONEachRow| STORAGE2[ClickHouse]
    end

    style SDK1 fill:#00D9FF
    style SDK2 fill:#00D9FF
    style COLLECTOR fill:#FFB84D
```

**When to Use Each:**

| Use Case | Recommended Backend | Reasoning |
|----------|-------------------|-----------|
| Production SaaS | OTLP | Managed infrastructure, standard protocol |
| Self-Hosted | ClickHouse | Direct control, better performance |
| Local Development | ClickHouse | Simple setup, instant feedback |
| Multi-Cloud | OTLP | Flexibility to change backends |
| High Volume (>10k events/sec) | ClickHouse | Optimized batching and compression |
| Complex Processing | OTLP | Collector can transform/filter data |

---

## Deployment Models

### Model 1: SaaS (OTLP Backend)

```mermaid
graph TB
    subgraph "Your Infrastructure"
        APP1[Application 1]
        APP2[Application 2]
        APP3[Application 3]
    end

    subgraph "Automagik Cloud"
        LB[Load Balancer<br/>telemetry.namastex.ai]
        COLLECTOR[OTLP Collector<br/>Container 155]
        PROM[(Prometheus<br/>Container 122)]
        CH[(ClickHouse<br/>Container 155)]
        GRAFANA[Grafana<br/>Container 122]
    end

    APP1 -->|HTTPS| LB
    APP2 -->|HTTPS| LB
    APP3 -->|HTTPS| LB

    LB --> COLLECTOR
    COLLECTOR -->|Metrics| PROM
    COLLECTOR -->|Traces| CH

    PROM --> GRAFANA
    CH --> GRAFANA

    style LB fill:#00D9FF
    style COLLECTOR fill:#FFB84D
```

**Configuration:**
```python
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0"
    # Uses default: https://telemetry.namastex.ai
)
```

### Model 2: Self-Hosted (ClickHouse Backend)

```mermaid
graph TB
    subgraph "Your Infrastructure"
        APP[Your Application]
        CH[(ClickHouse)]
        GRAFANA[Grafana]
    end

    APP -->|HTTP API<br/>Direct Insert| CH
    CH -->|SQL Queries| GRAFANA

    style APP fill:#00D9FF
    style CH fill:#FFB84D
```

**Configuration:**
```python
client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    backend="clickhouse",
    clickhouse_endpoint="http://localhost:8123"
)
```

### Model 3: Hybrid (Both Backends)

```mermaid
graph TB
    subgraph "Production"
        PROD_APP[Production App]
        CLOUD[Automagik Cloud<br/>OTLP]
    end

    subgraph "Development"
        DEV_APP[Development App]
        LOCAL_CH[(Local ClickHouse)]
    end

    PROD_APP -->|OTLP Backend| CLOUD
    DEV_APP -->|ClickHouse Backend| LOCAL_CH

    style PROD_APP fill:#00D9FF
    style DEV_APP fill:#00D9FF
```

**Configuration (Environment-Based):**
```python
import os

backend = "clickhouse" if os.getenv("ENVIRONMENT") == "development" else "otlp"

client = AutomagikTelemetry(
    project_name="my-app",
    version="1.0.0",
    backend=backend,
    clickhouse_endpoint="http://localhost:8123" if backend == "clickhouse" else None
)
```

---

## Performance Characteristics

### Latency Analysis

```mermaid
gantt
    title Event Processing Timeline (Single Event)
    dateFormat X
    axisFormat %Lms

    section Application
    track_event call    :0, 1

    section SDK
    Privacy check       :1, 2
    Create OTLP span   :2, 4
    Add to batch       :4, 5
    Return to app      :5, 6

    section Background
    Batch processing   :6, 10
    Compression        :10, 15
    HTTP send          :15, 50

    section Total
    User-facing latency :crit, 0, 6
    Background work    :50, 50
```

**Performance Benchmarks:**

| Operation | Python SDK | TypeScript SDK | Target |
|-----------|-----------|----------------|--------|
| **Event Generation** | 10,000+ events/sec | 8,000+ events/sec | >5,000/sec |
| **track_event() Latency** | <1ms | <1ms | <5ms |
| **Batch Flush (100 events)** | <500ms | <500ms | <1s |
| **Memory Overhead** | <5MB (10k events) | <10MB (5k events) | <20MB |
| **CPU Overhead** | <1% (idle) | <1% (idle) | <5% |
| **Network Compression** | 70-90% reduction | 70-90% reduction | >50% |

### Throughput Analysis

```mermaid
graph LR
    subgraph "Low Volume"
        A[1-100 events/sec] -->|batch_size=1| B[Immediate Send]
    end

    subgraph "Medium Volume"
        C[100-1000 events/sec] -->|batch_size=100| D[Batched Send]
    end

    subgraph "High Volume"
        E[1000+ events/sec] -->|batch_size=1000| F[Compressed Batch]
    end

    style B fill:#51CF66
    style D fill:#FFB84D
    style F fill:#FF6B6B
```

**Recommended Configuration:**

| Throughput | batch_size | flush_interval | Compression | Backend |
|------------|-----------|---------------|------------|---------|
| Low (<100/s) | 1 | 5s | Optional | Either |
| Medium (100-1000/s) | 100 | 5s | Recommended | Either |
| High (1000-5000/s) | 500 | 2s | Required | ClickHouse |
| Very High (>5000/s) | 1000 | 1s | Required | ClickHouse |

---

## Security Architecture

### Data Protection Layers

```mermaid
graph TD
    subgraph "Layer 1: Input Validation"
        INPUT[User Data]
        VALIDATE[Schema Validation]
        REJECT{Valid?}
    end

    subgraph "Layer 2: PII Detection"
        SCAN[PII Scanner]
        DETECT{Contains PII?}
        SANITIZE[Sanitization]
    end

    subgraph "Layer 3: Encryption"
        ENCRYPT{HTTPS?}
        TLS[TLS 1.3 Encryption]
    end

    subgraph "Layer 4: Authentication"
        AUTH{Auth Required?}
        BASIC[Basic Auth]
        TOKEN[Bearer Token]
    end

    subgraph "Layer 5: Storage"
        STORAGE[(Secure Storage)]
    end

    INPUT --> VALIDATE
    VALIDATE --> REJECT
    REJECT -->|No| END1[Reject]
    REJECT -->|Yes| SCAN

    SCAN --> DETECT
    DETECT -->|Yes| SANITIZE
    DETECT -->|No| ENCRYPT
    SANITIZE --> ENCRYPT

    ENCRYPT -->|Yes| TLS
    ENCRYPT -->|No| END2[Reject]

    TLS --> AUTH
    AUTH -->|Yes| BASIC
    AUTH -->|Yes| TOKEN
    AUTH -->|No| STORAGE
    BASIC --> STORAGE
    TOKEN --> STORAGE

    style VALIDATE fill:#FFB84D
    style SANITIZE fill:#FF6B6B
    style TLS fill:#51CF66
```

### Privacy Guarantees

| Data Type | Collection | Processing | Storage | Retention |
|-----------|-----------|-----------|---------|-----------|
| **Events** | ✅ Allowed | Sanitized | Encrypted | 90 days |
| **Metrics** | ✅ Allowed | Sanitized | Encrypted | 90 days |
| **Logs** | ✅ Allowed (opt-in) | Sanitized | Encrypted | 30 days |
| **User IDs** | ✅ Hashed only | SHA-256 | Encrypted | 90 days |
| **IP Addresses** | ❌ Not collected | N/A | N/A | N/A |
| **Email** | ❌ Sanitized out | Removed | N/A | N/A |
| **Phone Numbers** | ❌ Sanitized out | Removed | N/A | N/A |
| **API Keys** | ❌ Never collected | Removed | N/A | N/A |
| **Message Content** | ❌ Never collected | Removed | N/A | N/A |

### Threat Model

```mermaid
graph TD
    subgraph "Threats"
        T1[PII Leakage]
        T2[Man-in-the-Middle]
        T3[Unauthorized Access]
        T4[Data Tampering]
        T5[DoS Attack]
    end

    subgraph "Mitigations"
        M1[Privacy Engine]
        M2[TLS Encryption]
        M3[Authentication]
        M4[Signature Validation]
        M5[Rate Limiting]
    end

    T1 -->|Prevented by| M1
    T2 -->|Prevented by| M2
    T3 -->|Prevented by| M3
    T4 -->|Prevented by| M4
    T5 -->|Prevented by| M5

    style M1 fill:#51CF66
    style M2 fill:#51CF66
    style M3 fill:#51CF66
    style M4 fill:#51CF66
    style M5 fill:#51CF66
```

---

## Related Documentation

- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** - Implementation patterns and code examples
- **[TESTING.md](TESTING.md)** - Testing strategies and CI/CD integration
- **[SDK_DIFFERENCES.md](SDK_DIFFERENCES.md)** - Cross-SDK comparison and migration
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development workflow and standards

---

<p align="center">
  <strong>Built with ❤️ by <a href="https://namastex.ai">Namastex Labs</a></strong><br>
  <em>Privacy-first architecture for modern observability</em>
</p>
