"""
Unit tests to cover specific edge cases for 100% coverage.

This test file targets the following uncovered lines:
1. src/automagik_telemetry/__init__.py:49-51 - Exception handler for version fallback
2. src/automagik_telemetry/client.py:320 - ENVIRONMENT variable check
3. src/automagik_telemetry/client.py:468-469 - Exception handler for version fallback

These tests use mocking to simulate exception conditions and edge cases that are
difficult to trigger in normal testing scenarios.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

from automagik_telemetry import TelemetryConfig


class TestVersionFallbackInInit(unittest.TestCase):
    """Test version fallback in __init__.py when importlib.metadata fails."""

    def test_version_fallback_when_importlib_metadata_fails(self):
        """
        Test __init__.py:49-51 - Exception handler for version fallback.

        This test simulates the scenario where importlib.metadata.version()
        raises an exception (e.g., package not properly installed or in development mode).
        The fallback should set __version__ to "0.0.0-dev".
        """
        # We need to reload the module with a mocked importlib.metadata
        # First, remove the module from sys.modules to force a reload
        if "automagik_telemetry" in sys.modules:
            # Store reference to original module
            original_module = sys.modules["automagik_telemetry"]
            del sys.modules["automagik_telemetry"]

        try:
            # Mock importlib.metadata.version to raise an exception
            with patch("importlib.metadata.version", side_effect=Exception("Package not found")):
                # Import the module - this will trigger the exception and fallback
                import automagik_telemetry

                # Verify that the fallback version was used
                self.assertEqual(automagik_telemetry.__version__, "0.0.0-dev")

        finally:
            # Clean up: restore original module or remove the test import
            if "automagik_telemetry" in sys.modules:
                del sys.modules["automagik_telemetry"]
            # Restore original if it existed
            if "original_module" in locals():
                sys.modules["automagik_telemetry"] = original_module

    def test_version_fallback_with_module_not_found_error(self):
        """
        Test __init__.py:49-51 - Exception handler with ModuleNotFoundError.

        This specifically tests the case where the package metadata cannot be found,
        which is common in editable installs or development environments.
        """
        if "automagik_telemetry" in sys.modules:
            original_module = sys.modules["automagik_telemetry"]
            del sys.modules["automagik_telemetry"]

        try:
            # Mock importlib.metadata.version to raise ModuleNotFoundError
            with patch(
                "importlib.metadata.version",
                side_effect=ModuleNotFoundError("No module named 'automagik_telemetry'"),
            ):
                import automagik_telemetry

                # Verify fallback version
                self.assertEqual(automagik_telemetry.__version__, "0.0.0-dev")

        finally:
            if "automagik_telemetry" in sys.modules:
                del sys.modules["automagik_telemetry"]
            if "original_module" in locals():
                sys.modules["automagik_telemetry"] = original_module


class TestEnvironmentVariableCheck(unittest.TestCase):
    """Test ENVIRONMENT variable check in client.py."""

    @patch.dict(os.environ, {"HOME": tempfile.mkdtemp()})
    def test_environment_development_disables_telemetry(self):
        """
        Test client.py:320 - ENVIRONMENT variable check for 'development'.

        This tests the branch where ENVIRONMENT="development" causes
        telemetry to be disabled.
        """
        with patch.dict(
            os.environ,
            {"ENVIRONMENT": "development"},
            clear=False,
        ):
            from automagik_telemetry import AutomagikTelemetry

            config = TelemetryConfig(
                project_name="test",
                version="1.0.0",
                batch_size=1,
            )
            client = AutomagikTelemetry(config=config)

            # Telemetry should be disabled due to ENVIRONMENT=development
            self.assertFalse(client.enabled)
            self.assertFalse(client.is_enabled())

    @patch.dict(os.environ, {"HOME": tempfile.mkdtemp()})
    def test_environment_dev_disables_telemetry(self):
        """
        Test client.py:320 - ENVIRONMENT variable check for 'dev'.

        This tests the branch where ENVIRONMENT="dev" causes
        telemetry to be disabled.
        """
        with patch.dict(
            os.environ,
            {"ENVIRONMENT": "dev"},
            clear=False,
        ):
            from automagik_telemetry import AutomagikTelemetry

            config = TelemetryConfig(
                project_name="test",
                version="1.0.0",
                batch_size=1,
            )
            client = AutomagikTelemetry(config=config)

            # Telemetry should be disabled due to ENVIRONMENT=dev
            self.assertFalse(client.enabled)

    @patch.dict(os.environ, {"HOME": tempfile.mkdtemp()})
    def test_environment_test_disables_telemetry(self):
        """
        Test client.py:320 - ENVIRONMENT variable check for 'test'.

        This tests the branch where ENVIRONMENT="test" causes
        telemetry to be disabled.
        """
        with patch.dict(
            os.environ,
            {"ENVIRONMENT": "test"},
            clear=False,
        ):
            from automagik_telemetry import AutomagikTelemetry

            config = TelemetryConfig(
                project_name="test",
                version="1.0.0",
                batch_size=1,
            )
            client = AutomagikTelemetry(config=config)

            # Telemetry should be disabled due to ENVIRONMENT=test
            self.assertFalse(client.enabled)

    @patch.dict(os.environ, {"HOME": tempfile.mkdtemp()})
    def test_environment_testing_disables_telemetry(self):
        """
        Test client.py:320 - ENVIRONMENT variable check for 'testing'.

        This tests the branch where ENVIRONMENT="testing" causes
        telemetry to be disabled.
        """
        with patch.dict(
            os.environ,
            {"ENVIRONMENT": "testing"},
            clear=False,
        ):
            from automagik_telemetry import AutomagikTelemetry

            config = TelemetryConfig(
                project_name="test",
                version="1.0.0",
                batch_size=1,
            )
            client = AutomagikTelemetry(config=config)

            # Telemetry should be disabled due to ENVIRONMENT=testing
            self.assertFalse(client.enabled)


class TestGetVersionFallback(unittest.TestCase):
    """Test _get_sdk_version fallback in client.py."""

    @patch.dict(os.environ, {"HOME": tempfile.mkdtemp()})
    def test_get_version_fallback_when_importlib_fails(self):
        """
        Test client.py:468-469 - Exception handler in _get_sdk_version.

        This tests the fallback behavior when importlib.metadata.version()
        fails within the _get_sdk_version method. The method should catch
        the exception and return "0.0.0-dev" as the fallback version.
        """
        from automagik_telemetry import AutomagikTelemetry

        with patch.dict(
            os.environ,
            {"AUTOMAGIK_TELEMETRY_ENABLED": "true"},
            clear=False,
        ):
            config = TelemetryConfig(
                project_name="test",
                version="1.0.0",
                batch_size=1,
            )
            client = AutomagikTelemetry(config=config)

            # Mock importlib.metadata.version to raise an exception
            # when _get_sdk_version is called
            with patch("importlib.metadata.version", side_effect=Exception("Metadata error")):
                version = client._get_sdk_version()

                # Verify fallback version is returned
                self.assertEqual(version, "0.0.0-dev")

    @patch.dict(os.environ, {"HOME": tempfile.mkdtemp()})
    def test_get_version_fallback_with_package_not_found_error(self):
        """
        Test client.py:468-469 - Exception handler with PackageNotFoundError.

        This tests the specific case where the package metadata is not found,
        which can happen in development or when the package is not installed properly.
        """
        from automagik_telemetry import AutomagikTelemetry

        with patch.dict(
            os.environ,
            {"AUTOMAGIK_TELEMETRY_ENABLED": "true"},
            clear=False,
        ):
            config = TelemetryConfig(
                project_name="test",
                version="1.0.0",
                batch_size=1,
            )
            client = AutomagikTelemetry(config=config)

            # Mock to raise PackageNotFoundError
            from importlib.metadata import PackageNotFoundError

            with patch(
                "importlib.metadata.version",
                side_effect=PackageNotFoundError("automagik-telemetry"),
            ):
                version = client._get_sdk_version()

                # Verify fallback version
                self.assertEqual(version, "0.0.0-dev")

    @patch.dict(os.environ, {"HOME": tempfile.mkdtemp()})
    def test_get_version_fallback_used_in_resource_attributes(self):
        """
        Test that _get_sdk_version fallback is properly used in resource attributes.

        This test ensures that when _get_sdk_version returns the fallback version,
        it's correctly included in the resource attributes sent with telemetry data.
        """
        from automagik_telemetry import AutomagikTelemetry

        with patch.dict(
            os.environ,
            {"AUTOMAGIK_TELEMETRY_ENABLED": "true"},
            clear=False,
        ):
            config = TelemetryConfig(
                project_name="test",
                version="1.0.0",
                batch_size=1,
            )
            client = AutomagikTelemetry(config=config)

            # Mock importlib to trigger fallback
            with patch("importlib.metadata.version", side_effect=Exception("Test error")):
                resource_attrs = client._get_resource_attributes()

                # Find the telemetry.sdk.version attribute
                sdk_version_attr = None
                for attr in resource_attrs:
                    if attr.get("key") == "telemetry.sdk.version":
                        sdk_version_attr = attr
                        break

                # Verify the fallback version is used
                self.assertIsNotNone(sdk_version_attr)
                self.assertEqual(
                    sdk_version_attr.get("value", {}).get("stringValue"),
                    "0.0.0-dev",
                )


class TestCombinedEdgeCases(unittest.TestCase):
    """Test combined edge cases to ensure robustness."""

    @patch.dict(os.environ, {"HOME": tempfile.mkdtemp()})
    def test_all_edge_cases_together(self):
        """
        Test all edge cases in a single scenario.

        This test combines:
        - ENVIRONMENT variable check (client.py:320)
        - _get_sdk_version fallback (client.py:468-469)

        to ensure they work correctly together.
        """
        with patch.dict(
            os.environ,
            {"ENVIRONMENT": "development"},
            clear=False,
        ):
            from automagik_telemetry import AutomagikTelemetry

            config = TelemetryConfig(
                project_name="test",
                version="1.0.0",
                batch_size=1,
            )

            # Mock importlib to trigger version fallback
            with patch("importlib.metadata.version", side_effect=Exception("Test error")):
                client = AutomagikTelemetry(config=config)

                # Verify telemetry is disabled due to ENVIRONMENT
                self.assertFalse(client.enabled)

                # Verify version fallback still works
                version = client._get_sdk_version()
                self.assertEqual(version, "0.0.0-dev")


if __name__ == "__main__":
    unittest.main()
