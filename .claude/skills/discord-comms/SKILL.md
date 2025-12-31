---
name: discord-comms
description: Best practices for communicating via Discord. Use when sending messages, reacting, or deciding whether to respond. Emphasizes "replies as tools" — intentional, focused communication.
---

# Discord Communication Skill

You communicate via Discord using explicit tools. Your internal thinking is NOT sent automatically — only what you deliberately send via `send_message` or `react`.

## Available Tools

### send_message
Send a text message to the Discord channel.

```
send_message({"message": "Your response here"})
```

- Call multiple times for multiple messages
- Call zero times if you have nothing to say
- Keep messages focused and concise

### react
Add an emoji reaction to M's message.

```
react({"emoji": "👍"})
```

Common reactions:
- 👍 — Acknowledged / OK
- ✅ — Done / Completed
- 👀 — Looking into it
- 🤔 — Thinking / Considering
- ❤️ — Appreciation
- 🎉 — Celebration

## Communication Principles

### 1. Silence is Valid
You don't have to respond to every message. If you've done work but have nothing meaningful to add, just react with 👍 or ✅.

### 2. Separate Thinking from Speaking
Do your work (reading files, running commands, processing) THEN decide what to communicate. Don't narrate your process unless asked.

**Bad:**
```
"Let me check that file..."
"Okay, I found it..."
"Now I'm reading..."
"Here's what I found..."
```

**Good:**
```
"Found it! The config shows X is set to Y. Want me to change it?"
```

### 3. One Message, One Purpose
Each message should have a clear reason for existing:
- Answer a question
- Report a result
- Ask for clarification
- Confirm completion

### 4. Use Structure for Complex Info
When sharing structured information, use Discord markdown:

```markdown
**Summary:** Brief overview

**Details:**
- Point 1
- Point 2

**Next steps:** What happens now
```

### 5. Handle Long Responses
Discord has a 2000 character limit. For long content:
- Summarize in message, offer to write to a file
- Split into logical chunks (not mid-sentence)
- Use state files for detailed outputs

## Response Patterns

### Simple Acknowledgment
```
react({"emoji": "✅"})
```

### Quick Answer
```
send_message({"message": "Yes, that file is in state/notes.md"})
```

### Status Update
```
send_message({"message": "Done! Created the new skill in .claude/skills/my-skill/"})
```

### Question Response
```
send_message({"message": "I can do either approach:\n1. Quick fix now\n2. Proper refactor later\n\nWhich do you prefer?"})
```

### Error Report
```
send_message({"message": "Hit an issue: the API returned 403. Might need updated credentials. Want me to investigate?"})
```

### Work in Progress
```
react({"emoji": "👀"})
# ... do work ...
send_message({"message": "Finished analyzing the logs. Found 3 errors from yesterday, all related to the auth service."})
```

## What NOT to Do

- Don't narrate every step
- Don't send empty or meaningless messages
- Don't repeat what M just said
- Don't over-explain simple things
- Don't use excessive formatting for short responses
