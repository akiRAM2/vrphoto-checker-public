---
description: Implementation workflow - Always follow architecture.md
---

# Implementation Workflow for vrphoto-checker

**🚨 CRITICAL RULE: Before implementing ANY feature or fix, you MUST read `architecture.md` first.**

## Pre-Implementation Checklist

### 1. Read Architecture Document
```bash
# Always start by reviewing the design spec
Step 1: Read architecture.md completely
Step 2: Identify which module the change affects (core/, web/, main.py)
Step 3: Verify the change aligns with the design philosophy
```

### 2. Verify Design Compliance

**Key Design Principles from architecture.md:**

- ✅ **Standard Library First**: Use Python standard library (no external dependencies except Ollama)
- ✅ **rules.md as Single Source of Truth**: All moderation rules MUST be in `rules.md`, NOT hardcoded
- ✅ **Module Separation**:
  - `core/watcher.py` - Folder monitoring only
  - `core/auditor.py` - AI communication only (reads rules.md)
  - `core/database.py` - SQLite operations only
  - `web/server.py` - HTTP server only
  - `main.py` - Orchestration only

### 3. Implementation Steps

**For any code change:**

1. **CHECK**: Does this violate architecture.md?
   - ❌ Adding external dependencies (watchdog, requests, etc.)
   - ❌ Hardcoding moderation rules in Python code
   - ❌ Mixing responsibilities (e.g., watcher.py doing AI calls)

2. **VERIFY**: Is the change in the right module?
   - Folder watching → `core/watcher.py`
   - AI inference → `core/auditor.py`
   - Database → `core/database.py`
   - Web UI → `web/server.py` or `web/index.html`
   - Config → `config.json`
   - Rules → `rules.md`

3. **IMPLEMENT**: Follow the architecture
   - Use standard library equivalents (urllib instead of requests, etc.)
   - Keep `rules.md` as the central rule repository
   - Maintain portable design (no complex installation)

### 4. Post-Implementation Review

After making changes:

1. ✅ Verify no external dependencies were added
2. ✅ Confirm rules are still in `rules.md` (not hardcoded)
3. ✅ Check module boundaries are respected
4. ✅ Test that the change works as documented in architecture.md

## Common Mistakes to Avoid

❌ **Don't**: Add moderation logic to `auditor.py` → Use `rules.md`
❌ **Don't**: Use `watchdog` library → Use standard `os.scandir()`
❌ **Don't**: Use `requests` library → Use standard `urllib.request`
❌ **Don't**: Mix AI logic into `watcher.py` → Keep separation of concerns

✅ **Do**: Always read architecture.md before coding
✅ **Do**: Keep the design simple and portable
✅ **Do**: Maintain single source of truth (rules.md for rules, config.json for settings)

## Architecture Reference

**Must-read sections before implementing:**
- Section 2.1: Module structure
- Section 3: Directory structure
- Section 4.1: Audit process flow
- Section 4.2: rules.md usage
- Section 6: Technical constraints

---

**Remember**: architecture.md は設計図です。必ず従ってください。
