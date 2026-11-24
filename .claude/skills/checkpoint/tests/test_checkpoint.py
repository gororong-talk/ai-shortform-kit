#!/usr/bin/env python3
"""Test suite for the *checkpoint* skill. Stdlib only.

Standalone::   python3 tests/test_checkpoint.py
Pytest::       pytest tests/test_checkpoint.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


ckpt = _load("cp_checkpoint", SCRIPTS / "session_checkpoint.py")
install = _load("cp_install", SCRIPTS / "install.py")

_HAS_GIT = shutil.which("git") is not None


def _tmp() -> Path:
    return Path(tempfile.mkdtemp(prefix="cptest_"))


def _git_init(root: Path) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init", "-q"], cwd=root, env=env, check=True)
    (root / "a.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "."], cwd=root, env=env, check=True)
    subprocess.run(["git", "commit", "-qm", "init commit"], cwd=root, env=env, check=True)


def _capture(fn, *a, **k) -> str:
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn(*a, **k)
    finally:
        sys.stdout = old
    return buf.getvalue()


# ── checkpoint generation ──────────────────────────────────────────────────
def test_minimal_no_git_no_config():
    root = _tmp()
    try:
        text = ckpt.build_checkpoint(root, {})
        assert "체크포인트" in text or "Checkpoint" in text
        assert "## Git" not in text
        assert "## Pending" in text or "Pending" in text  # always emits handoff section
    finally:
        shutil.rmtree(root)


def test_includes_git_and_commit():
    if not _HAS_GIT:
        return
    root = _tmp()
    try:
        _git_init(root)
        text = ckpt.build_checkpoint(root, {})
        assert "## Git" in text and "init commit" in text and "✅ clean" in text
    finally:
        shutil.rmtree(root)


def test_dirty_tree_flagged():
    if not _HAS_GIT:
        return
    root = _tmp()
    try:
        _git_init(root)
        (root / "b.py").write_text("y = 2\n")
        text = ckpt.build_checkpoint(root, {})
        assert "⚠️ dirty" in text and "b.py" in text
    finally:
        shutil.rmtree(root)


def test_extracts_pending_from_continuity():
    root = _tmp()
    try:
        (root / "CONTINUITY.md").write_text("# x\n\n## Pending\n- do the thing\n", encoding="utf-8")
        text = ckpt.build_checkpoint(root, {})
        assert "do the thing" in text
    finally:
        shutil.rmtree(root)


def test_autodetects_restart_protocol():
    root = _tmp()
    try:
        (root / "RESTART_PROTOCOL.md").write_text("## Pending\n- legacy name works\n", encoding="utf-8")
        text = ckpt.build_checkpoint(root, {})
        assert "legacy name works" in text and "RESTART_PROTOCOL.md" in text
    finally:
        shutil.rmtree(root)


def test_korean_marker_detected():
    root = _tmp()
    try:
        (root / "CONTINUITY.md").write_text("# x\n\n## 다음 작업\n- 한국어 마커\n", encoding="utf-8")
        text = ckpt.build_checkpoint(root, {})
        assert "한국어 마커" in text
    finally:
        shutil.rmtree(root)


def test_recent_files_listed_and_filtered():
    root = _tmp()
    try:
        (root / "fresh.py").write_text("z = 3\n")
        (root / "venv").mkdir()
        (root / "venv" / "vend.py").write_text("v = 1\n")
        old = root / "old.py"
        old.write_text("o = 1\n")
        os.utime(old, (time.time() - 99999, time.time() - 99999))
        text = ckpt.build_checkpoint(root, {"recent_minutes": 180})
        assert "fresh.py" in text
        assert "venv/vend.py" not in text
        assert "old.py" not in text
    finally:
        shutil.rmtree(root)


def test_processes_section_toggle():
    root = _tmp()
    try:
        assert "## 프로세스" not in ckpt.build_checkpoint(root, {})
        text = ckpt.build_checkpoint(root, {"processes": [{"name": "X", "pattern": "no_such_proc_zzz"}]})
        assert "## 프로세스" in text and "X: DOWN" in text
    finally:
        shutil.rmtree(root)


def test_recovery_checklist_optional():
    root = _tmp()
    try:
        assert "Recovery checklist" not in ckpt.build_checkpoint(root, {})
        text = ckpt.build_checkpoint(root, {"recovery_checklist": ["step one", "step two"]})
        assert "Recovery checklist" in text and "1. step one" in text
    finally:
        shutil.rmtree(root)


def test_config_loaded_and_applied():
    root = _tmp()
    try:
        (root / ".claude").mkdir()
        (root / ".claude" / "continuity.json").write_text(json.dumps({"title": "ZZZ"}), encoding="utf-8")
        cfg = ckpt.load_config(root)
        assert cfg["title"] == "ZZZ"
        assert "ZZZ" in ckpt.build_checkpoint(root, cfg)
    finally:
        shutil.rmtree(root)


def test_config_parse_error_graceful():
    root = _tmp()
    try:
        (root / ".claude").mkdir()
        (root / ".claude" / "continuity.json").write_text("{ broken", encoding="utf-8")
        cfg = ckpt.load_config(root)
        assert "_config_error" in cfg
        assert "continuity.json" in ckpt.build_checkpoint(root, cfg)
    finally:
        shutil.rmtree(root)


# ── write + prune + session-start ──────────────────────────────────────────
def test_write_creates_latest():
    root = _tmp()
    try:
        latest = ckpt.write_checkpoint(root, {})
        assert latest.exists() and latest.name == "latest.md"
        assert (root / ".claude" / "checkpoints").is_dir()
    finally:
        shutil.rmtree(root)


def test_write_prunes_backups():
    root = _tmp()
    try:
        ck_dir = root / ".claude" / "checkpoints"
        ck_dir.mkdir(parents=True)
        # pre-seed 8 fake backups; keep_backups=3 should leave 3 newest after a write
        for i in range(8):
            (ck_dir / f"checkpoint_2026010{i}_000000.md").write_text("old")
        ckpt.write_checkpoint(root, {"keep_backups": 3})
        backups = list(ck_dir.glob("checkpoint_*.md"))
        assert len(backups) == 3, f"expected 3, got {len(backups)}"
    finally:
        shutil.rmtree(root)


def test_session_start_payload_empty_when_missing():
    root = _tmp()
    try:
        assert ckpt.session_start_payload(root, {}) == ""
    finally:
        shutil.rmtree(root)


def test_session_start_payload_json_shape():
    root = _tmp()
    try:
        ck = root / ".claude" / "checkpoints"
        ck.mkdir(parents=True)
        (ck / "latest.md").write_text("BODY LINE\nmore", encoding="utf-8")
        payload = ckpt.session_start_payload(root, {})
        d = json.loads(payload)
        assert d["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "BODY LINE" in d["hookSpecificOutput"]["additionalContext"]
    finally:
        shutil.rmtree(root)


def test_session_start_truncates_long():
    root = _tmp()
    try:
        ck = root / ".claude" / "checkpoints"
        ck.mkdir(parents=True)
        (ck / "latest.md").write_text("\n".join(f"line {i}" for i in range(200)), encoding="utf-8")
        d = json.loads(ckpt.session_start_payload(root, {"inject_max_lines": 10}))
        ctx = d["hookSpecificOutput"]["additionalContext"]
        assert "full: .claude/checkpoints/latest.md" in ctx
        assert ctx.count("\n") < 200
    finally:
        shutil.rmtree(root)


def test_main_write_and_session_start_modes():
    root = _tmp()
    try:
        os.environ["CLAUDE_PROJECT_DIR"] = str(root)
        out_w = _capture(ckpt.main, ["--write"])
        assert "checkpoint written" in out_w
        out_s = _capture(ckpt.main, ["--session-start"])
        assert "hookSpecificOutput" in out_s
    finally:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        shutil.rmtree(root)


def test_root_resolution_prefers_env():
    root = _tmp()
    try:
        os.environ["CLAUDE_PROJECT_DIR"] = str(root)
        assert ckpt.resolve_root() == root.resolve()
        assert ckpt.resolve_root("/tmp") == Path("/tmp").resolve()  # explicit wins
    finally:
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        shutil.rmtree(root)


# ── installer ──────────────────────────────────────────────────────────────
def test_merge_adds_both_idempotent():
    s, changes = install.merge_hooks({})
    assert len(s["hooks"]["PreCompact"]) == 1 and len(s["hooks"]["SessionStart"]) == 1
    assert len(changes) == 2
    s2, changes2 = install.merge_hooks(s)
    assert len(s2["hooks"]["PreCompact"]) == 1 and len(s2["hooks"]["SessionStart"]) == 1
    assert changes2 == []


def test_merge_preserves_existing():
    pre = {"hooks": {"PreCompact": [
        {"matcher": "", "hooks": [{"type": "command", "command": "echo rtk"}]}]}}
    s, _ = install.merge_hooks(pre)
    cmds = [install._command_of(e) for e in s["hooks"]["PreCompact"]]
    assert "echo rtk" in cmds and install.WRITE_CMD in cmds
    assert len(s["hooks"]["PreCompact"]) == 2


def test_unmerge_removes_only_ours():
    s, _ = install.merge_hooks({"hooks": {"PreCompact": [
        {"matcher": "", "hooks": [{"type": "command", "command": "echo rtk"}]}]}})
    s, changes = install.unmerge_hooks(s)
    cmds = [install._command_of(e) for e in s["hooks"]["PreCompact"]]
    assert "echo rtk" in cmds and install.WRITE_CMD not in cmds
    assert s["hooks"]["SessionStart"] == []


def test_install_dry_run_writes_nothing():
    root = _tmp()
    try:
        assert install.install(root, dry=True, with_config=True) == 0
        assert not (root / ".claude" / "settings.json").exists()
        assert not (root / ".claude" / "hooks" / "session_checkpoint.py").exists()
    finally:
        shutil.rmtree(root)


def test_install_full_idempotent():
    root = _tmp()
    try:
        assert install.install(root, dry=False, with_config=True) == 0
        assert (root / ".claude" / "hooks" / "session_checkpoint.py").exists()
        assert (root / "CONTINUITY.md").exists()
        assert (root / ".claude" / "continuity.json").exists()
        s = json.loads((root / ".claude" / "settings.json").read_text())
        assert len(s["hooks"]["PreCompact"]) == 1 and len(s["hooks"]["SessionStart"]) == 1
        assert "checkpoints/" in (root / ".claude" / ".gitignore").read_text()
        install.install(root, dry=False, with_config=True)  # again
        s2 = json.loads((root / ".claude" / "settings.json").read_text())
        assert len(s2["hooks"]["PreCompact"]) == 1 and len(s2["hooks"]["SessionStart"]) == 1
    finally:
        shutil.rmtree(root)


def test_install_uninstall_roundtrip():
    root = _tmp()
    try:
        install.install(root, dry=False, with_config=False)
        install.uninstall(root, dry=False)
        s = json.loads((root / ".claude" / "settings.json").read_text())
        assert s["hooks"]["PreCompact"] == [] and s["hooks"]["SessionStart"] == []
        assert not (root / ".claude" / "hooks" / "session_checkpoint.py").exists()
    finally:
        shutil.rmtree(root)


def test_end_to_end_install_write_restore():
    """Install into a temp project, run --write, then --session-start through the installed copy."""
    if not _HAS_GIT:
        return
    root = _tmp()
    try:
        _git_init(root)
        (root / "CONTINUITY.md").write_text("## Pending\n- ship widget\n", encoding="utf-8")
        install.install(root, dry=False, with_config=False)
        hook = root / ".claude" / "hooks" / "session_checkpoint.py"
        r = subprocess.run([sys.executable, str(hook), "--root", str(root), "--write"],
                           capture_output=True, text=True, timeout=30)
        assert r.returncode == 0, r.stderr
        body = (root / ".claude" / "checkpoints" / "latest.md").read_text()
        assert "## Git" in body and "init commit" in body and "ship widget" in body
        r2 = subprocess.run([sys.executable, str(hook), "--session-start"],
                            capture_output=True, text=True,
                            env={**os.environ, "CLAUDE_PROJECT_DIR": str(root)}, timeout=15)
        d = json.loads(r2.stdout)
        assert "ship widget" in d["hookSpecificOutput"]["additionalContext"]
    finally:
        shutil.rmtree(root)


# ── runner ─────────────────────────────────────────────────────────────────
def _run_all() -> int:
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    passed = failed = 0
    fails: list[str] = []
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  ✓ {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            fails.append(f"{name}: {type(e).__name__}: {e}")
            print(f"  ✗ {name}: {type(e).__name__}: {e}")
    skip = "" if _HAS_GIT else "  [git tests skipped: git not found]"
    print(f"\n{passed} passed, {failed} failed (of {len(tests)}){skip}")
    if fails:
        print("\nFAILURES:")
        for f in fails:
            print(f"  - {f}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run_all())
