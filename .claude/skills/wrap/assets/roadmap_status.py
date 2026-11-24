#!/usr/bin/env python3
"""Measure ROADMAP.md milestone progress and refresh its "현재 위치" line.

Big picture + where we are, derived from the file itself — no guessing:
  milestone = a `## M<n> <name>` heading
  progress  = the `- [ ]` / `- [x]` checkboxes under it
  현재 위치 = the first milestone that still has an unchecked box

Default run is read-only (prints the table). `--sync` rewrites ONE line — the
`> **현재 위치:** …` line — from the checkbox state, so it can never drift from
reality. Everything else in ROADMAP.md is left untouched.

Usage (from project root, or pass --root):
  python3 ~/.claude/skills/wrap/assets/roadmap_status.py
  python3 ~/.claude/skills/wrap/assets/roadmap_status.py --sync

Exit: 0 on success, 2 if ROADMAP.md is missing (a project may legitimately have
none — the global rule keeps ROADMAP for 3+ stage long projects only).
"""
from __future__ import annotations
import argparse
import os
import re
import sys
from pathlib import Path

# status glyph before the key is allowed: `## ✅ M0 — name`, `## ▶ M9 — name`
MILESTONE_RE = re.compile(r"^##\s+(?:[^\w\s]+\s+)?(M\d+)\s*[\.\-—:·]?\s*(.*)$")
BOX_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\[([ xX])\]\s*(.*)$")
MARKER_RE = re.compile(r"^>\s*\*\*현재 위치:\*\*")
BAR_FULL, BAR_EMPTY, BAR_WIDTH = "█", "░", 12


def parse(text: str):
    """[{key, name, done, total, next}] in file order."""
    out, cur = [], None
    for line in text.splitlines():
        m = MILESTONE_RE.match(line)
        if m:
            cur = {"key": m.group(1), "name": m.group(2).strip(), "done": 0, "total": 0, "next": ""}
            out.append(cur)
            continue
        if cur is None:
            continue
        b = BOX_RE.match(line)
        if b:
            cur["total"] += 1
            if b.group(1) in "xX":
                cur["done"] += 1
            elif not cur["next"]:
                cur["next"] = b.group(2).strip()
    return out


def _selfcheck() -> None:
    assert [m["key"] for m in parse("## ✅ M0 — a\n- [x] t\n## ▶ M9 — b\n- [ ] u\n## M10 c")] == ["M0", "M9", "M10"]
    assert parse("## 📍 현재 위치: M11")[:1] == []


def status_of(ms: dict) -> str:
    if ms["total"] and ms["done"] == ms["total"]:
        return "완료"
    return "진행중" if ms["done"] else "대기"


def marker_line(stones: list[dict]) -> str:
    current = next((m for m in stones if status_of(m) != "완료"), None)
    if current is None:
        total = sum(m["total"] for m in stones)
        return f"> **현재 위치:** 전체 마일스톤 완료 ({total}/{total})"
    nxt = current["next"] or "다음 항목 미정"
    return (f"> **현재 위치:** {current['key']} {current['name']} · "
            f"{current['done']}/{current['total']} 완료 · 다음: {nxt}")


def main() -> int:
    _selfcheck()
    ap = argparse.ArgumentParser(description="ROADMAP.md milestone progress (read-only unless --sync).")
    ap.add_argument("--root", default=os.environ.get("CLAUDE_PROJECT_DIR") or ".")
    ap.add_argument("--sync", action="store_true", help="rewrite the '현재 위치' line from checkbox state")
    args = ap.parse_args()

    road = Path(args.root).resolve() / "ROADMAP.md"
    if not road.exists():
        print(f"roadmap_status: {road} 없음 — 로드맵 단계 스킵.", file=sys.stderr)
        return 2

    text = road.read_text(encoding="utf-8")
    stones = parse(text)
    if not stones:
        print("roadmap_status: '## M<n> …' 마일스톤 헤딩이 없음 — 형식 확인 필요.", file=sys.stderr)
        return 2

    print(f"ROADMAP.md — 마일스톤 {len(stones)}개")
    for m in stones:
        filled = round(BAR_WIDTH * m["done"] / m["total"]) if m["total"] else 0
        bar = BAR_FULL * filled + BAR_EMPTY * (BAR_WIDTH - filled)
        print(f"  {m['key']:<4} {bar} {m['done']:>2}/{m['total']:<2} {status_of(m):<4} {m['name'][:52]}")
    want = marker_line(stones)
    print(want.replace("> ", "  ", 1))

    if not args.sync:
        return 0

    lines = text.splitlines()
    for i, line in enumerate(lines):
        if MARKER_RE.match(line):
            if line.rstrip() == want:
                print("sync: 현재 위치 줄 이미 최신 — 변경 없음.")
                return 0
            lines[i] = want
            road.write_text("\n".join(lines) + "\n", encoding="utf-8")
            print(f"sync: 현재 위치 줄 갱신 (L{i + 1}).")
            return 0

    insert_at = next((i + 1 for i, l in enumerate(lines) if l.startswith("# ")), 0)
    lines.insert(insert_at, "")
    lines.insert(insert_at + 1, want)
    road.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"sync: 현재 위치 줄 신규 삽입 (L{insert_at + 2}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
