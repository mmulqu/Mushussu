#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import urllib.parse
from pathlib import Path
from datetime import datetime
from typing import Optional

import aiohttp
from fastmcp import FastMCP

mcp = FastMCP(name="discord")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DEFAULT_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID", "")
BASE_DIR = Path(os.getenv("THOTH_BASE_DIR", Path(__file__).parent)).resolve()
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

DISCORD_API_BASE = "https://discord.com/api/v10"


def _auth_headers() -> dict:
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set in environment.")
    return {"Authorization": f"Bot {DISCORD_TOKEN}"}


async def _post_json(url: str, payload: dict) -> dict:
    async with aiohttp.ClientSession(headers=_auth_headers()) as session:
        async with session.post(url, json=payload) as r:
            text = await r.text()
            if r.status >= 300:
                raise RuntimeError(f"Discord API error {r.status}: {text}")
            return json.loads(text) if text else {}


async def _put(url: str) -> None:
    async with aiohttp.ClientSession(headers=_auth_headers()) as session:
        async with session.put(url) as r:
            if r.status >= 300:
                text = await r.text()
                raise RuntimeError(f"Discord API error {r.status}: {text}")


async def _post_multipart(url: str, *, content: str, file_path: Path) -> dict:
    form = aiohttp.FormData()
    form.add_field("payload_json", json.dumps({"content": content}), content_type="application/json")
    form.add_field("files[0]", file_path.read_bytes(), filename=file_path.name, content_type="application/octet-stream")

    async with aiohttp.ClientSession(headers=_auth_headers()) as session:
        async with session.post(url, data=form) as r:
            text = await r.text()
            if r.status >= 300:
                raise RuntimeError(f"Discord API error {r.status}: {text}")
            return json.loads(text) if text else {}


def _channel_id_or_default(channel_id: Optional[str]) -> str:
    cid = channel_id or DEFAULT_CHANNEL_ID
    if not cid:
        raise RuntimeError("No channel_id provided and DISCORD_CHANNEL_ID is not set.")
    return str(cid)


@mcp.tool
async def send_message(message: str, channel_id: Optional[str] = None) -> dict:
    """Send a Discord message to a channel."""
    cid = _channel_id_or_default(channel_id)
    url = f"{DISCORD_API_BASE}/channels/{cid}/messages"
    resp = await _post_json(url, {"content": message})
    return {
        "content": [
            {"type": "text", "text": f"Sent message to channel {cid} (id={resp.get('id')})."}
        ]
    }


@mcp.tool
async def react(emoji: str, channel_id: str, message_id: str) -> dict:
    """React to a specific Discord message with an emoji."""
    # Discord expects the emoji URL-encoded
    emoji_enc = urllib.parse.quote(emoji)
    url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages/{message_id}/reactions/{emoji_enc}/@me"
    await _put(url)
    return {"content": [{"type": "text", "text": f"Reacted with {emoji}."}]}


@mcp.tool
async def send_image(image_path: str, channel_id: Optional[str] = None, caption: str = "") -> dict:
    """Send an image file to Discord (by path)."""
    cid = _channel_id_or_default(channel_id)

    path = Path(image_path)
    if not path.is_absolute():
        path = (BASE_DIR / path).resolve()

    if not path.exists():
        raise RuntimeError(f"Image not found: {path}")

    url = f"{DISCORD_API_BASE}/channels/{cid}/messages"
    await _post_multipart(url, content=caption or "", file_path=path)

    return {"content": [{"type": "text", "text": f"Sent image {path.name} to channel {cid}."}]}


@mcp.tool
async def restart_self() -> dict:
    """Request the bot process to restart by creating a restart flag file."""
    flag = BASE_DIR / "restart.flag"
    flag.write_text(datetime.utcnow().isoformat(), encoding="utf-8")
    return {"content": [{"type": "text", "text": "Restart flag written."}]}


@mcp.tool
async def apply_update(new_content: str, target_path: str = "claude-agent-sdk-gemini-bot.py") -> dict:
    """Overwrite a file (default claude-agent-sdk-gemini-bot.py) and write a .backup copy first."""
    tgt = Path(target_path)
    if not tgt.is_absolute():
        tgt = (BASE_DIR / tgt).resolve()

    backup = tgt.with_suffix(tgt.suffix + ".backup")
    if tgt.exists():
        backup.write_text(tgt.read_text(encoding="utf-8"), encoding="utf-8")

    tgt.write_text(new_content, encoding="utf-8")
    (BASE_DIR / "restart.flag").write_text(datetime.utcnow().isoformat(), encoding="utf-8")

    return {
        "content": [
            {"type": "text", "text": f"Updated {tgt.name} ({len(new_content)} chars), backup at {backup.name}, restart requested."}
        ]
    }


if __name__ == "__main__":
    # STDIO transport so Gemini CLI can spawn it and talk over stdin/stdout.
    mcp.run()
