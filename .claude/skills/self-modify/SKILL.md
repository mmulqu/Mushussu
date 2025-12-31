---
name: self-modify
description: Modify Thoth's own code, skills, or configuration. Use when asked to change behavior, add capabilities, fix bugs in the agent, or create new skills. Always work on a dev branch and create a PR for review.
---

# Self-Modification Skill

You have the ability to modify your own code, skills, and configuration. This is a powerful capability that requires careful handling.

## Safety Principles

1. **Always use version control** — Never edit files on main directly
2. **Create PRs for review** — M should approve changes before deployment
3. **Test before committing** — Run syntax checks, lint, basic tests
4. **Document changes** — Write clear commit messages and update relevant docs
5. **Be conservative** — Prefer small, incremental changes over large rewrites

## Workflow for Code Changes (bot.py, etc.)

1. Check current branch: `git branch`
2. Create or switch to dev branch: `git checkout -b dev` or `git checkout dev`
3. Make your changes using Edit tool
4. Test the changes if possible (syntax check, dry run)
5. Commit with descriptive message: `git add -A && git commit -m "description"`
6. Push to remote: `git push origin dev`
7. Create PR via GitHub CLI: `gh pr create --title "..." --body "..."`
8. Notify M with the PR link via send_message

## Workflow for Creating New Skills

1. Create skill directory: `mkdir -p .claude/skills/skill-name`
2. Create SKILL.md with proper frontmatter:
   ```markdown
   ---
   name: skill-name
   description: Clear description of when to use this skill.
   ---
   
   # Skill Title
   
   Instructions here...
   ```
3. Add any scripts to `scripts/` subdirectory
4. Add any reference docs to `references/` subdirectory
5. Commit and push to dev branch
6. Skills don't require restart — they're loaded dynamically

## Workflow for Editing Existing Skills

1. Navigate to `.claude/skills/skill-name/`
2. Edit SKILL.md or related files
3. Commit with clear description of what changed
4. Push to dev branch

## Restart Handling

If you modify `bot.py` or other core files, M will need to restart the service for changes to take effect. After creating a PR:

1. Notify M that a restart is needed
2. Provide clear instructions: "After merging, restart with: `python bot.py discord`"

## Files You Can Modify

- `.claude/skills/*` — Skills (safe, no restart needed)
- `CLAUDE.md` — System prompt (no restart needed, reloaded each invocation)
- `state/*.md` — State files (no restart needed)
- `bot.py` — Core agent code (REQUIRES RESTART)
- `requirements.txt` — Dependencies (requires reinstall + restart)

## Git Setup Required

Before using this skill, ensure git is configured:
```bash
git config user.name "Thoth"
git config user.email "thoth@agent.local"
```

And GitHub CLI is authenticated:
```bash
gh auth status
```
