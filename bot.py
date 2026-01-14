#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thoth Agent - A stateful AI assistant built on Claude Agent SDK + Letta Memory + Discord
Inspired by Strix: https://timkellogg.me/blog/2025/05/23/strix

v2.8 - Fixed multimodal image handling

Key insight from Strix: "Replies as tools" - the agent explicitly calls send_message
when it wants to communicate, rather than just outputting text.

Usage:
    python bot.py                    # Default: Discord + HTTP server (Claude mode)
    python bot.py discord            # Discord only (Claude mode)
    python bot.py gemini discord     # Discord only (Gemini mode)
    python bot.py cli                # CLI mode (Claude)
    python bot.py gemini cli         # CLI mode (Gemini)
    python bot.py --debug discord    # With debug logging
"""

import asyncio
import base64
import json
import os
import re
import subprocess
import sys
import aiohttp
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field

import anyio
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

# -----------------------------------------------------------------------------
# UTF-8 / Windows console friendliness
# -----------------------------------------------------------------------------
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

if sys.platform.startswith("win"):
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# -----------------------------------------------------------------------------
# Load .env early
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent

try:
    from dotenv import load_dotenv
except ImportError:
    raise RuntimeError("python-dotenv is not installed. Run: pip install python-dotenv")

ENV_FILE = Path(os.getenv("THOTH_ENV_FILE", str(BASE_DIR / ".env")))
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE, override=False)
else:
    load_dotenv(override=False)

# Import Claude Agent SDK
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    tool,
    create_sdk_mcp_server,
)

# Import local utils
from git_utils import git_add, git_commit, git_push, GitError

# =============================================================================
# Configuration
# =============================================================================

STATE_DIR = BASE_DIR / "state"
LOGS_DIR = BASE_DIR / "logs"
UPLOADS_DIR = BASE_DIR / "uploads"
CLAUDE_MD = BASE_DIR / "CLAUDE.md"
GEMINI_MD = BASE_DIR / "GEMINI.md"

# Restart mode file - used for mode switching across restarts
RESTART_MODE_FILE = STATE_DIR / "restart_mode.txt"

# Wake-up context file - stores context for post-restart wake-up
WAKEUP_CONTEXT_FILE = STATE_DIR / "wakeup_context.json"

# Letta configuration
LETTA_BASE_URL = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
LETTA_AGENT_ID = os.getenv("LETTA_AGENT_ID", "")

# Discord configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")

# Mode configuration (set by command-line args)
DEBUG = os.getenv("THOTH_DEBUG", "false").lower() in ("true", "1", "yes")
GEMINI_MODE = False

# Ensure directories exist
STATE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)


def debug_log(msg: str):
    """Print debug message with timestamp if DEBUG is enabled."""
    if DEBUG:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")


# =============================================================================
# Message Queue - Collects tool outputs for batch sending
# =============================================================================

@dataclass
class MessageQueue:
    """Queue for messages/reactions/images to send after agent completes."""
    messages: List[str] = field(default_factory=list)
    reactions: List[str] = field(default_factory=list)
    images: List[dict] = field(default_factory=list)

    def clear(self):
        self.messages.clear()
        self.reactions.clear()
        self.images.clear()

    def has_content(self) -> bool:
        return bool(self.messages or self.reactions or self.images)


message_queue = MessageQueue()
_restart_requested = False

# Store current Discord context for wake-up
_current_discord_context: Optional[dict] = None
_current_channel_id: Optional[str] = None


# =============================================================================
# Wake-up Context Management
# =============================================================================

def save_wakeup_context(
        channel_id: str,
        user: str,
        last_prompt: str,
        mode: str,
        reason: str = "restart"
):
    """Save context before restart so the agent can wake up with context."""
    context = {
        "channel_id": channel_id,
        "user": user,
        "last_prompt": last_prompt[:500],  # Truncate to avoid huge files
        "mode": mode,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    try:
        WAKEUP_CONTEXT_FILE.write_text(json.dumps(context, indent=2), encoding="utf-8")
        debug_log(f"Saved wake-up context: {context}")
    except Exception as e:
        debug_log(f"Error saving wake-up context: {e}")


def load_wakeup_context() -> Optional[dict]:
    """Load and delete wake-up context if it exists."""
    if not WAKEUP_CONTEXT_FILE.exists():
        return None

    try:
        context = json.loads(WAKEUP_CONTEXT_FILE.read_text(encoding="utf-8"))
        WAKEUP_CONTEXT_FILE.unlink()  # Delete after reading
        debug_log(f"Loaded wake-up context: {context}")
        return context
    except Exception as e:
        debug_log(f"Error loading wake-up context: {e}")
        return None


# =============================================================================
# Tool Logic (callable by both Claude and Gemini)
# =============================================================================

async def _send_message(args):
    """Queue a message to send to the user."""
    message = args.get("message", "")
    if message:
        message_queue.messages.append(message)
    return {"content": [{"type": "text", "text": f"Message queued ({len(message)} chars)"}]}


async def _react(args):
    """Queue an emoji reaction."""
    emoji = args.get("emoji", "👍")
    message_queue.reactions.append(emoji)
    return {"content": [{"type": "text", "text": f"Reaction '{emoji}' queued"}]}


async def _send_image(args):
    """Queue an image to send."""
    image_path = args.get("image_path", "")
    caption = args.get("caption", "")
    if not image_path:
        return {"content": [{"type": "text", "text": "Error: No image path provided"}]}

    path = Path(image_path)
    if not path.is_absolute():
        path = BASE_DIR / image_path

    if not path.exists():
        return {"content": [{"type": "text", "text": f"Error: Image not found at {path}"}]}

    message_queue.images.append({"path": str(path), "caption": caption})
    return {"content": [{"type": "text", "text": f"Image queued: {path.name}"}]}


async def _restart_self(args):
    """
    Request a restart. Can optionally switch between Claude and Gemini modes.
    Saves wake-up context so the agent remembers what it was doing.
    """
    global _restart_requested
    _restart_requested = True
    mode = args.get("mode", "").lower().strip()
    reason = args.get("reason", "restart requested")

    # Determine target mode
    target_mode = mode if mode in ("claude", "gemini") else ("gemini" if GEMINI_MODE else "claude")

    # Save wake-up context
    if _current_channel_id and _current_discord_context:
        save_wakeup_context(
            channel_id=_current_channel_id,
            user=_current_discord_context.get("user", "unknown"),
            last_prompt=_current_discord_context.get("last_prompt", ""),
            mode=target_mode,
            reason=reason,
        )

    if mode in ("claude", "gemini"):
        try:
            RESTART_MODE_FILE.write_text(mode, encoding="utf-8")
            debug_log(f"Set restart mode to '{mode}' in {RESTART_MODE_FILE}")
            return {"content": [{"type": "text",
                                 "text": f"Restart requested. Switching to {mode.upper()} mode. Context saved for wake-up."}]}
        except Exception as e:
            debug_log(f"Error setting restart mode: {e}")
            return {"content": [{"type": "text", "text": f"Restart requested, but error setting mode: {e}"}]}

    return {"content": [{"type": "text", "text": "Restart requested. Context saved for wake-up."}]}


async def _apply_update(args):
    """Write new content to bot.py and trigger restart."""
    global _restart_requested
    new_content = args.get("new_content", "")
    if not new_content:
        return {"content": [{"type": "text", "text": "Error: No content provided"}]}

    bot_path = BASE_DIR / "bot.py"
    backup_path = bot_path.with_suffix(".py.backup")

    try:
        # Create backup
        if bot_path.exists():
            backup_path.write_text(bot_path.read_text(encoding="utf-8"), encoding="utf-8")

        # Write new content
        bot_path.write_text(new_content, encoding="utf-8")
        _restart_requested = True

        # Save wake-up context for code updates
        if _current_channel_id and _current_discord_context:
            save_wakeup_context(
                channel_id=_current_channel_id,
                user=_current_discord_context.get("user", "unknown"),
                last_prompt=_current_discord_context.get("last_prompt", ""),
                mode="gemini" if GEMINI_MODE else "claude",
                reason="apply_update",
            )

        return {"content": [
            {"type": "text", "text": f"Update applied ({len(new_content)} bytes). Backup saved. Restart requested."}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error applying update: {e}"}]}


async def _read_file(args):
    """Read a file from the project directory."""
    file_path = args.get("path", "") or args.get("file_path", "")
    if not file_path:
        return {"content": [{"type": "text", "text": "Error: No file path provided"}]}

    path = Path(file_path)
    if not path.is_absolute():
        path = BASE_DIR / file_path

    if not path.exists():
        return {"content": [{"type": "text", "text": f"Error: File not found at {path}"}]}

    try:
        content = path.read_text(encoding="utf-8")
        return {"content": [{"type": "text", "text": f"File contents of {path.name}:\n\n{content}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error reading file: {e}"}]}


async def _write_file(args):
    """Write content to a file in the project directory."""
    file_path = args.get("path", "") or args.get("file_path", "")
    content = args.get("content", "")

    if not file_path:
        return {"content": [{"type": "text", "text": "Error: No file path provided"}]}

    path = Path(file_path)
    if not path.is_absolute():
        path = BASE_DIR / file_path

    try:
        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"content": [{"type": "text", "text": f"Successfully wrote {len(content)} bytes to {path.name}"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error writing file: {e}"}]}


async def _git_add(args):
    """Stage files for commit."""
    files = args.get("files", [])
    # Handle string input (single file)
    if isinstance(files, str):
        files = [files]
    if not isinstance(files, list) or not files:
        return {"content": [{"type": "text", "text": "Error: 'files' must be a non-empty list of strings."}]}
    try:
        git_add(files=files)
        return {"content": [{"type": "text", "text": f"Staged {len(files)} file(s): {', '.join(files)}"}]}
    except GitError as e:
        return {"content": [{"type": "text", "text": f"Error staging files: {e}"}]}


async def _git_commit(args):
    """Commit staged files."""
    message = args.get("message", "")
    if not message:
        return {"content": [{"type": "text", "text": "Error: A commit message is required."}]}
    try:
        commit_sha = git_commit(message=message)
        return {"content": [{"type": "text", "text": f"Committed changes. New commit SHA: {commit_sha}"}]}
    except GitError as e:
        return {"content": [{"type": "text", "text": f"Error committing: {e}"}]}


async def _git_push(args):
    """Push commits to the remote repository."""
    try:
        push_output = git_push()
        return {"content": [{"type": "text", "text": f"Successfully pushed to remote.\nOutput:\n{push_output}"}]}
    except GitError as e:
        return {"content": [{"type": "text", "text": f"Error pushing to remote: {e}"}]}


# =============================================================================
# MCP Tool Wrappers (for Claude Agent SDK)
# =============================================================================

@tool("send_message", "Send a message to the user via Discord.", {"message": str})
async def send_message_tool(args):
    return await _send_message(args)


@tool("react", "React to the user's message with an emoji.", {"emoji": str})
async def react_tool(args):
    return await _react(args)


@tool("send_image", "Send an image file to Discord.", {"image_path": str, "caption": str})
async def send_image_tool(args):
    return await _send_image(args)


@tool("restart_self", "Restart the Thoth agent. Optionally switch between Claude and Gemini modes.",
      {"mode": str, "reason": str})
async def restart_self_tool(args):
    return await _restart_self(args)


@tool("apply_update", "Apply an update to bot.py source code and restart.", {"new_content": str})
async def apply_update_tool(args):
    return await _apply_update(args)


@tool("git_add", "Stage one or more files for the next commit.", {"files": List[str]})
async def git_add_tool(args):
    return await _git_add(args)


@tool("git_commit", "Commit the staged files with a message.", {"message": str})
async def git_commit_tool(args):
    return await _git_commit(args)


@tool("git_push", "Push committed changes to the remote repository.", {})
async def git_push_tool(args):
    return await _git_push(args)


# Create MCP server with Discord tools (for Claude Agent SDK)
discord_tools_server = create_sdk_mcp_server(
    name="discord",
    version="1.0.0",
    tools=[
        send_message_tool, react_tool, send_image_tool,
        restart_self_tool, apply_update_tool,
        git_add_tool, git_commit_tool, git_push_tool
    ],
)


# =============================================================================
# File/Image Handling
# =============================================================================

async def download_discord_attachment(url: str, filename: str) -> Optional[Path]:
    """Download a Discord attachment to the uploads directory."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{filename}"
        save_path = UPLOADS_DIR / safe_filename

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    save_path.write_bytes(await response.read())
                    debug_log(f"Downloaded attachment: {save_path}")
                    return save_path
        return None
    except Exception as e:
        debug_log(f"Download error: {e}")
        return None


