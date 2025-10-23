# Privacy Policy

**Effective Date:** October 21, 2025  
**Last Updated:** October 21, 2025

## Overview

Automagik Telemetry is designed with **privacy-first principles**. We only collect anonymous, aggregated data to improve our open-source projects. This document explains exactly what we collect, why, and how you control it.

## Your Control

### Opt-In by Default

Telemetry is **disabled by default**. You must explicitly enable it:

```bash
# First run prompts you
Help Improve Automagik! Enable telemetry? [y/N]: 

# Or set environment variable
export AUTOMAGIK_TELEMETRY_ENABLED=true
```

### Easy Opt-Out

Disable telemetry anytime:

```bash
# Globally
export AUTOMAGIK_TELEMETRY_ENABLED=false

# Per-command
AUTOMAGIK_TELEMETRY_ENABLED=false omni instance list

# Permanent opt-out
touch ~/.automagik-no-telemetry
```

### Auto-Disabled

Telemetry is automatically disabled in:
- CI environments (GitHub Actions, GitLab CI, etc.)
- Development mode (`ENVIRONMENT=dev`)
- Test environments

## What We Collect

### ✅ We DO Collect

**Feature Usage** (anonymous counts):
- Which commands you run (`omni instance create`)
- Which API endpoints you use (`GET /contacts`)
- Which features you enable

**Performance Metrics** (aggregated):
- Command execution time
- API response latency
- Error rates

**Error Information** (anonymous):
- Error codes (`OMNI-1001`)
- Error categories (authentication, messaging, database)
- Stack traces (with PII removed)

**System Information**:
- Operating system (Linux, macOS, Windows)
- Python/Node.js version
- Automagik project version

**Example Event:**
```json
{
  "event": "automagik.feature.used",
  "project": "omni",
  "feature_name": "list_contacts",
  "os": "Linux",
  "timestamp": "2025-10-21T12:00:00Z",
  "anonymous_user_id": "abc123...def"
}
```

### ❌ We DO NOT Collect

We **NEVER** collect:

- **Message content** - Your conversations are private
- **Phone numbers** - Not collected or always hashed
- **Email addresses** - Not collected or always hashed
- **API keys or credentials** - Never logged
- **File contents** - Your code/data stays private
- **User identities** - Everything is anonymized
- **IP addresses** - Not stored or tracked
- **Location data** - Not collected
- **Personal information** - No PII ever

## How We Use Data

### Improving Automagik

- Identify which features are most valuable
- Discover pain points and bugs users encounter
- Optimize performance based on real usage
- Prioritize development based on actual needs

### What We DON'T Do

- ❌ Sell your data (we don't collect personal data to sell)
- ❌ Share with third parties (except infrastructure providers)
- ❌ Track individuals (all data is anonymous)
- ❌ Build user profiles (impossible with anonymous data)

## Data Storage & Security

### Infrastructure

- **Storage:** Telemetry data sent to `telemetry.namastex.ai`
- **Retention:** 30 days for detailed logs, 1 year for aggregates
- **Encryption:** TLS in transit, encrypted at rest
- **Access:** Limited to core maintainers only

### Self-Hosting

You can run your own telemetry infrastructure:

```bash
# Point to your server instead
export AUTOMAGIK_TELEMETRY_ENDPOINT=http://your-server:4318
```

See [Self-Hosting Guide](../infra/README.md) for details.

## Transparency

### Open Source

- Telemetry SDK is open-source: https://github.com/namastexlabs/automagik-telemetry
- Audit the code yourself
- See exactly what's sent with `--telemetry-verbose` flag

### Verbose Mode

See exactly what's being sent:

```bash
AUTOMAGIK_TELEMETRY_VERBOSE=true omni instance list

# Output shows:
[Telemetry] Sending event: automagik.feature.used
{
  "project": "omni",
  "feature_name": "list_instances",
  "anonymous_user_id": "abc123..."
}
```

## Data Subject Rights

Under GDPR and similar regulations, you have the right to:

### Access Your Data

Since all data is anonymous, we cannot identify "your" data. Use `--telemetry-verbose` to see what's sent in real-time.

### Delete Your Data

```bash
# Stop sending data
export AUTOMAGIK_TELEMETRY_ENABLED=false
touch ~/.automagik-no-telemetry
```

Existing anonymous data remains in aggregates but cannot be tied to you.

### Portability

All telemetry data is sent in OpenTelemetry standard format (OTLP). You can:
- Self-host and keep all data
- Export from your own infrastructure

## Children's Privacy

Automagik products are not directed at children under 13. We do not knowingly collect data from children.

## International Users

Data may be processed in:
- United States (primary infrastructure)
- European Union (if self-hosting)

By enabling telemetry, you consent to this data transfer.

## Changes to This Policy

We may update this privacy policy. Changes will be:
- Posted on this page
- Announced in project releases
- Effective 30 days after posting

Continued use after changes means acceptance.

## Contact Us

**Privacy Questions:**  
privacy@namastex.ai

**General Support:**  
https://github.com/namastexlabs/automagik-telemetry/discussions

**Data Protection Officer:**  
dpo@namastex.ai

## Compliance

This policy complies with:
- **GDPR** (General Data Protection Regulation)
- **CCPA** (California Consumer Privacy Act)
- **Open Source Privacy Best Practices**

## Summary (TL;DR)

- ✅ **Opt-in by default** - You choose to share
- ✅ **Anonymous data only** - No personal info ever
- ✅ **Transparent** - See exactly what's sent
- ✅ **Self-hostable** - Run your own infrastructure
- ✅ **Open source** - Audit the code yourself
- ✅ **Easy opt-out** - One env variable to disable

We respect your privacy. Telemetry helps us build better open-source tools for everyone.
