# Changelog

## 1.2.0
- Publishable docs: how it works and what it can handle, orchestration diagrams, when the owner
  is asked, the seat catalogue, a prompt-by-prompt walkthrough, and a seated example project (Tally).
- The shared rulebook template gains *When the owner is asked, and when not* (§7).
- Seat rulebooks made domain-neutral throughout.

## 1.1.0
- Installable as a Claude Code plugin with its own marketplace.
- Seat rulebooks travel inside `team-setup` and are copied into each project's `.claude/skills/`
  (workers cannot preload a skill that lives only in a plugin), with a hash lock and `--sync`.

## 1.0.0
- 21 seat rulebooks, `team-setup`, the scaffold, the worker generator, seven model tiers.
