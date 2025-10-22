"""
First-run opt-in prompt for telemetry.

Provides a user-friendly, colorful, informative prompt that explains exactly
what data is collected and gives users full control.
"""

import os
import sys
from pathlib import Path


class TelemetryOptIn:
    """
    First-run experience for all Automagik tools.

    Shows a friendly opt-in prompt once per user, stores their decision,
    and respects their choice across all Automagik projects.
    """

    @classmethod
    def _get_preference_file(cls) -> Path:
        """Get the preference file path (lazy evaluation for testability)."""
        return Path.home() / ".automagik" / "telemetry_preference"

    @classmethod
    def _get_opt_out_file(cls) -> Path:
        """Get the opt-out file path (lazy evaluation for testability)."""
        return Path.home() / ".automagik-no-telemetry"

    @classmethod
    def has_user_decided(cls) -> bool:
        """Check if user has already made a telemetry decision."""
        # Check preference file
        if cls._get_preference_file().exists():
            return True

        # Check opt-out file
        if cls._get_opt_out_file().exists():
            return True

        # Check environment variable (explicit decision)
        if os.getenv("AUTOMAGIK_TELEMETRY_ENABLED") is not None:
            return True

        return False

    @classmethod
    def get_user_preference(cls) -> bool | None:
        """
        Get stored user preference.

        Returns:
            True if opted-in, False if opted-out, None if not decided
        """
        # Check opt-out file first (takes precedence)
        if cls._get_opt_out_file().exists():
            return False

        # Check preference file
        preference_file = cls._get_preference_file()
        if preference_file.exists():
            try:
                content = preference_file.read_text().strip().lower()
                return content in ("true", "yes", "1", "enabled")
            except Exception:
                pass

        # Check environment variable
        env_var = os.getenv("AUTOMAGIK_TELEMETRY_ENABLED")
        if env_var is not None:
            return env_var.lower() in ("true", "1", "yes", "on")

        return None

    @classmethod
    def save_preference(cls, enabled: bool) -> None:
        """
        Save user's telemetry preference.

        Args:
            enabled: True to enable telemetry, False to disable
        """
        try:
            preference_file = cls._get_preference_file()
            opt_out_file = cls._get_opt_out_file()

            if enabled:
                # Remove opt-out file if exists
                if opt_out_file.exists():
                    opt_out_file.unlink()

                # Save preference
                preference_file.parent.mkdir(parents=True, exist_ok=True)
                preference_file.write_text("enabled")
            else:
                # Create opt-out file
                opt_out_file.touch()

                # Remove preference file if exists
                if preference_file.exists():
                    preference_file.unlink()
        except Exception:
            # Silent failure - don't break the app
            pass

    @classmethod
    def _supports_color(cls) -> bool:
        """Check if terminal supports ANSI colors."""
        # Windows check
        if sys.platform == "win32":
            # Windows 10+ supports ANSI
            try:
                import platform

                if int(platform.version().split(".")[0]) >= 10:
                    return True
            except Exception:
                pass
            return False

        # Unix/Linux - check if TTY and TERM is set
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            term = os.getenv("TERM", "")
            if term and term != "dumb":
                return True

        return False

    @classmethod
    def _colorize(cls, text: str, color_code: str) -> str:
        """Add ANSI color codes if supported."""
        if not cls._supports_color():
            return text
        return f"\033[{color_code}m{text}\033[0m"

    @classmethod
    def prompt_user(cls, project_name: str = "Automagik") -> bool:
        """
        Show first-run opt-in prompt if user hasn't decided yet.

        Args:
            project_name: Name of the project for personalized messaging

        Returns:
            True if user opted in, False otherwise
        """
        # Don't prompt if user already decided
        if cls.has_user_decided():
            preference = cls.get_user_preference()
            return preference if preference is not None else False

        # Don't prompt in non-interactive environments
        if not cls._is_interactive():
            return False

        # Color codes (ANSI)
        CYAN = "96"  # Bright cyan
        GREEN = "92"  # Bright green
        YELLOW = "93"  # Bright yellow
        RED = "91"  # Bright red
        BLUE = "94"  # Bright blue
        BOLD = "1"  # Bold
        DIM = "2"  # Dim

        # Build colorful prompt
        title = cls._colorize(f"  Help Improve {project_name}! 🚀", f"{BOLD};{CYAN}")

        print(f"""
╔═══════════════════════════════════════════════════════════╗
║{title}{" " * (61 - len(f"  Help Improve {project_name}! 🚀"))}║
╚═══════════════════════════════════════════════════════════╝

We'd love your help making {cls._colorize(project_name, BOLD)} better for everyone.

{cls._colorize("📊 What we collect", f"{BOLD};{GREEN}")} (if you opt-in):
  {cls._colorize("✓", GREEN)} Feature usage (which commands/APIs you use)
  {cls._colorize("✓", GREEN)} Performance metrics (how fast things run)
  {cls._colorize("✓", GREEN)} Error reports (when things break)
  {cls._colorize("✓", GREEN)} Anonymous usage patterns

{cls._colorize("🔒 What we DON'T collect:", f"{BOLD};{RED}")}
  {cls._colorize("✗", RED)} Your messages or personal data
  {cls._colorize("✗", RED)} API keys or credentials
  {cls._colorize("✗", RED)} User identities (everything is anonymized)
  {cls._colorize("✗", RED)} File contents or business logic

{cls._colorize("🌐 Your data, your control:", f"{BOLD};{BLUE}")}
  • Data sent to: {cls._colorize("telemetry.namastex.ai", CYAN)} (open-source dashboard)
  • You can self-host: See docs/telemetry.md
  • Opt-out anytime: Set {cls._colorize("AUTOMAGIK_TELEMETRY_ENABLED=false", YELLOW)}
  • View what's sent: Use {cls._colorize("--telemetry-verbose", YELLOW)} flag

{cls._colorize("More info:", DIM)} https://docs.automagik.ai/privacy
""")

        try:
            prompt_text = cls._colorize("Enable telemetry? [y/N]: ", f"{BOLD};{CYAN}")
            response = input(prompt_text).strip().lower()
            enabled = response in ("y", "yes")

            # Save preference
            cls.save_preference(enabled)

            # Show confirmation
            if enabled:
                print(f"\n{cls._colorize('✅ Thank you!', f'{BOLD};{GREEN}')} Telemetry enabled.")
                print("   Your anonymous usage data will help improve Automagik.\n")
            else:
                print(f"\n{cls._colorize('✅ Telemetry disabled.', f'{BOLD};{YELLOW}')}")
                print(
                    f"   You can enable it later with: {cls._colorize('export AUTOMAGIK_TELEMETRY_ENABLED=true', CYAN)}\n"
                )

            return enabled

        except (KeyboardInterrupt, EOFError):
            # User cancelled - treat as "no"
            print(f"\n\n{cls._colorize('✅ Telemetry disabled.', f'{BOLD};{YELLOW}')}")
            cls.save_preference(False)
            return False

    @staticmethod
    def _is_interactive() -> bool:
        """Check if we're in an interactive terminal."""
        # Check if stdin/stdout are TTYs
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            return False

        # Check if in CI environment
        ci_vars = ["CI", "GITHUB_ACTIONS", "TRAVIS", "JENKINS", "GITLAB_CI", "CIRCLECI"]
        if any(os.getenv(var) for var in ci_vars):
            return False

        return True


def should_prompt_user(project_name: str = "Automagik") -> bool:
    """
    Convenience function to check if we should show the opt-in prompt.

    Args:
        project_name: Name of the project

    Returns:
        True if we should prompt, False otherwise
    """
    return not TelemetryOptIn.has_user_decided() and TelemetryOptIn._is_interactive()


def prompt_user_if_needed(project_name: str = "Automagik") -> bool:
    """
    Show opt-in prompt if needed and return user's decision.

    Args:
        project_name: Name of the project

    Returns:
        True if telemetry should be enabled, False otherwise
    """
    return TelemetryOptIn.prompt_user(project_name)
