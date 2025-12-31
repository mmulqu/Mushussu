---
name: self-update
description: Apply updates to claude-agent-sdk-gemini-bot.py that M sends you and restart. Use when M sends you new code to install, or when you need to restart yourself.
---

# Self-Update Skill

You can update your own code and restart yourself. This enables M to send you improvements without manually accessing the mini PC.

## Available Tools

### restart_self
Restart the agent without changing any code. Useful for:
- Picking up changes to CLAUDE.md
- Clearing any stuck state
- Testing the restart mechanism

```
restart_self({})
```
### restart_self

Restart the agent. Optionally switch between Claude and Gemini modes.
```
# Restart in current mode
restart_self({})

# Switch to Claude mode
restart_self({"mode": "claude"})

# Switch to Gemini mode  
restart_self({"mode": "gemini"})
```

**Gemini syntax** (for GEMINI.md or prompts):
```
[TOOL: restart_self()]
[TOOL: restart_self(mode="claude")]
[TOOL: restart_self(mode="gemini")]
```

### apply_update
Apply a new version of bot.py and restart. Use when M sends you updated code.

```
apply_update({"new_content": "#!/usr/bin/env python3\n..."})
```

This will:
1. Backup current bot.py to bot.py.backup
2. Write the new content to bot.py
3. Trigger a restart

## Workflow: Receiving Updates from M

When M sends you updated code (usually as a file or code block):

1. **Acknowledge receipt**
   ```
   react({"emoji": "👀"})
   ```

2. **Read the new code** if it's a file
   ```
   Read the uploaded file
   ```

3. **Apply the update**
   ```
   apply_update({"new_content": "<full content of new bot.py>"})
   ```

4. **Confirm** (this message sends before restart)
   ```
   send_message({"message": "Update applied! Restarting now..."})
   ```

5. **Restart happens automatically**

## Important Notes

- **Must use run.py**: Self-restart only works when started via `python run.py`, not `python bot.py` directly
- **Backup created**: Previous bot.py is saved to bot.py.backup
- **Exit code 42**: This signals the runner to restart (any other code = stop)
- **3-second delay**: Runner waits 3 seconds before restarting

## Rollback if Update Fails

If the new code has errors and the agent crashes:
1. The runner will see exit code (not 42) and stop
2. M can manually restore: `copy bot.py.backup bot.py`
3. M restarts: `python run.py`

## Testing Restart

To test that restart works:
```
restart_self({})
```

You should:
1. See "Restarting..." message in Discord
2. Disconnect briefly
3. Reconnect and respond normally

## HTTP Restart Endpoint

There's also an HTTP endpoint for external restart triggers:
```
POST http://localhost:8787/restart
```

This is useful for:
- CI/CD pipelines
- Scheduled maintenance
- Remote management
