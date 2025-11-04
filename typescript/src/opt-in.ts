/**
 * First-run opt-in prompt for telemetry.
 *
 * Provides a user-friendly, colorful, informative prompt that explains exactly
 * what data is collected and gives users full control.
 */

import * as fs from "fs";
import * as os from "os";
import * as path from "path";
import * as readline from "readline";

export class TelemetryOptIn {
  private static readonly PREFERENCE_FILE = path.join(
    os.homedir(),
    ".automagik",
    "telemetry_preference",
  );
  private static readonly OPT_OUT_FILE = path.join(
    os.homedir(),
    ".automagik-no-telemetry",
  );

  /**
   * Check if user has already made a telemetry decision.
   */
  static hasUserDecided(): boolean {
    // Check preference file
    if (fs.existsSync(this.PREFERENCE_FILE)) {
      return true;
    }

    // Check opt-out file
    if (fs.existsSync(this.OPT_OUT_FILE)) {
      return true;
    }

    // Check environment variable (explicit decision)
    if (process.env.AUTOMAGIK_TELEMETRY_ENABLED !== undefined) {
      return true;
    }

    return false;
  }

  /**
   * Get stored user preference.
   *
   * @returns true if opted-in, false if opted-out, null if not decided
   */
  static getUserPreference(): boolean | null {
    // Check opt-out file first (takes precedence)
    if (fs.existsSync(this.OPT_OUT_FILE)) {
      return false;
    }

    // Check preference file
    if (fs.existsSync(this.PREFERENCE_FILE)) {
      try {
        const content = fs
          .readFileSync(this.PREFERENCE_FILE, "utf-8")
          .trim()
          .toLowerCase();
        return ["true", "yes", "1", "enabled"].includes(content);
      } catch {
        // Ignore errors
      }
    }

    // Check environment variable
    const envVar = process.env.AUTOMAGIK_TELEMETRY_ENABLED;
    if (envVar !== undefined) {
      return ["true", "1", "yes", "on"].includes(envVar.toLowerCase());
    }

    return null;
  }

  /**
   * Persist user's telemetry preference to filesystem.
   *
   * Saves the user's decision to enable or disable telemetry. Uses a preference file
   * for opt-in and a simple marker file for opt-out. Silently fails if filesystem
   * operations fail (directory creation, file write).
   *
   * @param enabled - true to enable telemetry, false to disable
   * @returns void
   *
   * @remarks
   * - If enabled: Creates ~/.automagik/telemetry_preference file with "enabled"
   * - If disabled: Creates ~/.automagik-no-telemetry marker file
   * - Opposite files are deleted when changing preference
   * - Directory ~/.automagik/ created automatically if missing
   * - Errors are silently caught to avoid breaking application flow
   * - Takes precedence over environment variables when reading preference
   * - Subsequent calls to getUserPreference() will return the saved value
   *
   * @example
   * ```typescript
   * // User opts in to telemetry
   * TelemetryOptIn.savePreference(true);
   * // Creates: ~/.automagik/telemetry_preference
   * // Removes: ~/.automagik-no-telemetry (if exists)
   *
   * // User opts out
   * TelemetryOptIn.savePreference(false);
   * // Creates: ~/.automagik-no-telemetry
   * // Removes: ~/.automagik/telemetry_preference (if exists)
   * ```
   */
  static savePreference(enabled: boolean): void {
    try {
      if (enabled) {
        // Remove opt-out file if exists
        if (fs.existsSync(this.OPT_OUT_FILE)) {
          fs.unlinkSync(this.OPT_OUT_FILE);
        }

        // Save preference
        const dir = path.dirname(this.PREFERENCE_FILE);
        if (!fs.existsSync(dir)) {
          fs.mkdirSync(dir, { recursive: true });
        }
        fs.writeFileSync(this.PREFERENCE_FILE, "enabled");
      } else {
        // Create opt-out file
        fs.closeSync(fs.openSync(this.OPT_OUT_FILE, "w"));

        // Remove preference file if exists
        if (fs.existsSync(this.PREFERENCE_FILE)) {
          fs.unlinkSync(this.PREFERENCE_FILE);
        }
      }
    } catch {
      // Silent failure - don't break the app
    }
  }

