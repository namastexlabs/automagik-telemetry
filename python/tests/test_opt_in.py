"""
Comprehensive tests for TelemetryOptIn.

Tests cover:
- Opt-in prompt flow
- Preference storage and retrieval
- User decision detection
- CI environment detection
- Interactive terminal detection
- Color support detection
- Input handling (yes/no/interrupt)
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from automagik_telemetry.opt_in import (
    TelemetryOptIn,
    prompt_user_if_needed,
    should_prompt_user,
)


class TestUserDecisionDetection:
    """Test detection of whether user has already decided."""

    def test_should_return_false_when_no_decision_made(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that has_user_decided returns False when no decision exists."""
        assert TelemetryOptIn.has_user_decided() is False

    def test_should_return_true_when_preference_file_exists(
        self, temp_home: Path, telemetry_preference_file: Path, clean_env: None
    ) -> None:
        """Test that preference file indicates decision was made."""
        assert TelemetryOptIn.has_user_decided() is True

    def test_should_return_true_when_opt_out_file_exists(
        self, temp_home: Path, opt_out_file: Path, clean_env: None
    ) -> None:
        """Test that opt-out file indicates decision was made."""
        assert TelemetryOptIn.has_user_decided() is True

    def test_should_return_true_when_env_var_set(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that environment variable indicates decision was made."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        assert TelemetryOptIn.has_user_decided() is True


class TestGetUserPreference:
    """Test retrieval of user preference."""

    def test_should_return_none_when_no_preference(self, temp_home: Path, clean_env: None) -> None:
        """Test that get_user_preference returns None when no decision made."""
        assert TelemetryOptIn.get_user_preference() is None

    def test_should_return_false_when_opt_out_file_exists(
        self, temp_home: Path, opt_out_file: Path, clean_env: None
    ) -> None:
        """Test that opt-out file indicates False preference."""
        assert TelemetryOptIn.get_user_preference() is False

    def test_should_return_true_when_preference_file_says_enabled(
        self, temp_home: Path, telemetry_preference_file: Path, clean_env: None
    ) -> None:
        """Test that preference file with 'enabled' returns True."""
        assert TelemetryOptIn.get_user_preference() is True

    @pytest.mark.parametrize("content", ["true", "yes", "1", "enabled", "TRUE", "YES", "ENABLED"])
    def test_should_accept_various_enabled_values(
        self, temp_home: Path, automagik_dir: Path, clean_env: None, content: str
    ) -> None:
        """Test that various truthy values in preference file are accepted."""
        pref_file = automagik_dir / "telemetry_preference"
        pref_file.write_text(content)

        assert TelemetryOptIn.get_user_preference() is True

    def test_should_return_false_when_preference_file_says_disabled(
        self, temp_home: Path, automagik_dir: Path, clean_env: None
    ) -> None:
        """Test that preference file with non-truthy value returns False."""
        pref_file = automagik_dir / "telemetry_preference"
        pref_file.write_text("disabled")

        assert TelemetryOptIn.get_user_preference() is False

    def test_should_handle_preference_file_read_error(
        self, temp_home: Path, automagik_dir: Path, clean_env: None
    ) -> None:
        """Test graceful handling of preference file read errors."""
        # Create a directory instead of file to trigger read error
        pref_file = automagik_dir / "telemetry_preference"
        pref_file.mkdir()

        assert TelemetryOptIn.get_user_preference() is None

    def test_should_prefer_opt_out_file_over_preference_file(
        self, temp_home: Path, telemetry_preference_file: Path, opt_out_file: Path, clean_env: None
    ) -> None:
        """Test that opt-out file takes precedence over preference file."""
        # Preference file says enabled, but opt-out file exists
        assert TelemetryOptIn.get_user_preference() is False

    def test_should_read_from_env_var(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that preference can be read from environment variable."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")

        assert TelemetryOptIn.get_user_preference() is True

    @pytest.mark.parametrize("value", ["true", "1", "yes", "on", "TRUE", "YES", "ON"])
    def test_should_accept_various_env_var_values(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        """Test that various truthy environment variable values are accepted."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", value)

        assert TelemetryOptIn.get_user_preference() is True


class TestSavePreference:
    """Test saving user preference."""

    def test_should_save_enabled_preference(self, temp_home: Path, clean_env: None) -> None:
        """Test saving an 'enabled' preference."""
        TelemetryOptIn.save_preference(True)

        pref_file = temp_home / ".automagik" / "telemetry_preference"
        assert pref_file.exists()
        assert pref_file.read_text() == "enabled"

    def test_should_create_automagik_dir_if_missing(self, temp_home: Path, clean_env: None) -> None:
        """Test that .automagik directory is created if it doesn't exist."""
        automagik_dir = temp_home / ".automagik"
        assert not automagik_dir.exists()

        TelemetryOptIn.save_preference(True)

        assert automagik_dir.exists()
        assert automagik_dir.is_dir()

    def test_should_remove_opt_out_file_when_enabling(
        self, temp_home: Path, opt_out_file: Path, clean_env: None
    ) -> None:
        """Test that opt-out file is removed when saving enabled preference."""
        TelemetryOptIn.save_preference(True)

        assert not opt_out_file.exists()

    def test_should_create_opt_out_file_when_disabling(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that opt-out file is created when saving disabled preference."""
        TelemetryOptIn.save_preference(False)

        opt_out_file = temp_home / ".automagik-no-telemetry"
        assert opt_out_file.exists()

    def test_should_remove_preference_file_when_disabling(
        self, temp_home: Path, telemetry_preference_file: Path, clean_env: None
    ) -> None:
        """Test that preference file is removed when saving disabled preference."""
        TelemetryOptIn.save_preference(False)

        assert not telemetry_preference_file.exists()

    def test_should_handle_file_write_errors_silently(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that file write errors are handled silently."""
        with patch("pathlib.Path.write_text", side_effect=PermissionError):
            # Should not raise exception
            TelemetryOptIn.save_preference(True)


class TestColorSupport:
    """Test terminal color support detection."""

    def test_should_detect_color_support_on_linux_tty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test color support detection on Linux with TTY."""
        monkeypatch.setattr("sys.platform", "linux")
        monkeypatch.setenv("TERM", "xterm-256color")

        with patch("sys.stdout.isatty", return_value=True):
            assert TelemetryOptIn._supports_color() is True

    def test_should_not_support_color_when_not_tty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that color is not supported when stdout is not a TTY."""
        with patch("sys.stdout.isatty", return_value=False):
            assert TelemetryOptIn._supports_color() is False

    def test_should_not_support_color_with_dumb_terminal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that color is not supported with TERM=dumb."""
        monkeypatch.setenv("TERM", "dumb")

        with patch("sys.stdout.isatty", return_value=True):
            assert TelemetryOptIn._supports_color() is False

    def test_should_not_support_color_without_term_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that color is not supported without TERM environment variable."""
        monkeypatch.delenv("TERM", raising=False)

        with patch("sys.stdout.isatty", return_value=True):
            assert TelemetryOptIn._supports_color() is False

    def test_should_support_color_on_windows_10_plus(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test color support on Windows 10+."""
        monkeypatch.setattr("sys.platform", "win32")

        with patch("platform.version", return_value="10.0.19041"):
            assert TelemetryOptIn._supports_color() is True

    def test_should_not_support_color_on_old_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that color is not supported on Windows < 10."""
        monkeypatch.setattr("sys.platform", "win32")

        with patch("platform.version", return_value="6.1.7601"):
            assert TelemetryOptIn._supports_color() is False


class TestColorize:
    """Test text colorization."""

    def test_should_add_color_codes_when_supported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that ANSI color codes are added when colors are supported."""
        with patch.object(TelemetryOptIn, "_supports_color", return_value=True):
            result = TelemetryOptIn._colorize("test", "92")
            assert result == "\033[92mtest\033[0m"

    def test_should_not_add_color_codes_when_not_supported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that no color codes are added when colors are not supported."""
        with patch.object(TelemetryOptIn, "_supports_color", return_value=False):
            result = TelemetryOptIn._colorize("test", "92")
            assert result == "test"


class TestInteractiveDetection:
    """Test interactive terminal detection."""

    def test_should_be_interactive_with_tty(self) -> None:
        """Test that interactive is True with TTY."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                assert TelemetryOptIn._is_interactive() is True

    def test_should_not_be_interactive_without_stdin_tty(self) -> None:
        """Test that interactive is False when stdin is not TTY."""
        with patch("sys.stdin.isatty", return_value=False):
            with patch("sys.stdout.isatty", return_value=True):
                assert TelemetryOptIn._is_interactive() is False

    def test_should_not_be_interactive_without_stdout_tty(self) -> None:
        """Test that interactive is False when stdout is not TTY."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=False):
                assert TelemetryOptIn._is_interactive() is False

    @pytest.mark.parametrize(
        "ci_var", ["CI", "GITHUB_ACTIONS", "TRAVIS", "JENKINS", "GITLAB_CI", "CIRCLECI"]
    )
    def test_should_not_be_interactive_in_ci(
        self, monkeypatch: pytest.MonkeyPatch, ci_var: str
    ) -> None:
        """Test that interactive is False in CI environments."""
        monkeypatch.setenv(ci_var, "true")

        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                assert TelemetryOptIn._is_interactive() is False


class TestPromptUser:
    """Test user prompting functionality."""

    def test_should_not_prompt_if_already_decided(
        self, temp_home: Path, telemetry_preference_file: Path, clean_env: None
    ) -> None:
        """Test that prompt is not shown if user already decided."""
        with patch("builtins.input") as mock_input:
            result = TelemetryOptIn.prompt_user("test-project")

            # Should return existing preference without prompting
            mock_input.assert_not_called()
            assert result is True  # preference file says "enabled"

    def test_should_not_prompt_in_non_interactive_environment(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test that prompt is not shown in non-interactive environments."""
        with patch("sys.stdin.isatty", return_value=False):
            with patch("builtins.input") as mock_input:
                result = TelemetryOptIn.prompt_user("test-project")

                mock_input.assert_not_called()
                assert result is False

    def test_should_display_prompt_with_project_name(
        self, temp_home: Path, clean_env: None, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that prompt includes the project name."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("builtins.input", return_value="y"):
                    TelemetryOptIn.prompt_user("omni")

                    captured = capsys.readouterr()
                    assert "omni" in captured.out
                    assert "Help Improve" in captured.out

    def test_should_accept_yes_answer(self, temp_home: Path, clean_env: None) -> None:
        """Test that 'y' answer enables telemetry."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("builtins.input", return_value="y"):
                    result = TelemetryOptIn.prompt_user("test-project")

                    assert result is True

                    # Should save preference
                    pref_file = temp_home / ".automagik" / "telemetry_preference"
                    assert pref_file.exists()

    def test_should_accept_yes_full_word(self, temp_home: Path, clean_env: None) -> None:
        """Test that 'yes' answer enables telemetry."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("builtins.input", return_value="yes"):
                    result = TelemetryOptIn.prompt_user("test-project")

                    assert result is True

    def test_should_reject_no_answer(self, temp_home: Path, clean_env: None) -> None:
        """Test that 'n' answer disables telemetry."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("builtins.input", return_value="n"):
                    result = TelemetryOptIn.prompt_user("test-project")

                    assert result is False

                    # Should create opt-out file
                    opt_out_file = temp_home / ".automagik-no-telemetry"
                    assert opt_out_file.exists()

    def test_should_treat_empty_input_as_no(self, temp_home: Path, clean_env: None) -> None:
        """Test that empty input (Enter key) is treated as 'no'."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("builtins.input", return_value=""):
                    result = TelemetryOptIn.prompt_user("test-project")

                    assert result is False

    def test_should_handle_keyboard_interrupt(self, temp_home: Path, clean_env: None) -> None:
        """Test that Ctrl+C is treated as 'no'."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("builtins.input", side_effect=KeyboardInterrupt):
                    result = TelemetryOptIn.prompt_user("test-project")

                    assert result is False

                    # Should create opt-out file
                    opt_out_file = temp_home / ".automagik-no-telemetry"
                    assert opt_out_file.exists()

    def test_should_handle_eof_error(self, temp_home: Path, clean_env: None) -> None:
        """Test that EOF is treated as 'no'."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("builtins.input", side_effect=EOFError):
                    result = TelemetryOptIn.prompt_user("test-project")

                    assert result is False

    def test_should_show_confirmation_message_on_yes(
        self, temp_home: Path, clean_env: None, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that confirmation message is shown when user opts in."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("builtins.input", return_value="y"):
                    TelemetryOptIn.prompt_user("test-project")

                    captured = capsys.readouterr()
                    assert "Thank you" in captured.out
                    assert "Telemetry enabled" in captured.out

    def test_should_show_confirmation_message_on_no(
        self, temp_home: Path, clean_env: None, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that confirmation message is shown when user opts out."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("builtins.input", return_value="n"):
                    TelemetryOptIn.prompt_user("test-project")

                    captured = capsys.readouterr()
                    assert "Telemetry disabled" in captured.out

    def test_should_display_privacy_information(
        self, temp_home: Path, clean_env: None, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that privacy information is displayed in prompt."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("builtins.input", return_value="y"):
                    TelemetryOptIn.prompt_user("test-project")

                    captured = capsys.readouterr()
                    assert "What we collect" in captured.out
                    assert "What we DON'T collect" in captured.out
                    assert "Feature usage" in captured.out
                    assert "API keys or credentials" in captured.out


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_should_prompt_user_returns_true_when_needed(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test should_prompt_user returns True when prompting is needed."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                assert should_prompt_user() is True

    def test_should_prompt_user_returns_false_when_decided(
        self, temp_home: Path, telemetry_preference_file: Path, clean_env: None
    ) -> None:
        """Test should_prompt_user returns False when already decided."""
        assert should_prompt_user() is False

    def test_prompt_user_if_needed_prompts_when_needed(
        self, temp_home: Path, clean_env: None
    ) -> None:
        """Test prompt_user_if_needed shows prompt when needed."""
        with patch("sys.stdin.isatty", return_value=True):
            with patch("sys.stdout.isatty", return_value=True):
                with patch("builtins.input", return_value="y"):
                    result = prompt_user_if_needed("test-project")

                    assert result is True

    def test_prompt_user_if_needed_uses_existing_preference(
        self, temp_home: Path, telemetry_preference_file: Path, clean_env: None
    ) -> None:
        """Test prompt_user_if_needed uses existing preference."""
        with patch("builtins.input") as mock_input:
            result = prompt_user_if_needed("test-project")

            # Should not prompt
            mock_input.assert_not_called()
            assert result is True


class TestWindowsColorSupport:
    """Test Windows-specific color support edge cases."""

    def test_should_handle_windows_version_parse_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test handling of Windows version parsing errors."""
        monkeypatch.setattr("sys.platform", "win32")

        # Mock platform.version to raise an exception
        with patch("platform.version", side_effect=Exception("Parse error")):
            assert TelemetryOptIn._supports_color() is False

    def test_should_handle_windows_version_invalid_format(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test handling of invalid Windows version format."""
        monkeypatch.setattr("sys.platform", "win32")

        # Mock platform.version with invalid format (no dots)
        with patch("platform.version", return_value="InvalidVersion"):
            assert TelemetryOptIn._supports_color() is False


class TestErrorHandling:
    """Test error handling in save_preference."""

    def test_should_handle_opt_out_file_unlink_error(
        self, temp_home: Path, opt_out_file: Path, clean_env: None
    ) -> None:
        """Test handling of opt-out file deletion errors."""
        with patch("pathlib.Path.unlink", side_effect=PermissionError):
            # Should not raise exception
            TelemetryOptIn.save_preference(True)

    def test_should_handle_preference_file_unlink_error(
        self, temp_home: Path, telemetry_preference_file: Path, clean_env: None
    ) -> None:
        """Test handling of preference file deletion errors."""
        with patch("pathlib.Path.unlink", side_effect=PermissionError):
            # Should not raise exception
            TelemetryOptIn.save_preference(False)

    def test_should_handle_opt_out_file_touch_error(self, temp_home: Path, clean_env: None) -> None:
        """Test handling of opt-out file creation errors."""
        with patch("pathlib.Path.touch", side_effect=PermissionError):
            # Should not raise exception
            TelemetryOptIn.save_preference(False)


class TestAdditionalEdgeCases:
    """Test additional edge cases for complete coverage."""

    def test_should_handle_env_var_false_values(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that false environment variable values are handled correctly."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "false")
        assert TelemetryOptIn.get_user_preference() is False

    def test_should_handle_env_var_zero_value(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that '0' environment variable value is handled correctly."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "0")
        assert TelemetryOptIn.get_user_preference() is False

    def test_should_handle_whitespace_in_preference_file(
        self, temp_home: Path, automagik_dir: Path, clean_env: None
    ) -> None:
        """Test that whitespace in preference file is handled correctly."""
        pref_file = automagik_dir / "telemetry_preference"
        pref_file.write_text("  enabled  \n")
        assert TelemetryOptIn.get_user_preference() is True

    def test_should_handle_stdout_without_isatty_method(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test color support when stdout doesn't have isatty method."""
        mock_stdout = Mock(spec=[])  # No isatty method
        monkeypatch.setattr("sys.stdout", mock_stdout)

        assert TelemetryOptIn._supports_color() is False

    def test_prompt_user_returns_existing_opt_out_preference(
        self, temp_home: Path, opt_out_file: Path, clean_env: None
    ) -> None:
        """Test that prompt_user returns False when opt-out file exists."""
        with patch("builtins.input") as mock_input:
            result = TelemetryOptIn.prompt_user("test-project")

            # Should return existing preference without prompting
            mock_input.assert_not_called()
            assert result is False

    def test_get_user_preference_env_var_takes_precedence_over_nothing(
        self, temp_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that environment variable is checked when no files exist."""
        monkeypatch.setenv("AUTOMAGIK_TELEMETRY_ENABLED", "true")
        assert TelemetryOptIn.get_user_preference() is True
