# Telemetry Implementation Guide

> For maintainers implementing telemetry in Automagik projects

## Quick Start

### 1. Add Dependency

**Python projects** (Omni, Hive, Spark, Genie):
```bash
uv add automagik-telemetry
```

**TypeScript projects** (Forge, Tools):
```bash
pnpm add @automagik/telemetry
```

### 2. Initialize in Your Project

**Python:**
```python
from automagik_telemetry import AutomagikTelemetry

# Initialize once at application startup
telemetry = AutomagikTelemetry(
    project_name="omni",  # or "hive", "forge", etc.
    version="1.0.0"
)
```

**TypeScript:**
```typescript
import { AutomagikTelemetry } from '@automagik/telemetry';

const telemetry = new AutomagikTelemetry({
  projectName: 'forge',
  version: '1.0.0'
});
```

### 3. Track Events

```python
# Feature usage
telemetry.track_event(StandardEvents.FEATURE_USED, {
    "feature_name": "list_contacts",
    "feature_category": "api_endpoint"
})

# Errors
telemetry.track_error(error, {
    "error_code": "OMNI-1001",
    "operation": "message_send"
})

# Performance
telemetry.track_metric(StandardEvents.OPERATION_LATENCY, {
    "operation_type": "api_request",
    "duration_ms": 123
})
```

## What to Track (Per Project)

### Core Events (All Projects)

- [ ] **Feature usage** - Commands, API endpoints, major features
- [ ] **Error rates** - By type, with error codes
- [ ] **Performance metrics** - Latency (p50/p95/p99)
- [ ] **Health checks** - Service availability

### Project-Specific Events

#### Omni
- Message sent/received (per channel: WhatsApp, Discord, Slack)
- Instance creation/deletion
- Channel-specific errors (Evolution API, Discord bot)
- Contact/chat operations

#### Hive
- Agent spawned/terminated
- Multi-agent workflow execution
- Knowledge base queries
- Tool usage per agent

#### Forge
- Task orchestration events
- Worker execution status
- Workflow completion/failures
- Resource utilization

#### Genie
- Wish creation/completion
- Agent delegation events
- Decision point tracking

#### Spark
- Cron job execution
- Schedule changes
- Job failures/retries

#### Tools
- MCP tool usage
- Tool installation/activation
- Integration usage patterns

## Privacy Requirements

### ✅ ALWAYS Anonymize

- **User IDs** → Hash with SHA-256
- **Phone numbers** → Hash or truncate to country code
- **Email addresses** → Hash domain, remove local part
- **API keys** → NEVER log
- **Message content** → NEVER log
- **File paths** → Remove home directory prefix

### ✅ SAFE to Collect

- Feature names
- Error codes and categories
- Performance metrics (duration, latency)
- Counts and aggregates
- System info (OS, Python/Node version)
- Project version

### Example: Privacy Sanitization

```python
def sanitize_phone(phone: str) -> str:
    """Hash phone number for privacy"""
    import hashlib
    return hashlib.sha256(phone.encode()).hexdigest()[:16]

# Usage
telemetry.track_event(StandardEvents.FEATURE_USED, {
    "feature_name": "send_message",
    "recipient_hash": sanitize_phone("+1234567890"),  # Not the actual phone!
    "channel": "whatsapp"
})
```

## Configuration Template

Every project should include this in `.env.example`:

```bash
# Telemetry (opt-in, disabled by default)
AUTOMAGIK_TELEMETRY_ENABLED=false
AUTOMAGIK_TELEMETRY_ENDPOINT=https://telemetry.namastex.ai

# Self-hosted option
# AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318
```

## Testing Your Implementation

### 1. Enable Verbose Mode

```bash
AUTOMAGIK_TELEMETRY_VERBOSE=true AUTOMAGIK_TELEMETRY_ENABLED=true your-command
```

This prints all telemetry events to console for inspection.

### 2. Validate No PII

Check output for:
- Phone numbers
- Email addresses  
- API keys
- Message content
- User names

### 3. Check Dashboards

Visit https://telemetry.namastex.ai after 5 minutes to see your events.

## PR Review Checklist

Before merging telemetry implementation:

- [ ] Telemetry disabled by default (`AUTOMAGIK_TELEMETRY_ENABLED=false`)
- [ ] Opt-in prompt on first run
- [ ] No PII in telemetry data (verified with verbose mode)
- [ ] All standard events implemented
- [ ] Project-specific events documented
- [ ] Tests don't send telemetry (auto-disabled in CI)
- [ ] Updated `docs/telemetry.md` with project specifics
- [ ] Added to `.env.example`

## Common Patterns

### Tracking API Endpoints

```python
@router.get("/contacts")
async def list_contacts(instance: str):
    start_time = time.time()
    
    try:
        result = await get_contacts(instance)
        
        telemetry.track_event(StandardEvents.API_REQUEST, {
            "endpoint": "/contacts",
            "method": "GET",
            "status": 200
        })
        
        telemetry.track_metric(StandardEvents.OPERATION_LATENCY, {
            "operation_type": "api.list_contacts",
            "duration_ms": (time.time() - start_time) * 1000
        })
        
        return result
        
    except Exception as e:
        telemetry.track_error(e, {
            "endpoint": "/contacts",
            "error_code": get_error_code(e)
        })
        raise
```

### Tracking CLI Commands

```python
@click.command()
def instance_create(name: str):
    telemetry.track_event(StandardEvents.COMMAND_EXECUTED, {
        "command": "instance",
        "subcommand": "create"
    })
    
    # ... implementation
```

### Tracking Feature Usage

```python
def send_message(channel: str, recipient: str, message: str):
    telemetry.track_event(StandardEvents.FEATURE_USED, {
        "feature_name": "send_message",
        "feature_category": "messaging",
        "channel": channel
    })
    
    # ... implementation
```

## FAQ

**Q: Does telemetry slow down my application?**  
A: No. Events are sent asynchronously and add <1ms overhead.

**Q: What if users disable telemetry?**  
A: Respect their choice. All tracking methods become no-ops when disabled.

**Q: Can I test telemetry locally?**  
A: Yes! Use `AUTOMAGIK_TELEMETRY_VERBOSE=true` to see events in console.

**Q: How do I handle sensitive data?**  
A: Use the privacy utilities in `automagik_telemetry.privacy` module (coming in #1).

## Need Help?

- **Documentation**: https://docs.automagik.ai/telemetry
- **Issues**: https://github.com/namastexlabs/automagik-telemetry/issues
- **Discussions**: https://github.com/namastexlabs/automagik-telemetry/discussions
