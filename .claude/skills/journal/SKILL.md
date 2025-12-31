---
name: journal
description: Write entries to the journal log for temporal memory. Use this to record what happened during interactions, decisions made, errors encountered, or insights gained. Critical for maintaining continuity across invocations.
---

# Journaling Skill

Your journal (`logs/journal.jsonl`) is your temporal memory. Each entry is a JSON object on a single line. Recent entries are injected into your prompt, so future invocations of yourself will see them.

## When to Journal

- After completing a significant task
- When you learn something new about M or the projects
- When you make a decision that future-you should know about
- When errors occur (for debugging)
- When starting/ending perch time
- When you receive important information

## Journal Entry Format

```json
{"t": "ISO-timestamp", "type": "entry-type", "topics": ["tag1", "tag2"], "summary": "What happened"}
```

### Required Fields
- `t` — Timestamp (auto-added by write_journal, but include if writing directly)
- `type` — Category of entry

### Recommended Fields
- `topics` — Array of tags for searchability (use when you might want to find this later)
- `summary` — Brief description of what happened

### Optional Fields (by type)
- `user_stated` — What M said they would do (for tracking commitments)
- `my_intent` — What you're working on or planning
- `error` — Error message if something went wrong
- `decision` — A decision you made and why
- `insight` — Something you learned

## Entry Types

| Type | When to Use |
|------|-------------|
| `invocation` | Auto-logged for each agent run |
| `error` | Something went wrong |
| `decision` | You made a choice that matters |
| `insight` | You learned something new |
| `commitment` | M committed to something |
| `milestone` | A project reached a milestone |
| `perch` | Perch time activity |
| `note` | General observation |

## How to Write

Use Bash to append to the journal:

```bash
echo '{"t":"2025-12-20T12:00:00Z","type":"note","topics":["project","insight"],"summary":"Discovered new pattern in codebase"}' >> logs/journal.jsonl
```

Or use the Edit tool to append a line.

## Querying the Journal

Use `jq` to search by topic:
```bash
cat logs/journal.jsonl | jq -s '[.[] | select(.topics[]? == "project")]'
```

Search by type:
```bash
cat logs/journal.jsonl | jq -s '[.[] | select(.type == "error")]'
```

Last 10 entries:
```bash
tail -10 logs/journal.jsonl | jq .
```

## Best Practices

1. **Write frequently** — If it's important, journal it
2. **Use consistent topics** — Makes searching easier
3. **Be concise** — Summaries should be scannable
4. **Include context** — Future-you won't remember details
5. **Tag projects** — Use project names as topics