  /**
   * Check if terminal supports ANSI color codes.
   *
   * Detects terminal color support using multiple heuristics: environment variables,
   * TTY detection, platform detection, and terminal type. Respects NO_COLOR convention
   * and FORCE_COLOR override.
   *
   * @returns boolean - true if ANSI colors can be used, false otherwise
   *
   * @remarks
   * - NO_COLOR env var takes precedence (returns false if set)
   * - FORCE_COLOR env var forces colors (returns true if set)
   * - Requires stdout to be a TTY (interactive terminal)
   * - Windows 10+ supports ANSI natively (returns true)
   * - Unix/Linux checks TERM variable (must not be "dumb")
   * - Empty TERM environment variable treated as no color support
   * - Safe fallback: returns false if uncertain
   *
   * @example
   * ```typescript
   * // In interactive terminal
   * TelemetryOptIn['supportsColor'](); // Returns true
   *
   * // With NO_COLOR set
   * process.env.NO_COLOR = "1";
   * TelemetryOptIn['supportsColor'](); // Returns false
   *
   * // In piped output or file redirect
   * // stdout.isTTY will be false, returns false
   * ```
   */
  private static supportsColor(): boolean {
    // Check NO_COLOR environment variable
    if (process.env.NO_COLOR) {
      return false;
    }

    // Check FORCE_COLOR
    if (process.env.FORCE_COLOR) {
      return true;
    }

    // Check if stdout is a TTY
    if (!process.stdout.isTTY) {
      return false;
    }

    // Windows 10+ supports ANSI
    if (process.platform === "win32") {
      return true;
    }

    // Unix/Linux - check TERM
    const term = process.env.TERM || "";
    return term !== "dumb" && term !== "";
  }

  /**
   * Wrap text with ANSI color codes if terminal supports colors.
   *
   * Conditionally applies ANSI escape sequences to colorize text. If terminal
   * doesn't support colors (detected via supportsColor()), returns plain text.
   * Supports multiple style attributes via compound color codes.
   *
   * @param text - The text to colorize
   * @param colorCode - ANSI color code or compound style (e.g., "92", "1;96", "2;33")
   * @returns string - Colored text with ANSI codes or plain text
   *
   * @remarks
   * - Color codes follow ANSI SGR (Select Graphic Rendition) standard
   * - Format: \x1b[{code}m{text}\x1b[0m
   * - 0m resets all styles after text
   * - Multiple styles: semicolon-separated (e.g., "1;92" = bold + bright green)
   * - Common codes:
   *   - 1 = bold
   *   - 2 = dim
   *   - 91-97 = bright foreground colors (red, green, yellow, blue, magenta, cyan, white)
   *   - 30-37 = normal foreground colors
   * - Safe: no throw even with invalid codes (shell just ignores them)
   * - Performance: single function call, no regex needed
   *
   * @example
   * ```typescript
   * // Bright green text
   * TelemetryOptIn['colorize']("✓", "92"); // Returns "\\x1b[92m✓\\x1b[0m"
   *
   * // Bold bright cyan
   * TelemetryOptIn['colorize']("Title", "1;96"); // Returns "\\x1b[1;96mTitle\\x1b[0m"
   *
   * // Dim text
   * TelemetryOptIn['colorize']("Footer", "2"); // Returns "\\x1b[2mFooter\\x1b[0m"
   *
   * // No color support - returns plain text
   * process.env.NO_COLOR = "1";
   * TelemetryOptIn['colorize']("Text", "92"); // Returns "Text"
   * ```
   */
  private static colorize(text: string, colorCode: string): string {
    if (!this.supportsColor()) {
      return text;
    }
    return `\x1b[${colorCode}m${text}\x1b[0m`;
  }

  /**
   * Show first-run opt-in prompt if user hasn't decided yet.
   */
  static async promptUser(projectName: string = "Automagik"): Promise<boolean> {
    // Don't prompt if user already decided
    if (this.hasUserDecided()) {
      const preference = this.getUserPreference();
      return preference !== null ? preference : false;
    }

    // Don't prompt in non-interactive environments
    if (!this.isInteractive()) {
      return false;
    }

    // Color codes (ANSI)
    const CYAN = "96";
    const GREEN = "92";
    const YELLOW = "93";
    const RED = "91";
    const BLUE = "94";
    const BOLD = "1";
    const DIM = "2";

    // Build colorful prompt
    const titleText = `  Help Improve ${projectName}! 🚀`;
    const title = this.colorize(titleText, `${BOLD};${CYAN}`);
    const padding = " ".repeat(61 - titleText.length);

    console.log(`
╔═══════════════════════════════════════════════════════════╗
║${title}${padding}║
╚═══════════════════════════════════════════════════════════╝

We'd love your help making ${this.colorize(projectName, BOLD)} better for everyone.

${this.colorize("📊 What we collect", `${BOLD};${GREEN}`)} (if you opt-in):
  ${this.colorize("✓", GREEN)} Feature usage (which commands/APIs you use)
  ${this.colorize("✓", GREEN)} Performance metrics (how fast things run)
  ${this.colorize("✓", GREEN)} Error reports (when things break)
  ${this.colorize("✓", GREEN)} Anonymous usage patterns

${this.colorize("🔒 What we DON'T collect:", `${BOLD};${RED}`)}
  ${this.colorize("✗", RED)} Your messages or personal data
  ${this.colorize("✗", RED)} API keys or credentials
  ${this.colorize("✗", RED)} User identities (everything is anonymized)
  ${this.colorize("✗", RED)} File contents or business logic

${this.colorize("🌐 Your data, your control:", `${BOLD};${BLUE}`)}
  • Data sent to: ${this.colorize("telemetry.namastex.ai", CYAN)} (open-source dashboard)
  • You can self-host: See docs/telemetry.md
  • Opt-out anytime: Set ${this.colorize("AUTOMAGIK_TELEMETRY_ENABLED=false", YELLOW)}
  • View what's sent: Use ${this.colorize("--telemetry-verbose", YELLOW)} flag

${this.colorize("More info:", DIM)} https://docs.automagik.ai/privacy
`);

    try {
      const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
      });

