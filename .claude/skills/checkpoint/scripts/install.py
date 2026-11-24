#!/usr/bin/env python3
"""Installer for the *checkpoint* skill — wire compact-survival into any project.

Idempotently sets up the PreCompact + SessionStart hooks in a target project:

  1. copies ``session_checkpoint.py`` into ``<target>/.claude/hooks/``
  2. merges the two hook entries into ``<target>/.claude/settings.json``
     (preserving any hooks already there — e.g. a global RTK hook)
  3. ensures ``.claude/checkpoints/`` is git-ignored
  4. seeds a ``CONTINUITY.md`` handoff doc from the template (only if absent)
  5. (optional, --with-config) writes a starter ``.claude/continuity.json``

Safe to re-run — never duplicates hooks. **Stdlib only.**

Usage::

    python3 install.py --target /path/to/project          # install
    python3 install.py --target . --dry-run               # preview, write nothing
    python3 install.py --target . --with-config           # also seed continuity.json
    python3 install.py --target . --uninstall             # remove hooks + script
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_DIR / "scripts"
TEMPLATES = SKILL_DIR / "templates"

HOOK = '.claude/hooks/session_checkpoint.py'
WRITE_CMD = f'python3 "$CLAUDE_PROJECT_DIR/{HOOK}" --write'
START_CMD = f'python3 "$CLAUDE_PROJECT_DIR/{HOOK}" --session-start'

# PreCompact fires for both manual (/compact) and auto compaction.
PRECOMPACT_ENTRY = {"matcher": "", "hooks": [{"type": "command", "command": WRITE_CMD, "timeout": 30}]}
# SessionStart fires on resume / after compaction.
SESSIONSTART_ENTRY = {"matcher": "compact|resume", "hooks": [{"type": "command", "command": START_CMD}]}


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _command_of(entry: dict) -> str | None:
    for h in entry.get("hooks") or []:
        if isinstance(h, dict) and "command" in h:
            return h["command"]
    return None


def _has(existing: list, command: str) -> bool:
    return any(_command_of(e) == command for e in existing)


def merge_hooks(settings: dict) -> tuple[dict, list[str]]:
    """Pure: return (new_settings, changes). Additive + idempotent."""
    changes: list[str] = []
    hooks = settings.setdefault("hooks", {})
    pre = hooks.setdefault("PreCompact", [])
    if not _has(pre, WRITE_CMD):
        pre.append(json.loads(json.dumps(PRECOMPACT_ENTRY)))
        changes.append("PreCompact += checkpoint --write")
    ss = hooks.setdefault("SessionStart", [])
    if not _has(ss, START_CMD):
        ss.append(json.loads(json.dumps(SESSIONSTART_ENTRY)))
        changes.append("SessionStart += checkpoint --session-start")
    return settings, changes


def unmerge_hooks(settings: dict) -> tuple[dict, list[str]]:
    changes: list[str] = []
    hooks = settings.get("hooks", {})
    for event, cmd in (("PreCompact", WRITE_CMD), ("SessionStart", START_CMD)):
        cur = hooks.get(event, [])
        new = [e for e in cur if _command_of(e) != cmd]
        if len(new) != len(cur):
            changes.append(f"{event} -= checkpoint")
        hooks[event] = new
    return settings, changes


def ensure_gitignore(target: Path, dry: bool, log: list[str]) -> None:
    gi = target / ".claude" / ".gitignore"
    existing = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    if "checkpoints/" in existing:
        return
    log.append("gitignore += checkpoints/")
    if not dry:
        gi.parent.mkdir(parents=True, exist_ok=True)
        with gi.open("a", encoding="utf-8") as f:
            if not existing:
                f.write("# checkpoint skill — local machine state (not portable)\n")
            elif existing[-1].strip():
                f.write("\n")
            f.write("checkpoints/\n")


def install(target: Path, dry: bool, with_config: bool) -> int:
    log: list[str] = []
    hooks_dir = target / ".claude" / "hooks"

    src = SCRIPTS / "session_checkpoint.py"
    dst = hooks_dir / "session_checkpoint.py"
    same = dst.exists() and dst.read_bytes() == src.read_bytes()
    log.append(f"{'= up-to-date' if same else 'copy'}: {HOOK}")
    if not dry and not same:
        hooks_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        dst.chmod(0o755)

    settings_path = target / ".claude" / "settings.json"
    settings = _load_json(settings_path)
    settings, changes = merge_hooks(settings)
    log += changes or ["hooks already wired (no change)"]
    if not dry:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ensure_gitignore(target, dry, log)

    handoff = target / "CONTINUITY.md"
    tmpl = TEMPLATES / "CONTINUITY.md.template"
    if not handoff.exists() and tmpl.exists():
        log.append("seed: CONTINUITY.md (from template)")
        if not dry:
            handoff.write_text(tmpl.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        log.append("= CONTINUITY.md exists (kept)" if handoff.exists() else "(no template)")

    if with_config:
        cfg = target / ".claude" / "continuity.json"
        example = SCRIPTS / "continuity_config.example.json"
        if not cfg.exists() and example.exists():
            log.append("seed: .claude/continuity.json")
            if not dry:
                cfg.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            log.append("= continuity.json exists (kept)" if cfg.exists() else "(no example)")

    _print("INSTALL" + (" (dry-run)" if dry else ""), target, log)
    if not dry:
        print("\n  Next: verify with")
        print(f"    python3 {HOOK}                 # prints a checkpoint")
        print("    (then trigger /compact and confirm the next session restores it)")
    return 0


def uninstall(target: Path, dry: bool) -> int:
    log: list[str] = []
    settings_path = target / ".claude" / "settings.json"
    settings = _load_json(settings_path)
    settings, changes = unmerge_hooks(settings)
    log += changes or ["no hooks to remove"]
    if not dry and changes:
        settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    hook = target / ".claude" / "hooks" / "session_checkpoint.py"
    if hook.exists():
        log.append(f"remove: {HOOK}")
        if not dry:
            hook.unlink()
    log.append("note: .claude/checkpoints/ and CONTINUITY.md left in place (remove manually if desired)")
    _print("UNINSTALL" + (" (dry-run)" if dry else ""), target, log)
    return 0


def _print(header: str, target: Path, log: list[str]) -> None:
    print(f"[checkpoint] {header} → {target}")
    for line in log:
        print(f"  • {line}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Install the checkpoint skill into a project.")
    ap.add_argument("--target", default=".", help="target project root (default: cwd)")
    ap.add_argument("--dry-run", action="store_true", help="preview changes, write nothing")
    ap.add_argument("--with-config", action="store_true", help="also seed .claude/continuity.json")
    ap.add_argument("--uninstall", action="store_true", help="remove hooks + script")
    args = ap.parse_args(argv)

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"error: target does not exist: {target}", file=sys.stderr)
        return 2
    if args.uninstall:
        return uninstall(target, args.dry_run)
    return install(target, args.dry_run, args.with_config)


if __name__ == "__main__":
    sys.exit(main())
