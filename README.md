# Automagik Telemetry

> Privacy-first, opt-in telemetry SDK for the Automagik ecosystem

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)

## 🎯 Purpose

This repository provides **standardized, privacy-first telemetry SDKs** for all Automagik projects (Omni, Hive, Forge, Tools, Genie, Spark). It enables data-driven development while respecting user privacy and maintaining open-source transparency.

## 📦 SDKs

### Python SDK (`automagik-telemetry`)
For Python projects: Omni, Hive, Spark, Genie

```bash
# Install via uv
uv add automagik-telemetry

# Install via pip
pip install automagik-telemetry
```

### TypeScript SDK (`@automagik/telemetry`)
For Node.js projects: Forge, Tools

```bash
# Install via pnpm
pnpm add @automagik/telemetry

# Install via npm
npm install @automagik/telemetry
```

## 🚀 Quick Start

### Python

```python
from automagik_telemetry import TelemetryClient, StandardEvents

# Initialize once at startup (disabled by default)
telemetry = TelemetryClient(
    project_name="omni",
    version="1.0.0"
)

# Track feature usage
telemetry.track_event(StandardEvents.FEATURE_USED, {
    "feature_name": "list_contacts",
    "feature_category": "api_endpoint"
})

# Track errors with context
telemetry.track_error(error, {
    "error_code": "OMNI-1001",
    "operation": "message_send"
})

# Track performance
telemetry.track_metric(StandardEvents.OPERATION_LATENCY, {
    "operation_type": "api_request",
    "duration_ms": 123
})
```

### TypeScript

```typescript
import { TelemetryClient, StandardEvents } from '@automagik/telemetry';

// Initialize
const telemetry = new TelemetryClient({
  projectName: 'forge',
  version: '1.0.0'
});

// Track events
telemetry.trackEvent(StandardEvents.FEATURE_USED, {
  feature_name: 'workflow_execution',
  feature_category: 'orchestration'
});

// Track errors
telemetry.trackError(error, {
  error_code: 'FORGE-2001',
  context: 'task_execution'
});
```

## 🔒 Privacy & Control

### Privacy-First Design

- **Disabled by default** - Users must explicitly opt-in
- **No PII collected** - Phone numbers, emails, messages are never sent
- **Anonymous by default** - User IDs are hashed
- **Transparent** - `--telemetry-verbose` flag shows exactly what's sent
- **Self-hostable** - Run your own telemetry infrastructure

### What We Collect

✅ **Safe to collect:**
- Feature usage (which commands/APIs are used)
- Error rates (anonymous error codes and categories)
- Performance metrics (latency, response times)
- System info (OS, Python/Node version)
- Aggregated counts

❌ **Never collected:**
- Message content
- User credentials or API keys
- Phone numbers or email addresses (unless hashed)
- File contents or business logic
- Personal identifiable information (PII)

### User Control

**Opt-in prompt on first run:**
```
Help Improve Automagik! 🚀

Enable anonymous telemetry to help us improve? [y/N]: _
```

**Disable globally:**
```bash
export AUTOMAGIK_TELEMETRY_ENABLED=false
```

**Disable per-command:**
```bash
AUTOMAGIK_TELEMETRY_ENABLED=false omni instance list
```

**Create permanent opt-out:**
```bash
touch ~/.automagik-no-telemetry
```

**Auto-disabled in:**
- CI environments (GitHub Actions, GitLab CI, etc.)
- Development mode (`ENVIRONMENT=dev`)
- Test environments

## 🏗️ Repository Structure

```
automagik-telemetry/
├── python/              # Python SDK
│   ├── src/
│   │   └── automagik_telemetry/
│   │       ├── __init__.py
│   │       ├── client.py
│   │       ├── config.py
│   │       ├── opt_in.py
│   │       ├── privacy.py
│   │       └── schema.py
│   ├── tests/
│   ├── pyproject.toml
│   └── README.md
│
├── typescript/          # TypeScript SDK
│   ├── src/
│   │   ├── client.ts
│   │   ├── config.ts
│   │   ├── opt-in.ts
│   │   ├── privacy.ts
│   │   └── schema.ts
│   ├── tests/
│   ├── package.json
│   └── README.md
│
├── docs/
│   ├── IMPLEMENTATION_GUIDE.md    # For maintainers
│   ├── SELF_HOSTING.md            # For users
│   ├── PRIVACY_POLICY.md          # Legal/transparency
│   ├── EVENT_SCHEMA.md            # Standard events reference
│   └── FAQ.md
│
├── examples/
│   ├── python/
│   │   ├── omni_example.py
│   │   ├── hive_example.py
│   │   └── spark_example.py
│   └── typescript/
│       ├── forge_example.ts
│       └── tools_example.ts
│
├── dashboards/          # Grafana dashboard templates
│   ├── overview.json
│   ├── errors.json
│   └── performance.json
│
├── infra/               # Self-hosting configs
│   ├── docker-compose.yml
│   ├── otel-config.yaml
│   └── prometheus.yml
│
└── README.md
```

## 📚 Documentation

- **[Implementation Guide](docs/IMPLEMENTATION_GUIDE.md)** - For maintainers adding telemetry to Automagik projects
- **[Self-Hosting Guide](docs/SELF_HOSTING.md)** - Run your own telemetry infrastructure
- **[Privacy Policy](docs/PRIVACY_POLICY.md)** - What we collect and why
- **[Event Schema](docs/EVENT_SCHEMA.md)** - Standardized events reference
- **[FAQ](docs/FAQ.md)** - Common questions

## 🛠️ Development

### Python SDK

```bash
cd python
uv sync
uv run pytest
uv run ruff check src tests
uv run mypy src
```

### TypeScript SDK

```bash
cd typescript
pnpm install
pnpm test
pnpm lint
pnpm build
```

## 🌐 Self-Hosting

Don't want to send data to `telemetry.namastex.ai`? No problem!

```bash
# Clone this repo
git clone https://github.com/namastexlabs/automagik-telemetry
cd automagik-telemetry/infra

# Start your own telemetry stack
docker-compose up -d

# Point your tools to your server
export AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318
```

See [Self-Hosting Guide](docs/SELF_HOSTING.md) for details.

## 📊 Dashboards

Pre-built Grafana dashboards available in [`dashboards/`](dashboards/):

- **Overview Dashboard** - System health, message volume, error rates
- **Error Dashboard** - Error breakdown by type, timeline, trends
- **Performance Dashboard** - Latency p50/p95/p99, slow operations

Import into your Grafana instance or view at https://telemetry.namastex.ai

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Areas where we need help:**
- [ ] Python SDK implementation (#1)
- [ ] TypeScript SDK implementation (#1)
- [ ] Additional privacy sanitization patterns
- [ ] Dashboard improvements
- [ ] Documentation translations

## 📜 License

MIT License - See [LICENSE](LICENSE) for details.

## 🔗 Related Projects

- [automagik-omni](https://github.com/namastexlabs/automagik-omni) - Multi-tenant messaging hub
- [automagik-hive](https://github.com/namastexlabs/automagik-hive) - Multi-agent orchestration
- [automagik-forge](https://github.com/namastexlabs/automagik-forge) - Task orchestration engine
- [automagik-roadmap](https://github.com/namastexlabs/automagik-roadmap) - Strategic roadmap

## 📞 Support

- **Documentation:** https://docs.automagik.ai
- **Issues:** https://github.com/namastexlabs/automagik-telemetry/issues
- **Discussions:** https://github.com/namastexlabs/automagik-telemetry/discussions
- **Privacy Questions:** privacy@namastex.ai

---

Made with ❤️ by the Automagik community
