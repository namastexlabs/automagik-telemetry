"""
Example: Using automagik-telemetry in Automagik Omni

This shows real-world usage based on the actual Omni implementation.
"""

from automagik_telemetry import AutomagikTelemetry, StandardEvents

# Initialize telemetry client once at app startup
telemetry = AutomagikTelemetry(
    project_name="automagik-omni",
    version="0.2.0"
)

# === Example 1: Track API Requests ===
def list_contacts_endpoint():
    """API endpoint handler example"""
    import time
    start_time = time.time()
    
    try:
        # Your business logic here
        contacts = fetch_contacts_from_db()
        
        # Track successful API request
        telemetry.track_event(StandardEvents.API_REQUEST, {
            "endpoint": "/api/v1/contacts",
            "method": "GET",
            "status": 200,
            "duration_ms": (time.time() - start_time) * 1000
        })
        
        return contacts
        
    except Exception as e:
        # Track error
        telemetry.track_error(e, {
            "error_code": "OMNI-1001",
            "endpoint": "/api/v1/contacts",
            "operation": "list_contacts"
        })
        raise


# === Example 2: Track Feature Usage ===
def send_whatsapp_message(phone: str, message: str):
    """Track feature usage"""
    telemetry.track_event(StandardEvents.FEATURE_USED, {
        "feature_name": "send_message",
        "feature_category": "messaging",
        "channel": "whatsapp"
        # Note: phone number is NOT included (privacy!)
    })
    
    # Your implementation here
    pass


# === Example 3: Track CLI Commands ===
def cli_instance_create(name: str):
    """CLI command handler"""
    telemetry.track_event(StandardEvents.COMMAND_EXECUTED, {
        "command": "instance",
        "subcommand": "create"
    })
    
    # Your implementation
    create_instance(name)


# === Example 4: Track Performance Metrics ===
def process_webhook(channel: str, data: dict):
    """Track performance of webhook processing"""
    import time
    start_time = time.time()
    
    try:
        # Process webhook
        result = handle_webhook(channel, data)
        
        # Track performance
        telemetry.track_metric(StandardEvents.OPERATION_LATENCY, {
            "operation_type": "webhook_processing",
            "channel": channel,
            "duration_ms": (time.time() - start_time) * 1000
        })
        
        return result
        
    except Exception as e:
        telemetry.track_error(e, {
            "error_code": "OMNI-2001",
            "operation": "webhook_processing",
            "channel": channel
        })
        raise


# === Example 5: Check Telemetry Status ===
def show_telemetry_status():
    """CLI command to show telemetry status"""
    status = telemetry.get_status()
    
    print(f"Telemetry Status:")
    print(f"  Enabled: {status['enabled']}")
    print(f"  User ID: {status['user_id']}")
    print(f"  Session ID: {status['session_id']}")
    print(f"  Endpoint: {status['endpoint']}")
    print(f"  Verbose: {status['verbose']}")


# === Example 6: Opt-In/Opt-Out ===
def disable_telemetry_command():
    """CLI command to disable telemetry"""
    telemetry.disable()
    print("✅ Telemetry disabled. Created ~/.automagik-no-telemetry")
    print("   No data will be collected.")


def enable_telemetry_command():
    """CLI command to enable telemetry"""
    telemetry.enable()
    print("✅ Telemetry enabled. Removed ~/.automagik-no-telemetry")
    print("   Anonymous usage data will help improve Automagik!")


# === Dummy functions for example ===
def fetch_contacts_from_db():
    return [{"name": "Contact 1"}, {"name": "Contact 2"}]

def create_instance(name: str):
    print(f"Creating instance: {name}")

def handle_webhook(channel: str, data: dict):
    return {"status": "processed"}


if __name__ == "__main__":
    # Test verbose mode
    import os
    os.environ["AUTOMAGIK_TELEMETRY_VERBOSE"] = "true"
    os.environ["AUTOMAGIK_TELEMETRY_ENABLED"] = "true"

    # Send a test event
    telemetry_test = AutomagikTelemetry("omni", "0.2.0")
    telemetry_test.track_event(StandardEvents.FEATURE_USED, {
        "feature_name": "test_example",
        "feature_category": "example"
    })

    print("\n✅ If telemetry is enabled, you should see the event above!")
    print("   Check your OTel collector logs to verify it was received.\n")
