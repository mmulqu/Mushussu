#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thoth Runner - Wrapper script that enables self-restart capability.
Run this instead of bot.py directly. When bot.py exits with code 42,
the wrapper restarts it. Any other exit code stops the wrapper.

Usage:
    python run.py                         # Run with Discord + HTTP server (Claude mode)
    python run.py discord                 # Discord only (Claude mode)
    python run.py --gemini discord        # Discord only (Gemini mode)
    python run.py cli                     # CLI mode (no restart loop)
    python run.py --gemini cli            # CLI mode with Gemini

Extra:
    python run.py discord --debug --env-file C:\\path\\to\\.env
    python run.py --gemini discord --debug --env-file C:\\path\\to\\.env
"""
import os
import subprocess
import sys
import time
from pathlib import Path

# Thoth-specific imports
from git_utils import git_pull, is_git_repo, GitError

RESTART_CODE = 42
SCRIPT_DIR = Path(__file__).parent
BOT_SCRIPT = SCRIPT_DIR / "bot.py"
STATE_DIR = SCRIPT_DIR / "state"

# Restart mode file - same location as bot.py uses
RESTART_MODE_FILE = STATE_DIR / "restart_mode.txt"


def _parse_args(argv: list[str]) -> tuple[list[str], str | None, bool]:
    """
    Parse --env-file <path> and --gemini from argv.
    Returns (cleaned_args, env_file_or_none, gemini_mode).
    """
    cleaned = []
    env_file = None
    gemini_mode = False
    i = 0
    while i < len(argv):
        if argv[i] == "--env-file":
            if i + 1 >= len(argv):
                raise SystemExit("Error: --env-file requires a path")
            env_file = argv[i + 1]
            i += 2
            continue
        if argv[i] == "--gemini":
            gemini_mode = True
            i += 1
            continue
        cleaned.append(argv[i])
        i += 1
    return cleaned, env_file, gemini_mode


def check_mode_override() -> str | None:
    """
    Check for mode override file written by restart_self tool.
    Returns 'claude', 'gemini', or None.
    Deletes the file after reading.
    """
    if not RESTART_MODE_FILE.exists():
        return None

    try:
        mode = RESTART_MODE_FILE.read_text(encoding="utf-8").strip().lower()
        RESTART_MODE_FILE.unlink()  # Delete after reading
        if mode in ("claude", "gemini"):
            return mode
        return None
    except Exception as e:
        print(f"[Runner] Error reading restart mode file: {e}")
        return None


def run_bot(args: list[str], env_file: str | None, gemini_mode: bool) -> int:
    """Run bot.py and return its exit code."""
    # Build command - add "gemini" arg if in gemini mode
    bot_args = args.copy()
    if gemini_mode:
        bot_args.append("gemini")

    cmd = [sys.executable, str(BOT_SCRIPT)] + bot_args
    mode_str = "Gemini" if gemini_mode else "Claude"
    print(f"[Runner] Starting ({mode_str} mode): {' '.join(cmd)}")

    # Child environment
    child_env = os.environ.copy()
    # UTF-8 output fix for the child process
    child_env.setdefault("PYTHONUTF8", "1")
    child_env.setdefault("PYTHONIOENCODING", "utf-8")
    # .env selection for the child (bot.py loads THOTH_ENV_FILE)
    if env_file:
        child_env["THOTH_ENV_FILE"] = env_file

    try:
        result = subprocess.run(cmd, cwd=str(SCRIPT_DIR), env=child_env)
        return result.returncode
    except KeyboardInterrupt:
        print("\n[Runner] Interrupted by user")
        return 0


def main():
    # Ensure state directory exists
    STATE_DIR.mkdir(exist_ok=True)

    # Pull args after run.py
    raw_args = sys.argv[1:]

    # Extract --env-file and --gemini (runner-level), pass remaining args to bot.py
    args, env_file, gemini_mode = _parse_args(raw_args)

    # CLI mode doesn't need restart loop
    if "cli" in args:
        sys.exit(run_bot(args, env_file, gemini_mode))

    mode_str = "Gemini" if gemini_mode else "Claude"
    print("[Runner] Thoth Runner started")
    print(f"[Runner] Initial Mode: {mode_str}")
    print(f"[Runner] Exit code {RESTART_CODE} = restart, any other = stop")

    if env_file:
        print(f"[Runner] Using env file: {env_file}")
    else:
        print(f"[Runner] Using default env file: {SCRIPT_DIR / '.env'} (or THOTH_ENV_FILE if set)")
    print()

    restart_count = 0
    while True:
        # ===== PULL LATEST CODE =====
        if restart_count > 0: # Only pull on restarts, not the initial run
            try:
                if is_git_repo(str(SCRIPT_DIR)):
                    print("[Runner] Checking for updates...")
                    pull_output = git_pull(str(SCRIPT_DIR))
                    if "Already up to date." not in pull_output:
                        print("[Runner] Updates pulled successfully:")
                        # Indent the output for readability
                        for line in pull_output.strip().split('\n'):
                            print(f"[Runner]   {line}")
                    else:
                        print("[Runner] Already up to date.")
                else:
                    print("[Runner] Not a Git repository, skipping pull.")
            except GitError as e:
                print(f"[Runner] Error pulling updates: {e}", file=sys.stderr)
                print("[Runner] Continuing with local version.", file=sys.stderr)
            except Exception as e:
                print(f"[Runner] An unexpected error occurred during git pull: {e}", file=sys.stderr)
            print() # Add a newline for spacing
        # ============================

        # Check for mode override before running the bot
        override_mode = check_mode_override()
        if override_mode:
            new_gemini = (override_mode == "gemini")
            if new_gemini != gemini_mode:
                old_mode = "Gemini" if gemini_mode else "Claude"
                new_mode = "Gemini" if new_gemini else "Claude"
                print(f"[Runner] Mode switch detected: {old_mode} -> {new_mode}")
                gemini_mode = new_gemini

        exit_code = run_bot(args, env_file, gemini_mode)

        if exit_code == RESTART_CODE:
            restart_count += 1
            print()
            print(f"[Runner] Restart requested (restart #{restart_count})")
            print("[Runner] Waiting 3 seconds before restart...")
            time.sleep(3)
            print()
        else:
            print()
            print(f"[Runner] Bot exited with code {exit_code}")
            print("[Runner] Stopping runner")
            sys.exit(exit_code)


if __name__ == "__main__":
    main()
