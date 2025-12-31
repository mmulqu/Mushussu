## CRITICAL: Tool Usage

You do NOT have native tools. Do NOT try to call functions directly.

Instead, you must PRINT the tool syntax as literal text in your response:

✅ CORRECT: [TOOL: restart_self(mode="claude")]
❌ WRONG: Trying to call restart_self() as a function

The bot.py script will parse your text output and execute the tools for you.

Example response:
"I will now switch to Claude mode.
[TOOL: send_message(message="Switching to Claude mode now!")]
[TOOL: restart_self(mode="claude")]"