def is_image_file(path: Path) -> bool:
    """Check if file is an image based on extension."""
    return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}


def get_image_media_type(path: Path) -> str:
    """Get MIME type for image file."""
    suffix = path.suffix.lower().lstrip('.')
    if suffix == "jpg":
        suffix = "jpeg"
    return f"image/{suffix}"


def image_to_base64(path: Path) -> Optional[str]:
    """Convert image file to base64 string."""
    try:
        return base64.b64encode(path.read_bytes()).decode("utf-8")
    except Exception as e:
        debug_log(f"Base64 encoding error: {e}")
        return None


# =============================================================================
# Letta Memory & Journal
# =============================================================================

def get_letta_client():
    """Get Letta client instance."""
    try:
        from letta_client import Letta
        return Letta(base_url=LETTA_BASE_URL)
    except ImportError:
        debug_log("letta_client not installed")
        return None
    except Exception as e:
        debug_log(f"Letta client error: {e}")
        return None


def get_letta_memory_blocks() -> dict[str, str]:
    """Fetch memory blocks from Letta agent."""
    if not LETTA_AGENT_ID:
        debug_log("No LETTA_AGENT_ID configured")
        return {}

    client = get_letta_client()
    if not client:
        return {}

    try:
        blocks = client.agents.blocks.list(agent_id=LETTA_AGENT_ID)
        memory = {block.label: block.value for block in blocks}
        debug_log(f"Loaded {len(memory)} Letta memory blocks")
        return memory
    except Exception as e:
        debug_log(f"Letta memory fetch error: {e}")
        return {}


