"""
Automagik Telemetry SDK

Privacy-first, opt-in telemetry for the Automagik ecosystem.
"""

from automagik_telemetry.client import TelemetryClient
from automagik_telemetry.schema import StandardEvents

__version__ = "0.1.0"
__all__ = ["TelemetryClient", "StandardEvents"]
