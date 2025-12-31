---
name: letta-memory
description: View and update Letta memory blocks. Use when you need to persistently store information about projects, people, workflows, or any long-term knowledge that should survive beyond the journal.
---

# Letta Memory Skill

Your Letta memory blocks are your long-term persistent memory. Unlike the journal (temporal, recent entries only), memory blocks are always fully injected into your context. They're your identity and knowledge base.

## Current Memory Blocks

Your memory blocks are injected as `<letta_memory>` in your system prompt. Common blocks:

- `assistant_persona` — Your identity and personality
- `projects_*` — Individual project details
- `tool_workflow` — How to use tools and store data
- `to-read` — Reading list and resources
- `message_routes` — How messages flow to you

## When to Update Memory

- New project started → Create `projects_projectname` block
- Project status changed → Update existing project block
- Learned new workflow → Update `tool_workflow`
- New person in M's life → Create person block
- Your capabilities changed → Update `assistant_persona`

## How to Update Memory Blocks

Currently, you cannot directly update Letta memory blocks from within the Claude Agent SDK. You have two options:

### Option 1: Ask M to Update (Recommended for now)

Send a message like:
```
"I'd like to update my memory block 'projects_xyz' with the new status. Could you update it via the Letta ADE or let me know when the direct API integration is ready?"
```

### Option 2: Update via HTTP (if implemented)

If the Letta API is exposed, you could use curl:
```bash
# Get block ID first
curl http://localhost:8283/v1/agents/AGENT_ID/blocks

# Update block
curl -X PATCH http://localhost:8283/v1/blocks/BLOCK_ID \
  -H "Content-Type: application/json" \
  -d '{"value": "new content"}'
```

### Option 3: Use State Files as Cache

For information that changes frequently, use state files instead:
- `state/inbox.md` — Incoming items
- `state/today.md` — Current focus
- `state/commitments.md` — Tracked promises
- `state/notes.md` — Reference information

State files are read on every invocation and can be updated freely.

## Memory Block Best Practices

1. **Keep blocks focused** — One topic per block
2. **Use clear labels** — `projects_` prefix for projects, etc.
3. **Include timestamps** — Note when things were last updated
4. **Prune old info** — Remove outdated content to save context space
5. **Coordinate with journal** — Memory = what, Journal = when

## Memory vs Journal vs State Files

| Storage | Persistence | Injected | Best For |
|---------|-------------|----------|----------|
| Letta Memory | Permanent | Always (full) | Identity, long-term knowledge |
| Journal | Permanent | Recent 40 entries | Temporal events, decisions |
| State Files | Permanent | On-demand (Read) | Working memory, todos |

## Future: Direct Letta Integration

A future upgrade could add MCP tools for direct Letta memory manipulation:
- `letta_get_block(label)` — Read a specific block
- `letta_update_block(label, value)` — Update a block
- `letta_create_block(label, value)` — Create new block

This would let you manage your own memory autonomously.
