"""
Automagik Telemetry SDK

Privacy-first, opt-in telemetry for the Automagik ecosystem.
"""

from automagik_telemetry.client import TelemetryClient
from automagik_telemetry.opt_in import (
    TelemetryOptIn,
    prompt_user_if_needed,
    should_prompt_user,
)
from automagik_telemetry.schema import StandardEvents

__version__ = "0.1.0"
__all__ = [
    "TelemetryClient",
    "StandardEvents",
    "TelemetryOptIn",
    "prompt_user_if_needed",
    "should_prompt_user",
]
