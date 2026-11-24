#!/usr/bin/env python3
"""Append a session entry to a project's HISTORY.md (append-only work log).

HISTORY.md is the backward-looking "what happened" timeline — the opposite of
CONTINUITY.md (forward-looking "next actions", kept short & injected at session
start). HISTORY is NEVER injected at session start and NEVER edited/rewritten;
/wrap adds one entry per session at the bottom. For retrospectives, audit, video.

This script only ever APPENDS. It creates HISTORY.md with a header if missing.
It never reads, modifies, or deletes existing entries — safe by construction.

Usage (run from project root, or pass --root). Body comes from stdin:
  python3 ~/.claude/skills/wrap/assets/append_history.py \
      --date 2026-07-09 --title "Shopify 제출 스킬 자산화" --commit abc1234 <<'EOF'
  - 한 일: ...
  - 결정: ...
  - 함정/해법: ...
  EOF

Args:
  --root    project dir (default: $CLAUDE_PROJECT_DIR or cwd)
  --date    entry date, YYYY-MM-DD (required — caller passes it; no clock here)
  --title   short entry title (required)
  --commit  optional commit hash(es) to record
  --file    read body from this file instead of stdin
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

HEADER = """# 📜 프로젝트 히스토리 / Project history (append-only)

> **절대 편집·삭제 금지.** 시간순 "무슨 일이 있었나" 기록.
> CONTINUITY.md(다음 할 일, 짧게 유지, 세션시작 주입)와 **반대 방향**의 문서 —
> 여긴 계속 쌓기만 한다. /wrap이 세션마다 항목을 맨 아래에 추가.
> 용도: 작업 회고록 · 유튜브 영상 · 감사 추적. 새 항목일수록 아래.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Append a session entry to HISTORY.md (append-only).")
    ap.add_argument("--root", default=os.environ.get("CLAUDE_PROJECT_DIR") or ".")
    ap.add_argument("--date", required=True, help="YYYY-MM-DD (caller supplies; no clock here)")
    ap.add_argument("--title", required=True)
    ap.add_argument("--commit", default="")
    ap.add_argument("--file", default="")
    args = ap.parse_args()

    body = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    body = body.strip("\n")
    if not body.strip():
        print("append_history: empty body — nothing appended.", file=sys.stderr)
        return 2

    hist = Path(args.root).resolve() / "HISTORY.md"
    created = not hist.exists()
    if created:
        hist.write_text(HEADER, encoding="utf-8")

    commit_line = f" · `{args.commit}`" if args.commit else ""
    entry = f"\n\n---\n\n## {args.date} — {args.title}{commit_line}\n\n{body}\n"
    with hist.open("a", encoding="utf-8") as f:  # 'a' = append-only, never truncates
        f.write(entry)

    print(f"append_history: {'created + ' if created else ''}appended entry '{args.title}' → {hist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
