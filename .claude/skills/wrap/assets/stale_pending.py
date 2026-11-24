#!/usr/bin/env python3
"""List CONTINUITY.md "## Pending" items that have gone stale (default: 3+ days).

Read-only by construction: this script never writes, edits, or deletes anything.
/wrap runs it to FIND records that have sat in Pending too long, then asks the
user per item whether to keep / rewrite / delete. Deciding alone is a bug.

Age of an item, in this order:
  1. a YYYY-MM-DD at the very start of the item (after the bullet / checkbox / `**`);
     dates later in the text are references ("fixed in 2026-11-03 ...") and are ignored
  2. `git blame` author-time of that line (how long the line has sat there)
  3. unknown -> reported as `age=?` and NEVER counted as stale

Usage (run from project root, or pass --root):
  python3 ~/.claude/skills/wrap/assets/stale_pending.py
  python3 ~/.claude/skills/wrap/assets/stale_pending.py --days 7
  python3 ~/.claude/skills/wrap/assets/stale_pending.py --today 2026-11-09

Checkbox items (`- [ ]` / `- [x]`) are listed one by one — those are the actual
records to keep/delete. Plain prose bullets inside Pending are summarized as ONE
aggregate line: they are log text that belongs in HISTORY, not 30 questions.

Exit: 0 on success (the count is in the output), 2 if CONTINUITY.md or its "## Pending" heading is missing.
"""
from __future__ import annotations
import argparse
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
# Only a date that opens the item is its age; a date quoted mid-sentence is a reference.
HEAD_DATE_RE = re.compile(r"^\s*(?:>\s*)*(?:[-*+]|\d+\.)\s+(?:\[[ xX]\]\s+)?(?:\*\*)?[(\[]?(\d{4})-(\d{2})-(\d{2})")
ITEM_RE = re.compile(r"^\s*(?:>\s*)*(?:[-*+]|\d+\.)\s+\S")
BOX_RE = re.compile(r"^\s*(?:>\s*)*(?:[-*+]|\d+\.)\s+\[[ xX]\]")
BLAME_HDR_RE = re.compile(r"^[0-9a-f]{40} \d+ (\d+)")


def pending_items(text: str) -> list[tuple[int, str]]:
    """List-item lines inside the '## Pending' section, as (lineno, line)."""
    items, inside = [], False
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            inside = line.startswith("## Pending")
            continue
        if inside and ITEM_RE.match(line):
            items.append((i, line.rstrip()))
    return items


def blame_times(root: Path, rel: str) -> dict[int, int]:
    """line number -> author-time (epoch). Empty dict if not a git repo."""
    try:
        r = subprocess.run(
            ["git", "blame", "--line-porcelain", "--", rel],
            cwd=root, capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    if r.returncode != 0:
        return {}
    out, lineno = {}, None
    for ln in r.stdout.splitlines():
        m = BLAME_HDR_RE.match(ln)
        if m:
            lineno = int(m.group(1))
        elif lineno and ln.startswith("author-time "):
            out[lineno] = int(ln.split()[1])
    return out


def age_of(line: str, lineno: int, blame: dict[int, int], today: date):
    """(age_in_days, source) — (None, '?') when undecidable."""
    m = HEAD_DATE_RE.match(line)
    if m:
        try:
            return (today - date(*map(int, m.groups()))).days, "date"
        except ValueError:
            pass
    ts = blame.get(lineno)
    if ts is not None:
        return (today - datetime.fromtimestamp(ts).date()).days, "blame"
    return None, "?"


def _selfcheck() -> None:
    t = date(2026, 11, 12)
    assert age_of("- [ ] **2026-11-01 deploy** x", 1, {}, t) == (11, "date")
    assert age_of("- [ ] 2026-11-10 note", 1, {}, t) == (2, "date")
    assert age_of("- [ ] fix (see 2026-01-01 report)", 1, {}, t) == (None, "?")  # reference, not age
    assert age_of("- [ ] fix (see 2026-01-01 report)", 1, {1: datetime(2026, 11, 11).timestamp()}, t) == (1, "blame")
    # blockquote-wrapped Pending (e.g. RESTART_PROTOCOL.md `> 1. **2026-11-01 …`)
    assert age_of("> 1. **2026-11-01 deploy**", 1, {}, t) == (11, "date")
    assert pending_items("## Pending (x)\n> 0. a\n>    ① b\n## Next\n- c") == [(2, "> 0. a")]


def main() -> int:
    _selfcheck()
    ap = argparse.ArgumentParser(description="Find stale CONTINUITY.md Pending items (read-only).")
    ap.add_argument("--root", default=os.environ.get("CLAUDE_PROJECT_DIR") or ".")
    ap.add_argument("--days", type=int, default=3, help="stale threshold in days (default 3)")
    ap.add_argument("--today", default="", help="YYYY-MM-DD (default: system date)")
    ap.add_argument("--file", default="CONTINUITY.md", help="Pending file relative to root (default CONTINUITY.md)")
    ap.add_argument("--max", type=int, default=12, help="max checkbox items to print (default 12)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    cont = root / args.file
    if not cont.exists():
        print(f"stale_pending: {cont} 없음 — 묵힌 기록 점검 스킵.", file=sys.stderr)
        return 2

    today = date.today()
    if args.today:
        try:
            today = date(*map(int, DATE_RE.match(args.today).groups()))
        except (AttributeError, ValueError):
            print("stale_pending: --today 는 YYYY-MM-DD 형식.", file=sys.stderr)
            return 2

    text = cont.read_text(encoding="utf-8")
    if not re.search(r"^## Pending", text, re.M):
        # 2026-11-12: a heading merged into a blockquote line made this report "0 items" for 3 days.
        print(f"ERROR: no '## Pending' heading in {args.file} (broken or renamed) — fix the file first")
        return 2
    items = pending_items(text)
    blame = blame_times(root, args.file)

    stale, notes, unknown = [], [], 0
    for lineno, line in items:
        age, src = age_of(line, lineno, blame, today)
        if age is None:
            unknown += 1
            continue
        if age < args.days:
            continue
        (stale if BOX_RE.match(line) else notes).append((lineno, age, src, line))

    print(f"{args.file} ## Pending — 묵힌 항목 (기준 {args.days}일, today={today})")
    for lineno, age, src, line in stale[: args.max]:
        done = "완료" if re.search(r"\[[xX]\]", line) else "미완료"
        print(f"  L{lineno}  age={age}d  ({src},{done})  {line.strip()[:110]}")
    if len(stale) > args.max:
        print(f"  ... 체크박스 항목 {len(stale) - args.max}건 더 (--max 로 늘림)")
    if notes:
        lines = ", ".join(f"L{n}" for n, *_ in notes[:12]) + ("..." if len(notes) > 12 else "")
        print(f"  [서술형 {len(notes)}줄] {lines} — 다음 액션이 아닌 기록 → HISTORY 이전 후보(한 건으로 묻기)")
    print(f"STALE: 체크박스 {len(stale)} + 서술형 {len(notes)} / 총 {len(items)} 항목 (판정불가 {unknown})")
    if stale or notes:
        print("→ 각 항목을 사용자에게 유지/재작성/삭제로 물어볼 것. 자동 삭제 금지.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