def write_journal(entry: dict):
    """Append an entry to the journal log."""
    journal_path = LOGS_DIR / "journal.jsonl"
    entry["t"] = datetime.now(timezone.utc).isoformat()

    with open(journal_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_recent_journal(n: int = 40) -> list[dict]:
    """Read the most recent journal entries."""
    journal_path = LOGS_DIR / "journal.jsonl"
    if not journal_path.exists():
        return []

    try:
        with open(journal_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-n:]
        return [json.loads(line) for line in lines if line.strip()]
    except Exception as e:
        debug_log(f"Journal read error: {e}")
        return []


# =============================================================================
# Claude Mode - System Prompt Builder
# =============================================================================

def build_claude_system_prompt(
        discord_context: Optional[dict] = None,
        include_discord_tools: bool = False
) -> str:
    """Build the system prompt with injected context from Letta + local state."""

    # Load base prompt from CLAUDE.md
    if CLAUDE_MD.exists():
        base_prompt = CLAUDE_MD.read_text(encoding='utf-8')
    else:
        base_prompt = "You are Thoth, a helpful stateful assistant."

    # Add Discord-specific instructions when in Discord mode
    if include_discord_tools:
        discord_instructions = """

## Discord Communication

You have tools for communicating via Discord:

1. **send_message** - Send a text message. Call when you have something to say.
2. **react** - Add an emoji reaction (👍 ✅ 👀 🤔 ❤️)
3. **send_image** - Send an image file with optional caption
4. **restart_self** - Restart yourself, optionally switching modes (claude/gemini)

**Important**: Your internal thinking is NOT sent to Discord automatically.
Only content you explicitly send via tools will reach the user.

## Images

You can SEE images that the user sends you - they appear as visual input.
Describe what you see, answer questions, analyze screenshots, etc.
Images are also saved to `uploads/` directory for later reference.

To send an image back, use send_image with a path like `uploads/filename.jpg`

## Mode Switching

You can switch between Claude and Gemini modes:
- restart_self(mode="gemini") - Switch to Gemini mode
- restart_self(mode="claude") - Switch to Claude mode  
- restart_self() - Restart in current mode

## Git Tools

You have git tools for self-modification:
- git_add(files=["file1.py"]) - Stage files
- git_commit(message="...") - Commit staged files
- git_push() - Push to remote
"""
        base_prompt += discord_instructions

    # Inject Letta memory blocks
    letta_memory = get_letta_memory_blocks()
    if letta_memory:
        memory_text = "\n\n<letta_memory>\n"
        for label, value in letta_memory.items():
            memory_text += f"<{label}>\n{value}\n</{label}>\n"
        memory_text += "</letta_memory>"
        base_prompt += memory_text

    # Inject recent journal entries
    journal_entries = read_recent_journal(40)
    if journal_entries:
        journal_text = "\n\n<recent_journal>\n"
        for entry in journal_entries:
            journal_text += json.dumps(entry, ensure_ascii=False) + "\n"
        journal_text += "</recent_journal>"
        base_prompt += journal_text

    # Inject Discord context if present
    if discord_context:
        discord_text = f"\n\n<discord_context>\n"
        discord_text += f"Channel: {discord_context.get('channel', 'unknown')}\n"
        discord_text += f"User: {discord_context.get('user', 'unknown')}\n"
        if discord_context.get('recent_messages'):
            discord_text += "Recent messages:\n"
            for msg in discord_context['recent_messages']:
                discord_text += f"  {msg['author']}: {msg['content']}\n"
        discord_text += "</discord_context>"
        base_prompt += discord_text

    # Inject current time
    now = datetime.now(timezone.utc)
    time_context = f"\n\nCurrent UTC time: {now.isoformat()}"
    base_prompt += time_context

    return base_prompt


# =============================================================================
# Gemini Mode - Prompt Builder
# =============================================================================

def build_gemini_prompt(
        user_prompt: str,
        discord_context: Optional[dict] = None,
        images: Optional[List[dict]] = None
) -> str:
    """Build the full prompt for Gemini CLI mode."""

    # Base system prompt from GEMINI.md or default
    if GEMINI_MD.exists():
        system_prompt = GEMINI_MD.read_text(encoding='utf-8')
    else:
        system_prompt = """You are Thoth, a helpful AI assistant running in Gemini mode.
You have persistent memory from past conversations via Letta.

## CRITICAL: How Tools Work

You do NOT have native function calling. Instead, you must PRINT tool commands as literal text.
The bot.py script will parse your text output and execute the tools.

To use a tool, write this EXACT syntax in your response:
[TOOL: tool_name(param="value")]

## Available Tools

Communication:
- [TOOL: send_message(message="Your message here")] - REQUIRED to send any response to user
- [TOOL: react(emoji="👍")] - React with emoji
- [TOOL: send_image(image_path="path/to/image.png", caption="optional")]

System:
- [TOOL: restart_self()] - Restart in current mode
- [TOOL: restart_self(mode="claude")] - Switch to Claude mode
- [TOOL: restart_self(mode="gemini")] - Switch to Gemini mode

File Operations:
- [TOOL: read_file(path="bot.py")] - Read a file
- [TOOL: write_file(path="test.txt", content="file contents")] - Write a file
- [TOOL: apply_update(new_content="...")] - Update bot.py (DANGEROUS - ask first!)

Git (for self-modification):
- [TOOL: git_add(files="bot.py")] - Stage a file (use quotes, not brackets)
- [TOOL: git_commit(message="Your commit message")] - Commit staged files
- [TOOL: git_push()] - Push to remote

## IMPORTANT RULES

1. Your raw text is NOT sent to Discord. You MUST use send_message for ALL responses.
2. NEVER use apply_update without explicit permission from the user.
3. ALWAYS describe what you plan to do BEFORE modifying any files.
4. For git_add, use files="filename.py" (string), not files=["filename.py"] (array)

## Example Response

User asks "Hello, how are you?"

Your response should be:
I'm doing well! Let me respond to the user.
[TOOL: send_message(message="Hello! I'm doing great, thank you for asking. How can I help you today?")]

## Example: Git Workflow

User asks to commit changes:

[TOOL: send_message(message="I'll commit the changes now.")]
[TOOL: git_add(files="bot.py")]
[TOOL: git_commit(message="Update bot.py with new feature")]
[TOOL: git_push()]
[TOOL: send_message(message="Done! Changes have been committed and pushed.")]
"""

    # Inject Letta memory blocks
    letta_memory = get_letta_memory_blocks()
    if letta_memory:
        memory_text = "\n\n<letta_memory>\n"
        for label, value in letta_memory.items():
            memory_text += f"<{label}>\n{value}\n</{label}>\n"
        memory_text += "</letta_memory>"
        system_prompt += memory_text

    # Inject recent journal entries
    journal_entries = read_recent_journal(40)
    if journal_entries:
        journal_text = "\n\n<recent_journal>\n"
        for entry in journal_entries:
            journal_text += json.dumps(entry, ensure_ascii=False) + "\n"
        journal_text += "</recent_journal>"
        system_prompt += journal_text

    # Inject Discord context if present
    if discord_context:
        discord_text = f"\n\n<discord_context>\n"
        discord_text += f"Channel: {discord_context.get('channel', 'unknown')}\n"
        discord_text += f"User: {discord_context.get('user', 'unknown')}\n"
        if discord_context.get('recent_messages'):
            discord_text += "Recent messages:\n"
            for msg in discord_context['recent_messages']:
                discord_text += f"  {msg['author']}: {msg['content']}\n"
        discord_text += "</discord_context>"
        system_prompt += discord_text

    # Add image attachment info
    if images:
        attachments = "\n\n<attachments>\n"
        for img in images:
            attachments += f"- Image: {img.get('path', 'unknown')}\n"
        attachments += "</attachments>"
        system_prompt += attachments

    # Inject current time
    now = datetime.now(timezone.utc)
    system_prompt += f"\n\nCurrent UTC time: {now.isoformat()}"

    # Add user prompt
    return f"{system_prompt}\n\n---\nUser message: {user_prompt}"


# =============================================================================
# Gemini Tool Argument Parser
# =============================================================================

def parse_gemini_tool_args(call_str: str) -> dict:
    """
    Parse tool arguments from a Gemini tool call string.
    Handles both simple strings and JSON-like arrays.
    """
    args = {}

    # Try to find arguments in parentheses
    paren_match = re.search(r'\((.+)\)', call_str)
    if not paren_match:
        return args

    args_str = paren_match.group(1)

    # Pattern for key="value" or key='value'
    string_pattern = r'(\w+)\s*=\s*["\']([^"\']*)["\']'

    # Pattern for key=[...] (array)
    array_pattern = r'(\w+)\s*=\s*\[([^\]]*)\]'

    # First, extract arrays
    for match in re.finditer(array_pattern, args_str):
        key = match.group(1)
        array_content = match.group(2)
        items = re.findall(r'["\']([^"\']+)["\']', array_content)
        args[key] = items

    # Then extract simple string values (that weren't part of arrays)
    for match in re.finditer(string_pattern, args_str):
        key = match.group(1)
        if key not in args:
            args[key] = match.group(2)

    return args


# =============================================================================
# Claude Agent Invocation
# =============================================================================

async def invoke_claude_agent(
        prompt: str,
        trigger_source: str,
        discord_context: Optional[dict] = None,
        use_discord_tools: bool = False,
        images: Optional[List[dict]] = None,
) -> str:
    """
    Invoke the Claude Agent SDK to process a prompt.
    """
    global _current_discord_context
    message_queue.clear()

    # Store context for wake-up
    if discord_context:
        _current_discord_context = discord_context.copy()
        _current_discord_context["last_prompt"] = prompt

    debug_log(f"═══════════════════════════════════════════════════════")
    debug_log(f"AGENT INVOCATION - Source: {trigger_source}")
    debug_log(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    if images:
        debug_log(f"Images attached: {len(images)}")
    debug_log(f"═══════════════════════════════════════════════════════")

    # Build system prompt
    system_prompt = build_claude_system_prompt(
        discord_context=discord_context,
        include_discord_tools=use_discord_tools
    )

    debug_log(f"System prompt length: {len(system_prompt)} chars")

    # Base tools
    allowed_tools = [
        "Read",
        "Write",
        "Edit",
        "Bash",
        "Glob",
        "Grep",
        "WebFetch",
        "WebSearch",
    ]

    # MCP servers config
    mcp_servers = {}

    # Add Discord tools if in Discord mode
    if use_discord_tools:
        mcp_servers["discord"] = discord_tools_server
        allowed_tools.extend([
            "mcp__discord__send_message",
            "mcp__discord__react",
            "mcp__discord__send_image",
            "mcp__discord__restart_self",
            "mcp__discord__apply_update",
            "mcp__discord__git_add",
            "mcp__discord__git_commit",
            "mcp__discord__git_push",
        ])
        debug_log(f"Discord tools enabled")

    debug_log(f"Allowed tools: {allowed_tools}")

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        cwd=str(BASE_DIR),
        allowed_tools=allowed_tools,
        mcp_servers=mcp_servers if mcp_servers else None,
        permission_mode="acceptEdits",
        max_turns=30,
    )

    response_text = ""
    tool_uses = []

    def process_message(msg):
        """Process a single message from the agent."""
        nonlocal response_text

        debug_log(f"───────────────────────────────────────────")
        debug_log(f"Message type: {type(msg).__name__}")

        if isinstance(msg, AssistantMessage):
            for block in msg.content:
                if isinstance(block, TextBlock):
                    debug_log(f"📝 TEXT: {block.text[:200]}{'...' if len(block.text) > 200 else ''}")
                    response_text += block.text
                elif isinstance(block, ToolUseBlock):
                    debug_log(f"🔧 TOOL CALL: {block.name}")
                    debug_log(f"   Input: {json.dumps(block.input, indent=2)[:300]}")
                    tool_uses.append({
                        "tool": block.name,
                        "input": block.input
                    })
                elif isinstance(block, ToolResultBlock):
                    result_preview = str(block)[:200]
                    debug_log(f"📤 TOOL RESULT: {result_preview}")
                else:
                    debug_log(f"❓ OTHER BLOCK: {type(block).__name__}")
        else:
            debug_log(f"📨 {type(msg).__name__}: {str(msg)[:200]}")

    try:
        async with ClaudeSDKClient(options=options) as client:
            # Build query content
            if images:
                content_parts = []
                for img in images:
                    content_parts.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": img["media_type"],
                            "data": img["base64"]
                        }
                    })
                content_parts.append({"type": "text", "text": prompt})
                debug_log(f"Sending multimodal query with {len(images)} image(s)")
                await client.query(content_parts)
            else:
                await client.query(prompt)

            # Get response - handle both async iterator and list
            response = client.receive_response()

            # Check if it's a list or async iterator
            if isinstance(response, list):
                # It's already a list, iterate normally
                debug_log(f"Response is a list with {len(response)} messages")
                for msg in response:
                    process_message(msg)
            else:
                # It's an async iterator
                debug_log(f"Response is an async iterator")
                async for msg in response:
                    process_message(msg)

    except Exception as e:
        error_msg = f"Agent error: {type(e).__name__}: {e}"
        debug_log(f"❌ ERROR: {error_msg}")
        import traceback
        debug_log(f"Traceback: {traceback.format_exc()}")
        message_queue.messages.append(f"Sorry, I encountered an error: {e}")
        write_journal({
            "type": "error",
            "mode": "claude",
            "trigger": trigger_source,
            "error": error_msg,
        })
        return error_msg

    debug_log(f"═══════════════════════════════════════════════════════")
    debug_log(f"INVOCATION COMPLETE")
    debug_log(f"  Tools used: {[t['tool'] for t in tool_uses]}")
    debug_log(f"  Messages queued: {len(message_queue.messages)}")
    debug_log(f"  Images queued: {len(message_queue.images)}")
    debug_log(f"  Reactions queued: {message_queue.reactions}")
    debug_log(f"═══════════════════════════════════════════════════════")

    write_journal({
        "type": "invocation",
        "mode": "claude",
        "trigger": trigger_source,
        "prompt_preview": prompt[:100],
        "tools_used": [t["tool"] for t in tool_uses],
        "messages_queued": len(message_queue.messages),
        "images_queued": len(message_queue.images),
        "reactions_queued": len(message_queue.reactions),
        "response_preview": response_text[:200] if response_text else "(no text response)",
    })

    return response_text


