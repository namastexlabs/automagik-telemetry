"""
Test the colorful opt-in prompt.

Run this to see the first-run experience for Automagik Telemetry.
"""

from automagik_telemetry import TelemetryOptIn, prompt_user_if_needed

# Test the prompt
if __name__ == "__main__":
    print("Testing opt-in prompt...\n")
    
    # Show current status
    if TelemetryOptIn.has_user_decided():
        preference = TelemetryOptIn.get_user_preference()
        print(f"✓ User has already decided: {preference}\n")
        print("To test the prompt again, delete:")
        print("  - ~/.automagik/telemetry_preference")
        print("  - ~/.automagik-no-telemetry\n")
    else:
        print("User hasn't decided yet. Showing prompt...\n")
        
        # Show the prompt
        result = prompt_user_if_needed("Automagik Omni")
        
        print(f"\nResult: Telemetry {'enabled' if result else 'disabled'}")
        print(f"Preference saved to: ~/.automagik/telemetry_preference")
