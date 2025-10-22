# Quick Start Guide

Get up and running with Automagik Telemetry in 5 minutes.

## Installation

### Python
```bash
uv add automagik-telemetry
# or
pip install automagik-telemetry
```

### TypeScript
```bash
pnpm add @automagik/telemetry
# or
npm install @automagik/telemetry
```

## Minimal Example

### Python

```python
from automagik_telemetry import TelemetryClient, StandardEvents

# 1. Initialize (once at startup)
telemetry = TelemetryClient(
    project_name="your-project",  # omni, hive, forge, etc.
    version="1.0.0"
)

# 2. Track events
telemetry.track_event(StandardEvents.FEATURE_USED, {
    "feature_name": "awesome_feature"
})
```

### TypeScript

```typescript
import { TelemetryClient, StandardEvents } from '@automagik/telemetry';

// 1. Initialize
const telemetry = new TelemetryClient({
  projectName: 'your-project',
  version: '1.0.0'
});

// 2. Track events
telemetry.trackEvent(StandardEvents.FEATURE_USED, {
  feature_name: 'awesome_feature'
});
```

## Configuration

### Enable Telemetry

```bash
# In .env or export
export AUTOMAGIK_TELEMETRY_ENABLED=true
```

### Test with Verbose Mode

```bash
# See exactly what's being sent
export AUTOMAGIK_TELEMETRY_VERBOSE=true
export AUTOMAGIK_TELEMETRY_ENABLED=true

python your_script.py
```

Output:
```
[Telemetry] Sending event: automagik.feature.used
  Project: your-project
  Data: {
    "feature_name": "awesome_feature"
  }
  Endpoint: https://telemetry.namastex.ai/v1/traces
```

### Self-Host (Optional)

```bash
# Point to your own OpenTelemetry collector
export AUTOMAGIK_TELEMETRY_ENDPOINT=http://localhost:4318/v1/traces
```

See [Self-Hosting Guide](docs/SELF_HOSTING.md) for full setup.

## Common Patterns

### Track API Requests

```python
import time

def api_handler():
    start = time.time()
    
    try:
        result = do_work()
        
        telemetry.track_event(StandardEvents.API_REQUEST, {
            "endpoint": "/api/v1/users",
            "method": "GET",
            "status": 200,
            "duration_ms": (time.time() - start) * 1000
        })
        
        return result
    except Exception as e:
        telemetry.track_error(e, {
            "error_code": "API-5001",
            "endpoint": "/api/v1/users"
        })
        raise
```

### Track CLI Commands

```python
@click.command()
def deploy(environment: str):
    telemetry.track_event(StandardEvents.COMMAND_EXECUTED, {
        "command": "deploy",
        "subcommand": environment
    })
    
    # Your deploy logic
    pass
```

### Track Performance

```python
telemetry.track_metric(StandardEvents.OPERATION_LATENCY, {
    "operation_type": "database_query",
    "duration_ms": 45.2
})
```

## Privacy by Default

### What's Collected ✅

- Feature usage counts
- Error types (no sensitive data)
- Performance metrics
- System info (OS, Python version)

### What's NOT Collected ❌

- User credentials
- Message content
- Phone numbers/emails
- Personal data

### User Control

```python
# Check status
status = telemetry.get_status()
print(f"Enabled: {status['enabled']}")

# Disable permanently
telemetry.disable()  # Creates ~/.automagik-no-telemetry

# Re-enable
telemetry.enable()   # Removes opt-out file
```

## Testing Your Integration

1. **Enable verbose mode:**
   ```bash
   AUTOMAGIK_TELEMETRY_VERBOSE=true \
   AUTOMAGIK_TELEMETRY_ENABLED=true \
   python your_script.py
   ```

2. **Verify no PII in output** - Check console output for:
   - Phone numbers
   - Emails
   - API keys
   - Message content

3. **Check your OpenTelemetry collector** - Events should appear within seconds

4. **Test opt-out:**
   ```bash
   touch ~/.automagik-no-telemetry
   python your_script.py  # No events sent
   ```

## Next Steps

- **See real examples:** [examples/python/omni_example.py](examples/python/omni_example.py)
- **Implementation guide:** [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)
- **Privacy policy:** [docs/PRIVACY_POLICY.md](docs/PRIVACY_POLICY.md)
- **Self-hosting:** [docs/SELF_HOSTING.md](docs/SELF_HOSTING.md)

## Need Help?

- **Issues:** https://github.com/namastexlabs/automagik-telemetry/issues
- **Discussions:** https://github.com/namastexlabs/automagik-telemetry/discussions
- **Discord:** https://discord.gg/xcW8c7fF3R