      const response = await new Promise<string>((resolve) => {
        const promptText = this.colorize(
          "Enable telemetry? [y/N]: ",
          `${BOLD};${CYAN}`,
        );
        rl.question(promptText, (answer) => {
          rl.close();
          resolve(answer);
        });
      });

      const enabled = ["y", "yes"].includes(response.trim().toLowerCase());

      // Save preference
      this.savePreference(enabled);

      // Show confirmation
      if (enabled) {
        console.log(
          `\n${this.colorize("✅ Thank you!", `${BOLD};${GREEN}`)} Telemetry enabled.`,
        );
        console.log(
          "   Your anonymous usage data will help improve Automagik.\n",
        );
      } else {
        console.log(
          `\n${this.colorize("✅ Telemetry disabled.", `${BOLD};${YELLOW}`)}`,
        );
        console.log(
          `   You can enable it later with: ${this.colorize("export AUTOMAGIK_TELEMETRY_ENABLED=true", CYAN)}\n`,
        );
      }

      return enabled;
    } catch (error) {
      // User cancelled - treat as "no"
      console.log(
        `\n\n${this.colorize("✅ Telemetry disabled.", `${BOLD};${YELLOW}`)}`,
      );
      this.savePreference(false);
      return false;
    }
  }

  /**
   * Check if running in an interactive terminal environment.
   *
   * Determines whether the user can interact with prompts and input. Checks both
   * TTY status and CI environment variables to avoid prompting in automated contexts.
   *
   * @returns boolean - true if running interactively, false in CI or non-TTY context
   *
   * @remarks
   * - Both stdin and stdout must be TTY (not pipes, files, or sockets)
   * - Returns false in CI environments to prevent hanging builds
   * - CI detection: checks common CI platform env vars
   * - Non-interactive contexts: cron jobs, service restarts, background tasks
   * - Safe: defaults to false if uncertain
   * - Side effect free: only reads environment and process properties
   *
   * @example
   * ```typescript
   * // In interactive terminal
   * TelemetryOptIn['isInteractive'](); // Returns true
   *
   * // In CI pipeline
   * process.env.GITHUB_ACTIONS = "true";
   * TelemetryOptIn['isInteractive'](); // Returns false
   *
   * // Piped to file
   * // node script.js > output.txt
   * // TelemetryOptIn['isInteractive'](); // Returns false (stdout.isTTY = false)
   * ```
   */
  private static isInteractive(): boolean {
    // Check if stdin/stdout are TTYs
    if (!process.stdin.isTTY || !process.stdout.isTTY) {
      return false;
    }

    // Check if in CI environment
    const ciVars = [
      "CI",
      "GITHUB_ACTIONS",
      "TRAVIS",
      "JENKINS",
      "GITLAB_CI",
      "CIRCLECI",
    ];
    if (ciVars.some((v) => process.env[v])) {
      return false;
    }

    return true;
  }
}

/**
 * Convenience function to check if we should show the opt-in prompt.
 */
export function shouldPromptUser(_projectName: string = "Automagik"): boolean {
  return !TelemetryOptIn.hasUserDecided() && TelemetryOptIn["isInteractive"]();
}

/**
 * Show opt-in prompt if needed and return user's decision.
 */
export async function promptUserIfNeeded(
  projectName: string = "Automagik",
): Promise<boolean> {
  return TelemetryOptIn.promptUser(projectName);
}
