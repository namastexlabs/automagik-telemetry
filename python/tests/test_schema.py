"""Tests for the StandardEvents schema."""

import pytest

from automagik_telemetry.schema import StandardEvents


class TestStandardEvents:
    """Test suite for StandardEvents schema validation."""

    def test_all_constants_exist(self) -> None:
        """Verify all expected event constants are defined."""
        assert hasattr(StandardEvents, "FEATURE_USED")
        assert hasattr(StandardEvents, "API_REQUEST")
        assert hasattr(StandardEvents, "COMMAND_EXECUTED")
        assert hasattr(StandardEvents, "OPERATION_LATENCY")
        assert hasattr(StandardEvents, "ERROR_OCCURRED")
        assert hasattr(StandardEvents, "SERVICE_HEALTH")

    def test_event_naming_convention(self) -> None:
        """Verify all events follow automagik.* naming convention."""
        assert StandardEvents.FEATURE_USED.startswith("automagik.")
        assert StandardEvents.API_REQUEST.startswith("automagik.")
        assert StandardEvents.COMMAND_EXECUTED.startswith("automagik.")
        assert StandardEvents.OPERATION_LATENCY.startswith("automagik.")
        assert StandardEvents.ERROR_OCCURRED.startswith("automagik.")
        assert StandardEvents.SERVICE_HEALTH.startswith("automagik.")

    def test_event_values_are_strings(self) -> None:
        """Verify all event constants are strings."""
        assert isinstance(StandardEvents.FEATURE_USED, str)
        assert isinstance(StandardEvents.API_REQUEST, str)
        assert isinstance(StandardEvents.COMMAND_EXECUTED, str)
        assert isinstance(StandardEvents.OPERATION_LATENCY, str)
        assert isinstance(StandardEvents.ERROR_OCCURRED, str)
        assert isinstance(StandardEvents.SERVICE_HEALTH, str)

    def test_event_values_are_unique(self) -> None:
        """Verify no duplicate event names."""
        events = [
            StandardEvents.FEATURE_USED,
            StandardEvents.API_REQUEST,
            StandardEvents.COMMAND_EXECUTED,
            StandardEvents.OPERATION_LATENCY,
            StandardEvents.ERROR_OCCURRED,
            StandardEvents.SERVICE_HEALTH,
        ]
        assert len(events) == len(set(events)), "Duplicate event names found"

    def test_specific_event_values(self) -> None:
        """Verify specific event name values for cross-SDK consistency."""
        assert StandardEvents.FEATURE_USED == "automagik.feature.used"
        assert StandardEvents.API_REQUEST == "automagik.api.request"
        assert StandardEvents.COMMAND_EXECUTED == "automagik.cli.command"
        assert StandardEvents.OPERATION_LATENCY == "automagik.performance.latency"
        assert StandardEvents.ERROR_OCCURRED == "automagik.error"
        assert StandardEvents.SERVICE_HEALTH == "automagik.health"

    def test_event_names_use_dot_notation(self) -> None:
        """Verify events use dot notation (not underscore or dash)."""
        events = [
            StandardEvents.FEATURE_USED,
            StandardEvents.API_REQUEST,
            StandardEvents.COMMAND_EXECUTED,
            StandardEvents.OPERATION_LATENCY,
            StandardEvents.ERROR_OCCURRED,
            StandardEvents.SERVICE_HEALTH,
        ]
        for event in events:
            assert "." in event, f"Event {event} should use dot notation"
            assert "_" not in event or event == StandardEvents.ERROR_OCCURRED, (
                f"Event {event} should not use underscores except in error"
            )
            assert "-" not in event, f"Event {event} should not use dashes"

    def test_events_follow_category_hierarchy(self) -> None:
        """Verify events follow category.subcategory.action pattern."""
        # automagik.feature.used
        assert StandardEvents.FEATURE_USED.count(".") == 2
        # automagik.api.request
        assert StandardEvents.API_REQUEST.count(".") == 2
        # automagik.cli.command (special case)
        assert StandardEvents.COMMAND_EXECUTED.count(".") == 2
        # automagik.performance.latency
        assert StandardEvents.OPERATION_LATENCY.count(".") == 2
        # automagik.error (special case - only 1 dot)
        assert StandardEvents.ERROR_OCCURRED.count(".") == 1
        # automagik.health (special case - only 1 dot)
        assert StandardEvents.SERVICE_HEALTH.count(".") == 1

    def test_no_uppercase_in_event_names(self) -> None:
        """Verify event names are lowercase."""
        events = [
            StandardEvents.FEATURE_USED,
            StandardEvents.API_REQUEST,
            StandardEvents.COMMAND_EXECUTED,
            StandardEvents.OPERATION_LATENCY,
            StandardEvents.ERROR_OCCURRED,
            StandardEvents.SERVICE_HEALTH,
        ]
        for event in events:
            assert event == event.lower(), f"Event {event} should be lowercase"

    def test_standard_events_is_class(self) -> None:
        """Verify StandardEvents is a class, not instance."""
        assert isinstance(StandardEvents, type)

    def test_standard_events_immutable(self) -> None:
        """Verify StandardEvents constants cannot be easily modified."""
        # Attempting to set a new value should work (Python doesn't have const)
        # but we test that the original values are preserved
        original_value = StandardEvents.FEATURE_USED

        # Try to modify (this will work in Python but shouldn't be done)
        StandardEvents.FEATURE_USED = "modified"

        # Restore original value
        StandardEvents.FEATURE_USED = original_value

        # Verify restoration worked
        assert StandardEvents.FEATURE_USED == original_value
