# Agent Instructions for vrphoto-checker

## 🚨 MANDATORY READING BEFORE ANY IMPLEMENTATION

### Primary Rule: ALWAYS READ `architecture.md` FIRST

**Before making ANY code changes, bug fixes, or feature additions:**

1. **READ**: `architecture.md` in the project root
2. **UNDERSTAND**: Which module the change affects
3. **VERIFY**: The change aligns with the design philosophy
4. **IMPLEMENT**: Following the architectural constraints

### Why This Matters

This project has a **strict architectural design** that prioritizes:

- **Zero external dependencies** (except Ollama for AI)
- **rules.md as single source of truth** for moderation rules
- **Standard library only** (no pip install required)
- **Module separation** (watcher, auditor, database, server)

**Previous mistakes by other agents:**
- ❌ Hardcoding moderation rules in `auditor.py` instead of using `rules.md`
- ❌ Adding external libraries that break portability
- ❌ Mixing responsibilities between modules

### Required Workflow

See: `.agent/workflows/implementation-workflow.md`

Every implementation must follow this workflow to maintain architectural integrity.

### Key Files

| File | Purpose | Agent Action |
|------|---------|--------------|
| `architecture.md` | **Design spec** | ✅ READ FIRST before any change |
| `rules.md` | Moderation rules | ✅ Update rules here, NOT in code |
| `config.json` | Runtime config | ✅ Add new settings here |
| `core/auditor.py` | AI communication | ❌ Do NOT hardcode rules here |
| `core/watcher.py` | Folder monitoring | ❌ Do NOT add AI logic here |
| `core/database.py` | SQLite operations | ❌ Do NOT add business logic here |

### Design Philosophy

From architecture.md Section 1:
> 外部ライブラリを最小限に抑えることで、環境構築の手間（pip install 等）を減らし、安定したポータブルな監査環境を提供する。

**Translation**: Minimize external libraries to reduce setup effort and provide a stable, portable audit environment.

**This is not optional. This is the core design principle.**

---

## Quick Reference

**Before implementing, ask yourself:**

1. ✅ Did I read `architecture.md`?
2. ✅ Is this change in the correct module?
3. ✅ Am I using standard library only?
4. ✅ Are rules still in `rules.md` (not hardcoded)?
5. ✅ Does this maintain portability?

If any answer is "No" → Re-read architecture.md and adjust your approach.

---

**作成日**: 2026-02-14
**目的**: 設計図に従わない実装を防ぐための強制ルール
