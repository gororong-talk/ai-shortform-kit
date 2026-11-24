#!/usr/bin/env python3
"""Bootstrap the continuity/checkpoint setup into a project so /wrap works fully.

Idempotent — safe to re-run; never clobbers existing config. Installs (only what's missing):
  .claude/hooks/session_checkpoint.py   (bundled portable script)
  .claude/settings.json hooks           (PreCompact --write + SessionStart "" --write→--session-start)
  CONTINUITY.md                         (from template)

Usage (run from project root, or pass --root):
  python3 ~/.claude/skills/wrap/assets/setup_continuity.py [--root <dir>]

Detection: a project is "set up" when .claude/hooks/session_checkpoint.py exists
AND a handoff doc (CONTINUITY.md) exists AND settings.json has a SessionStart
checkpoint hook. This installer fills whichever pieces are missing.
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
from pathlib import Path

ASSETS = Path(__file__).resolve().parent
SCRIPT_SRC = ASSETS / "session_checkpoint.py"
CONT_TMPL = ASSETS / "CONTINUITY.template.md"

PRECOMPACT_CMD = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/session_checkpoint.py" --write'
SESSIONSTART_CMD = (
    'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/session_checkpoint.py" --write >/dev/null 2>&1; '
    'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/session_checkpoint.py" --session-start'
)


def _has_checkpoint_hook(arr) -> bool:
    for group in arr or []:
        for h in group.get("hooks", []):
            if "session_checkpoint.py" in (h.get("command") or ""):
                return True
    return False


def _ensure_hook(settings: dict, event: str, command: str, timeout: int) -> bool:
    settings.setdefault("hooks", {})
    arr = settings["hooks"].setdefault(event, [])
    if _has_checkpoint_hook(arr):
        return False
    arr.append({"matcher": "", "hooks": [{"type": "command", "command": command, "timeout": timeout}]})
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Install continuity/checkpoint setup for /wrap.")
    ap.add_argument("--root", default=os.environ.get("CLAUDE_PROJECT_DIR") or ".")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    log: list[str] = []

    # 1) checkpoint script
    hooks_dir = root / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    dst = hooks_dir / "session_checkpoint.py"
    if not dst.exists():
        shutil.copy2(SCRIPT_SRC, dst)
        log.append(f"+ .claude/hooks/session_checkpoint.py (설치)")
    else:
        log.append(f"= .claude/hooks/session_checkpoint.py (이미 있음)")

    # 2) settings.json hooks (merge, never clobber)
    sp = root / ".claude" / "settings.json"
    settings: dict = {}
    if sp.exists():
        try:
            settings = json.loads(sp.read_text(encoding="utf-8"))
        except Exception:
            log.append("⚠️ 기존 settings.json 파싱 실패 → 훅 자동추가 건너뜀(수동 확인 필요)")
            settings = None  # type: ignore
    if settings is not None:
        a = _ensure_hook(settings, "PreCompact", PRECOMPACT_CMD, 30)
        b = _ensure_hook(settings, "SessionStart", SESSIONSTART_CMD, 20)
        if a or b:
            sp.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            tag = " + ".join(t for t, on in (("PreCompact", a), ("SessionStart", b)) if on)
            log.append(f"+ .claude/settings.json 훅 추가: {tag}")
        else:
            log.append("= .claude/settings.json (checkpoint 훅 이미 있음)")

    # 3) CONTINUITY.md
    cont = root / "CONTINUITY.md"
    if not cont.exists():
        shutil.copy2(CONT_TMPL, cont)
        log.append("+ CONTINUITY.md (템플릿 생성 — '## Pending'에 다음 할 일 적기)")
    else:
        log.append("= CONTINUITY.md (이미 있음)")

    print("✅ continuity 부트스트랩 완료:")
    for line in log:
        print("  ", line)
    print("→ 이제 이 프로젝트에서 /wrap 풀 작동 + /clear·재시작 후 체크포인트 자동 복원.")
    print("   (git 저장소가 아니면 git init 권장 — /wrap의 커밋 단계용)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
