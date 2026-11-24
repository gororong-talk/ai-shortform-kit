#!/usr/bin/env python3
"""Portable session checkpoint — survive Claude Code context compaction.

A single script with two modes, wired to two hooks:

  --write          PreCompact hook. Snapshots operational state to
                   .claude/checkpoints/latest.md (+ timestamped backups)
                   *before* the transcript is auto-summarized.
  --session-start  SessionStart hook. Emits the latest checkpoint as JSON
                   `hookSpecificOutput.additionalContext` so Claude Code
                   injects it into the fresh/compacted session.
  (no arg)         same as --write.

It captures what an auto-summary routinely drops: running processes, git state
(branch / dirty / recent commits), the handoff doc's pending section, and
recently-changed files. A human-maintained handoff doc (CONTINUITY.md) carries
the intent the tooling can't infer (its "## Pending" section is auto-extracted).

Design: **stdlib only**, every step wrapped so a hook can never fail (always
exit 0), output bounded so the checkpoint itself never bloats context. Drops
into any project unchanged. Optional config: .claude/continuity.json
(see continuity_config.example.json).
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_DEFAULT_HANDOFF_NAMES = ["CONTINUITY.md", "RESTART_PROTOCOL.md", "HANDOFF.md", "SESSION.md"]
_DEFAULT_WATCH_GLOBS = ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.go", "*.rs",
                        "*.java", "*.rb", "*.php", "*.md", "*.yaml", "*.yml", "*.toml"]
_IGNORE_DIRS = {".git", "venv", ".venv", "node_modules", "__pycache__", ".mypy_cache",
                ".pytest_cache", "dist", "build", ".next", "target", ".idea", ".tox", "data"}
_PENDING_MARKERS = ["Pending", "다음 명령", "다음 작업", "Next actions", "다음 세션"]


# ── root + config ─────────────────────────────────────────────────────────
def resolve_root(explicit: str | None = None) -> Path:
    """--root > $CLAUDE_PROJECT_DIR (set by Claude Code) > walk to .git/.claude marker."""
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and Path(env).exists():
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists() or (parent / ".claude").is_dir():
            return parent
    return Path.cwd()


def load_config(root: Path) -> dict:
    cfg_path = root / ".claude" / "continuity.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"_config_error": f"{type(e).__name__}: {e}"}


def _now(cfg: dict) -> datetime:
    off = cfg.get("timezone_offset_hours")
    return datetime.now() if off is None else datetime.now(timezone(timedelta(hours=off)))


# ── data collectors (each never raises) ────────────────────────────────────
def _run(cmd: list[str], root: Path, timeout: int = 8) -> str:
    try:
        r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "").strip()
    except Exception as e:  # noqa: BLE001
        return f"(unavailable: {e})"


def _proc(pattern: str, label: str, root: Path) -> str:
    """pgrep -f <pattern>; pgrep never matches its own process, so no self-match."""
    try:
        r = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True, timeout=5)
        pid = (r.stdout or "").strip().split("\n")[0]
        return f"{label}: {pid}" if pid else f"{label}: DOWN"
    except Exception:  # noqa: BLE001
        return f"{label}: ?"


def _detect_handoff(root: Path, cfg: dict) -> Path | None:
    name = cfg.get("handoff_doc")
    if name:
        p = root / name
        return p if p.exists() else None
    for cand in _DEFAULT_HANDOFF_NAMES:
        if (root / cand).exists():
            return root / cand
    return None


def _pending_section(root: Path, cfg: dict) -> tuple[str, str]:
    """Return (doc_name, section_text). Extracts from the first matching marker."""
    handoff = _detect_handoff(root, cfg)
    if not handoff:
        return ("", "(no handoff doc — create CONTINUITY.md with a '## Pending' section)")
    try:
        lines = handoff.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as e:  # noqa: BLE001
        return (handoff.name, f"(read failed: {e})")
    markers = cfg.get("pending_markers", _PENDING_MARKERS)
    max_lines = int(cfg.get("pending_lines", 40))
    out: list[str] = []
    capture = False
    for ln in lines:
        if not capture and any(m in ln for m in markers):
            capture = True
        if capture:
            out.append(ln)
        if len(out) >= max_lines:
            break
    if out:
        return (handoff.name, "\n".join(out))
    # no marker → head of doc as orientation
    head = "\n".join(lines[:max_lines])
    return (handoff.name, head or "(empty handoff doc)")


def _recent_files(root: Path, cfg: dict) -> list[str]:
    globs = cfg.get("watch_globs", _DEFAULT_WATCH_GLOBS)
    minutes = int(cfg.get("recent_minutes", 180))
    cap = int(cfg.get("max_recent_files", 20))
    cutoff = datetime.now().timestamp() - minutes * 60
    hits: list[tuple[float, str]] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _IGNORE_DIRS]
        if Path(dirpath).name == "checkpoints":
            dirnames[:] = []
            continue
        for fn in filenames:
            if not any(fnmatch.fnmatch(fn, g) for g in globs):
                continue
            fp = Path(dirpath) / fn
            try:
                mt = fp.stat().st_mtime
            except OSError:
                continue
            if mt >= cutoff:
                hits.append((mt, os.path.relpath(fp, root)))
    hits.sort(reverse=True)
    return [rel for _, rel in hits[:cap]]


# ── checkpoint document ────────────────────────────────────────────────────
def build_checkpoint(root: Path, cfg: dict) -> str:
    ts = _now(cfg).strftime("%Y-%m-%d %H:%M")
    tz = "" if cfg.get("timezone_offset_hours") is None else f" UTC{cfg['timezone_offset_hours']:+d}"
    title = cfg.get("title", "세션 체크포인트 / Session Checkpoint")

    md = [
        f"# 🔖 {title} — {ts}{tz}",
        "",
        "> compact/재시작 후 이 파일로 정확한 작업 상태를 즉시 복원 "
        "(auto-summary가 흘리는 운영 사실 보강 / restores state the summary drops).",
    ]
    if cfg.get("_config_error"):
        md += ["", f"> ⚠️ continuity.json: {cfg['_config_error']} (using defaults)"]

    # processes
    procs = cfg.get("processes", [])
    if procs:
        line = " | ".join(_proc(p.get("pattern", ""), p.get("name", "?"), root) for p in procs)
        md += ["", "## 프로세스 / Processes", line]

    # git
    if (root / ".git").exists():
        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root)
        status = _run(["git", "status", "--short"], root)
        n = int(cfg.get("git_log_count", 10))
        commits = _run(["git", "log", f"-{n}", "--oneline"], root)
        clean = "✅ clean" if not status else f"⚠️ dirty ({len(status.splitlines())} files)"
        md += ["", "## Git", f"- branch: `{branch}`  |  working tree: {clean}",
               "- recent commits:", "```", commits, "```"]
        if status:
            md += ["- uncommitted:", "```", "\n".join(status.splitlines()[:25]), "```"]

    # handoff pending
    doc, section = _pending_section(root, cfg)
    md += ["", f"## {doc or 'Handoff'} — Pending / 다음 명령", "```", section, "```"]

    # recent files
    recent = _recent_files(root, cfg)
    minutes = int(cfg.get("recent_minutes", 180))
    md += ["", f"## 최근 {minutes}분 변경 파일 / Recently changed", "```",
           "\n".join(recent) if recent else "(none)", "```"]

    # recovery checklist (optional, project-tunable)
    checklist = cfg.get("recovery_checklist")
    if checklist:
        md += ["", "## 복구 체크리스트 / Recovery checklist"]
        md += [f"{i}. {step}" for i, step in enumerate(checklist, 1)]

    return "\n".join(md)


def write_checkpoint(root: Path, cfg: dict) -> Path:
    ckpt_dir = root / ".claude" / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    md = build_checkpoint(root, cfg)
    latest = ckpt_dir / "latest.md"
    latest.write_text(md, encoding="utf-8")
    stamp = _now(cfg).strftime("%Y%m%d_%H%M%S")
    (ckpt_dir / f"checkpoint_{stamp}.md").write_text(md, encoding="utf-8")
    keep = int(cfg.get("keep_backups", 20))
    for old in sorted(ckpt_dir.glob("checkpoint_*.md"), reverse=True)[keep:]:
        try:
            old.unlink()
        except OSError:
            pass
    return latest


def session_start_payload(root: Path, cfg: dict) -> str:
    """JSON for the SessionStart hook (additionalContext), or '' if no checkpoint."""
    latest = root / ".claude" / "checkpoints" / "latest.md"
    if not latest.exists():
        return ""
    try:
        content = latest.read_text(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""
    cap = int(cfg.get("inject_max_lines", 80))
    lines = content.splitlines()
    if len(lines) > cap:
        content = "\n".join(lines[:cap]) + "\n... (full: .claude/checkpoints/latest.md)"
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": content,
        }
    }, ensure_ascii=False)


# ── entrypoint ──────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Portable Claude Code session checkpoint.")
    ap.add_argument("--write", action="store_true", help="write checkpoint (PreCompact)")
    ap.add_argument("--session-start", action="store_true", help="emit checkpoint JSON (SessionStart)")
    ap.add_argument("--root", default=None, help="project root (default: $CLAUDE_PROJECT_DIR or auto)")
    args = ap.parse_args(argv)

    try:
        root = resolve_root(args.root)
        cfg = load_config(root)
        if args.session_start:
            payload = session_start_payload(root, cfg)
            if payload:
                print(payload)
        else:  # --write or default
            p = write_checkpoint(root, cfg)
            print(f"checkpoint written: {p}")
    except Exception as e:  # noqa: BLE001 — a hook must never fail the operation
        print(f"(checkpoint skipped: {e})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