# =============================================================================
# Gemini Agent Invocation
# =============================================================================

async def invoke_gemini_agent(
        prompt: str,
        trigger_source: str,
        discord_context: Optional[dict] = None,
        images: Optional[List[dict]] = None,
        **kwargs,
) -> str:
    """
    Invoke the Gemini CLI to process a prompt.
    """
    global _current_discord_context
    message_queue.clear()

    # Store context for wake-up
    if discord_context:
        _current_discord_context = discord_context.copy()
        _current_discord_context["last_prompt"] = prompt

    debug_log(f"Invoking Gemini Agent (trigger: {trigger_source})")

    # Build full prompt with memory context
    full_prompt = build_gemini_prompt(
        user_prompt=prompt,
        discord_context=discord_context,
        images=images,
    )

    debug_log(f"Gemini prompt length: {len(full_prompt)} chars")

    try:
        # Gemini CLI path - hardcoded for Windows
        if sys.platform.startswith("win"):
            gemini_cmd = r"C:\Users\Mike\AppData\Roaming\npm\gemini.cmd"
        else:
            gemini_cmd = "gemini"

        # Call Gemini CLI (no timeout)
        process = await asyncio.create_subprocess_exec(
            gemini_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate(input=full_prompt.encode('utf-8'))

        if process.returncode != 0:
            error_msg = stderr.decode('utf-8', errors='replace')
            raise RuntimeError(f"Gemini CLI exited with code {process.returncode}: {error_msg}")

        response_text = stdout.decode('utf-8', errors='replace')
        debug_log(f"Gemini raw output: {len(response_text)} chars")

        # Parse and execute tool calls
        tool_pattern = r'\[TOOL:\s*([^\]]+)\]'
        tool_calls = re.findall(tool_pattern, response_text)
        tools_used = []

        for call_str in tool_calls:
            tool_name_match = re.match(r'(\w+)', call_str)
            if not tool_name_match:
                continue

            tool_name = tool_name_match.group(1)
            tools_used.append(tool_name)

            args = parse_gemini_tool_args(call_str)

            debug_log(f"Executing tool: {tool_name}({args})")

            if tool_name == "send_message":
                await _send_message(args)
            elif tool_name == "react":
                await _react(args)
            elif tool_name == "send_image":
                await _send_image(args)
            elif tool_name == "restart_self":
                await _restart_self(args)
            elif tool_name == "apply_update":
                await _apply_update(args)
            elif tool_name == "read_file":
                result = await _read_file(args)
                debug_log(f"read_file result: {str(result)[:200]}")
            elif tool_name == "write_file":
                await _write_file(args)
            elif tool_name == "git_add":
                await _git_add(args)
            elif tool_name == "git_commit":
                await _git_commit(args)
            elif tool_name == "git_push":
                await _git_push(args)
            else:
                debug_log(f"Unknown tool: {tool_name}")

        # Remove tool calls from response text
        clean_text = re.sub(tool_pattern, '', response_text).strip()

        # If there's remaining text and no send_message was called, queue it
        if clean_text and not any(t == "send_message" for t in tools_used):
            if len(clean_text) > 10:
                message_queue.messages.append(clean_text)

        # Log to journal
        write_journal({
            "type": "invocation",
            "mode": "gemini",
            "trigger": trigger_source,
            "prompt_preview": prompt[:100],
            "tools_used": tools_used,
            "messages_queued": len(message_queue.messages),
            "response_preview": clean_text[:200] if clean_text else "",
        })

        return clean_text

    except FileNotFoundError:
        error_msg = "Gemini CLI not found. Please ensure 'gemini' is in your PATH."
        debug_log(error_msg)
        message_queue.messages.append(error_msg)
        write_journal({"type": "error", "mode": "gemini", "trigger": trigger_source, "error": error_msg})
        return error_msg

    except Exception as e:
        error_msg = f"Gemini error: {e}"
        debug_log(error_msg)
        message_queue.messages.append(f"Sorry, I encountered an error: {e}")
        write_journal({"type": "error", "mode": "gemini", "trigger": trigger_source, "error": str(e)})
        return error_msg


# =============================================================================
# Unified Agent Dispatcher
# =============================================================================

async def invoke_agent(
        prompt: str,
        trigger_source: str,
        discord_context: Optional[dict] = None,
        use_discord_tools: bool = False,
        images: Optional[List[dict]] = None,
) -> str:
    """
    Unified dispatcher that routes to Claude or Gemini based on GEMINI_MODE.
    """
    if GEMINI_MODE:
        return await invoke_gemini_agent(
            prompt=prompt,
            trigger_source=trigger_source,
            discord_context=discord_context,
            images=images,
        )
    else:
        return await invoke_claude_agent(
            prompt=prompt,
            trigger_source=trigger_source,
            discord_context=discord_context,
            use_discord_tools=use_discord_tools,
            images=images,
        )


# =============================================================================
# Discord Bot
# =============================================================================

discord_client = None


def setup_discord():
    """Set up Discord bot if token is configured."""
    global discord_client, _current_channel_id

    if not DISCORD_TOKEN:
        print("Discord: No token configured (set DISCORD_TOKEN env var)")
        return None

    try:
        import discord
        from discord import Intents, File

        intents = Intents.default()
        intents.message_content = True

        discord_client = discord.Client(intents=intents)

        @discord_client.event
        async def on_ready():
            global _current_channel_id
            mode_str = "Gemini" if GEMINI_MODE else "Claude"
            print(f"Discord: Logged in as {discord_client.user} (Mode: {mode_str})")
            print(f"📷 Image vision enabled!")

            # Check for wake-up context
            wakeup_context = load_wakeup_context()
            if wakeup_context:
                print(f"🌅 Wake-up context found! Reason: {wakeup_context.get('reason', 'unknown')}")

                try:
                    channel_id = wakeup_context.get("channel_id")
                    if channel_id:
                        channel = discord_client.get_channel(int(channel_id))
                        if channel is None:
                            channel = await discord_client.fetch_channel(int(channel_id))

                        if channel:
                            _current_channel_id = channel_id

                            # Build wake-up prompt
                            reason = wakeup_context.get("reason", "restart")
                            user = wakeup_context.get("user", "unknown")
                            last_prompt = wakeup_context.get("last_prompt", "")
                            prev_mode = wakeup_context.get("mode", "unknown")

                            wakeup_prompt = f"""You have just restarted. Here is the context:
- Reason: {reason}
- Previous mode: {prev_mode}
- Current mode: {'Gemini' if GEMINI_MODE else 'Claude'}
- User who triggered: {user}
- Last prompt before restart: {last_prompt[:200] if last_prompt else 'N/A'}

Please acknowledge that you have restarted and are now online. If mode was switched, mention the new mode. Be brief."""

                            discord_context = {
                                "channel": getattr(channel, 'name', 'DM'),
                                "user": user,
                                "recent_messages": [],
                            }

                            debug_log(f"Sending wake-up prompt to channel {channel_id}")

                            # Show typing while processing wake-up
                            async with channel.typing():
                                await invoke_agent(
                                    prompt=wakeup_prompt,
                                    trigger_source="wakeup",
                                    discord_context=discord_context,
                                    use_discord_tools=True,
                                )

                            # Send queued messages
                            for msg_content in message_queue.messages:
                                if msg_content:
                                    chunks = [msg_content[i:i + 1900] for i in range(0, len(msg_content), 1900)]
                                    for chunk in chunks:
                                        try:
                                            await channel.send(chunk)
                                        except Exception as e:
                                            print(f"Failed to send wake-up message: {e}")

                            message_queue.clear()
                            print(f"🌅 Wake-up complete!")
                        else:
                            print(f"Could not find channel {channel_id}")
                except Exception as e:
                    print(f"Error during wake-up: {e}")

        @discord_client.event
        async def on_message(message):
            global _restart_requested, _current_channel_id

            # Don't respond to ourselves
            if message.author == discord_client.user:
                return

            # Optional: limit to specific channel
            if DISCORD_CHANNEL_ID and str(message.channel.id) != DISCORD_CHANNEL_ID:
                return

            # Check if bot is mentioned or it's a DM
            is_mentioned = discord_client.user in message.mentions
            is_dm = isinstance(message.channel, discord.DMChannel)

            if not (is_mentioned or is_dm):
                return

            # Store current channel for wake-up context
            _current_channel_id = str(message.channel.id)

            # Clean the message content (remove mention)
            content = message.content
            if is_mentioned:
                content = content.replace(f'<@{discord_client.user.id}>', '').strip()

            if not content and not message.attachments:
                content = "Hello!"

            # Process attachments
            images = []
            text_attachments = []

            for attachment in message.attachments:
                debug_log(f"📎 Attachment: {attachment.filename} ({attachment.content_type})")

                file_path = await download_discord_attachment(attachment.url, attachment.filename)
                if not file_path:
                    continue

                if is_image_file(file_path):
                    base64_data = image_to_base64(file_path)
                    if base64_data:
                        images.append({
                            "path": str(file_path),
                            "media_type": get_image_media_type(file_path),
                            "base64": base64_data
                        })
                        debug_log(f"🖼️ Image ready for vision: {file_path.name}")

                elif file_path.suffix.lower() in {'.py', '.txt', '.md', '.json', '.yaml', '.yml',
                                                  '.toml', '.cfg', '.ini', '.sh', '.html', '.css',
                                                  '.js', '.ts', '.jsx', '.tsx', '.sql', '.xml', '.csv'}:
                    try:
                        text_content = file_path.read_text(encoding='utf-8')
                        text_attachments.append({
                            "filename": attachment.filename,
                            "path": str(file_path),
                            "content": text_content
                        })
                        debug_log(f"📄 Text file read: {file_path.name} ({len(text_content)} chars)")
                    except Exception as e:
                        debug_log(f"Error reading text file: {e}")

                else:
                    text_attachments.append({
                        "filename": attachment.filename,
                        "path": str(file_path),
                        "content": None
                    })
                    debug_log(f"📦 Binary file saved: {file_path.name}")

            if text_attachments:
                content += "\n\n<attachments>\n"
                for att in text_attachments:
                    content += f"File: {att['filename']}\n"
                    content += f"Path: {att['path']}\n"
                    if att['content']:
                        file_content = att['content'][:50000]
                        if len(att['content']) > 50000:
                            file_content += "\n... (truncated)"
                        content += f"Content:\n```\n{file_content}\n```\n"
                    content += "\n"
                content += "</attachments>\n"

            if images and not content.strip():
                content = "I'm sending you an image. Please look at it and describe what you see."

            recent_messages = []
            try:
                async for msg in message.channel.history(limit=5):
                    if msg.id != message.id:
                        recent_messages.append({
                            "author": msg.author.display_name,
                            "content": msg.content[:200]
                        })
                recent_messages.reverse()
            except:
                pass

            discord_context = {
                "channel": getattr(message.channel, 'name', 'DM'),
                "user": message.author.display_name,
                "recent_messages": recent_messages
            }

            debug_log(f"Processing message from {discord_context['user']}: {content[:50]}...")

            async with message.channel.typing():
                await invoke_agent(
                    prompt=content,
                    trigger_source="discord",
                    discord_context=discord_context,
                    use_discord_tools=True,
                    images=images if images else None,
                )

            for emoji in message_queue.reactions:
                try:
                    await message.add_reaction(emoji)
                except Exception as e:
                    print(f"Failed to add reaction {emoji}: {e}")

            for msg_content in message_queue.messages:
                if msg_content:
                    chunks = [msg_content[i:i + 1900] for i in range(0, len(msg_content), 1900)]
                    for chunk in chunks:
                        try:
                            await message.channel.send(chunk)
                        except Exception as e:
                            print(f"Failed to send message: {e}")

            for img_data in message_queue.images:
                try:
                    img_path = Path(img_data["path"])
                    if img_path.exists():
                        file = File(str(img_path), filename=img_path.name)
                        caption = img_data.get("caption", "")
                        await message.channel.send(content=caption if caption else None, file=file)
                        debug_log(f"📤 Sent image: {img_path.name}")
                    else:
                        await message.channel.send(f"⚠️ Image not found: {img_path}")
                except Exception as e:
                    print(f"Failed to send image: {e}")

            if not message_queue.messages and not message_queue.reactions and not message_queue.images:
                try:
                    await message.add_reaction("👍")
                except:
                    pass

            if _restart_requested:
                await message.channel.send("🔄 Restarting... I'll be back in a moment!")
                await asyncio.sleep(1)
                sys.exit(42)

        return discord_client

    except ImportError:
        print("Discord: discord.py not installed. Run: uv pip install discord.py")
        return None
    except Exception as e:
        print(f"Discord: Error setting up bot: {e}")
        return None


# =============================================================================
# HTTP Server (FastAPI)
# =============================================================================

app = FastAPI(title="Thoth Agent", description="AI Assistant API")


@app.get("/health")
async def health():
    """Health check endpoint."""
    mode = "gemini" if GEMINI_MODE else "claude"
    return {"status": "ok", "mode": mode, "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/memory")
async def get_memory():
    """Get current Letta memory blocks."""
    return {"memory": get_letta_memory_blocks()}


@app.get("/journal")
async def get_journal(n: int = 20):
    """Get recent journal entries."""
    return {"entries": read_recent_journal(n)}


@app.post("/chat")
async def chat(request: Request):
    """Process a chat message."""
    try:
        body = await request.json()
        prompt = body.get("message", body.get("prompt", ""))

        if not prompt:
            return JSONResponse({"error": "No message provided"}, status_code=400)

        response = await invoke_agent(
            prompt=prompt,
            trigger_source="http",
            use_discord_tools=False,
        )

        return {
            "response": response,
            "messages": message_queue.messages,
            "mode": "gemini" if GEMINI_MODE else "claude",
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/invoke")
async def invoke(request: Request):
    """Lower-level invoke endpoint with more options."""
    try:
        body = await request.json()

        response = await invoke_agent(
            prompt=body.get("prompt", ""),
            trigger_source=body.get("trigger_source", "http"),
            discord_context=body.get("discord_context"),
            use_discord_tools=body.get("use_discord_tools", False),
        )

        return {
            "response": response,
            "queue": {
                "messages": message_queue.messages,
                "reactions": message_queue.reactions,
                "images": message_queue.images,
            },
            "restart_requested": _restart_requested,
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/perch")
async def perch():
    """Ambient processing tick - agent reviews state and acts autonomously."""
    try:
        # Read state files
        state_files = {}
        for name in ["today.md", "inbox.md", "commitments.md"]:
            path = STATE_DIR / name
            if path.exists():
                state_files[name] = path.read_text(encoding="utf-8")[:2000]
            else:
                state_files[name] = "(not found)"

        # Build perch prompt
        prompt = f"""This is your scheduled ambient processing tick (runs every 2 hours).

## Current State Files

### today.md
{state_files.get('today.md', '(empty)')}

### inbox.md
{state_files.get('inbox.md', '(empty)')}

### commitments.md
{state_files.get('commitments.md', '(empty)')}

## Your Task

1. Review your state files and recent journal
2. Identify any tasks you can make progress on
3. Update state files if needed (write to them)
4. Send a brief message to Discord summarizing what you did or observed

Be proactive but concise. If nothing needs attention, just send a brief status update."""

        # We need to send to Discord, so we need the channel
        if discord_client and discord_client.is_ready():
            channel_id = DISCORD_CHANNEL_ID or _current_channel_id
            if channel_id:
                channel = discord_client.get_channel(int(channel_id))
                if channel is None:
                    channel = await discord_client.fetch_channel(int(channel_id))

                if channel:
                    discord_context = {
                        "channel": getattr(channel, 'name', 'perch'),
                        "user": "perch_tick",
                        "recent_messages": [],
                    }

                    await invoke_agent(
                        prompt=prompt,
                        trigger_source="perch",
                        discord_context=discord_context,
                        use_discord_tools=True,
                    )

                    # Send queued messages to Discord
                    for msg_content in message_queue.messages:
                        if msg_content:
                            chunks = [msg_content[i:i + 1900] for i in range(0, len(msg_content), 1900)]
                            for chunk in chunks:
                                await channel.send(chunk)

                    result = {
                        "status": "ok",
                        "messages_sent": len(message_queue.messages),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    message_queue.clear()
                    return result

        return JSONResponse({"error": "Discord not connected or no channel configured"}, status_code=503)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# =============================================================================
# CLI Mode
# =============================================================================

async def cli_mode():
    """Interactive CLI mode for testing."""
    mode_str = "Gemini" if GEMINI_MODE else "Claude"
    print(f"Thoth Agent - CLI Mode ({mode_str})")
    print("Type 'quit' or 'exit' to stop.\n")

    while True:
        try:
            prompt = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if prompt.lower() in ("quit", "exit"):
            break

        if not prompt:
            continue

        response = await invoke_agent(
            prompt=prompt,
            trigger_source="cli",
            discord_context={"user": "cli_user", "channel": "cli"},
            use_discord_tools=False,
        )

        if message_queue.reactions:
            print(f"[Reactions: {' '.join(message_queue.reactions)}]")

        for msg in message_queue.messages:
            print(f"Thoth: {msg}")

        for img in message_queue.images:
            print(f"[Image: {img['path']}]")

        if not message_queue.has_content() and response:
            print(f"Thoth: {response}")

        print()


# =============================================================================
# Combined Server + Discord
# =============================================================================

async def run_server_with_discord():
    """Run both HTTP server and Discord bot concurrently."""
    discord_bot = setup_discord()

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8787,
        log_level="info" if DEBUG else "warning",
    )
    server = uvicorn.Server(config)

    tasks = [server.serve()]

    if discord_bot:
        tasks.append(discord_bot.start(DISCORD_TOKEN))

    print(f"Starting Thoth Agent (Mode: {'Gemini' if GEMINI_MODE else 'Claude'})")
    print(f"HTTP server: http://0.0.0.0:8787")
    if discord_bot:
        print("Discord bot: connecting...")

    await asyncio.gather(*tasks)


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    global DEBUG, GEMINI_MODE

    args = sys.argv[1:]

    if "--debug" in args:
        DEBUG = True
        args.remove("--debug")
        print("🔍 DEBUG MODE ENABLED")

    if "gemini" in args:
        GEMINI_MODE = True
        args.remove("gemini")
        print("♊ GEMINI MODE ENABLED")
    else:
        print("🔷 CLAUDE MODE")

    mode = args[0] if args else "default"

    if mode == "cli":
        anyio.run(cli_mode)

    elif mode == "discord":
        bot = setup_discord()
        if bot:
            bot.run(DISCORD_TOKEN)
        else:
            print("Error: Could not initialize Discord bot")
            sys.exit(1)

    elif mode == "server":
        print(f"Starting HTTP server only (Mode: {'Gemini' if GEMINI_MODE else 'Claude'})")
        uvicorn.run(app, host="0.0.0.0", port=8787)

    else:
        asyncio.run(run_server_with_discord())


if __name__ == "__main__":
    main()