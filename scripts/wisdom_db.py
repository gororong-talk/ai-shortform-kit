#!/usr/bin/env python3
"""
wisdom_db.py — 명언/지혜 텍스트 콘텐츠의 데이터 레이어.

사연(stories.db)과 분리된 별도 콘텐츠 種.
시드 JSONL(data/wisdom/*.jsonl)을 받아 wisdom_library.db 의 quotes 테이블에 적재.
외부 크롤/수집 도구가 같은 JSONL 포맷으로 떨어뜨리면 그대로 ingest 가능 (사연의 /ingest-stories 와 동일 패턴).

JSONL 한 줄 = 명언 한 건:
  {id, text, author, source, orig, tradition, theme[], mood, lang_orig, license, verified, note}

사용:
  python scripts/wisdom_db.py init
  python scripts/wisdom_db.py ingest data/wisdom/seed_quotes.jsonl
  python scripts/wisdom_db.py stats
  python scripts/wisdom_db.py list --tradition 불교 --limit 10
  python scripts/wisdom_db.py get bud_001
  python scripts/wisdom_db.py random --n 5 --mood 평온
"""
import argparse
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "wisdom_library.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS quotes (
    id          TEXT PRIMARY KEY,
    text        TEXT NOT NULL,
    author      TEXT,
    source      TEXT,
    orig        TEXT,          -- 원문(한문/원어), 없으면 ''
    tradition   TEXT,          -- 스토아/동양고전/서양철학/문학/성경/불교/위인
    theme       TEXT,          -- 콤마 구분 태그
    mood        TEXT,          -- 평온/각성/단호/위안/경건 (렌더 팔레트 결정)
    lang_orig   TEXT,          -- la/grc/zh/pli/he/en/de/fr/ru/ko
    license     TEXT,          -- public_domain/scripture_ref/fair_use_short
    verified    INTEGER DEFAULT 0,  -- 출처 attribution 교차확인 여부
    note        TEXT,
    is_used     INTEGER DEFAULT 0,  -- 렌더/게시에 쓰였는지
    added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_quotes_tradition ON quotes(tradition);
CREATE INDEX IF NOT EXISTS idx_quotes_mood ON quotes(mood);
"""


def connect():
    return sqlite3.connect(DB_PATH)


def _migrate(con):
    """기존 quotes 테이블에 게시 추적 컬럼을 더한다 (이미 있으면 무시)."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(quotes)")}
    for col, ddl in (
        ("published", "ALTER TABLE quotes ADD COLUMN published INTEGER DEFAULT 0"),   # 실제 업로드됨
        ("published_at", "ALTER TABLE quotes ADD COLUMN published_at TIMESTAMP"),
        ("published_to", "ALTER TABLE quotes ADD COLUMN published_to TEXT"),          # csv: yt,tiktok,ig
    ):
        if col not in cols:
            con.execute(ddl)
    con.commit()


def init_db():
    con = connect()
    con.executescript(SCHEMA)
    _migrate(con)
    con.commit()
    con.close()
    print(f"✅ init: {DB_PATH}")


def _norm(rec):
    """JSONL 레코드를 행 튜플로. theme 배열 → 콤마 문자열."""
    theme = rec.get("theme", [])
    if isinstance(theme, list):
        theme = ",".join(theme)
    return (
        rec["id"],
        rec["text"].strip(),
        rec.get("author", "").strip(),
        rec.get("source", "").strip(),
        rec.get("orig", "").strip(),
        rec.get("tradition", "").strip(),
        theme,
        rec.get("mood", "평온").strip(),
        rec.get("lang_orig", "").strip(),
        rec.get("license", "public_domain").strip(),
        int(rec.get("verified", 0)),
        rec.get("note", "").strip(),
    )


def ingest(paths):
    con = connect()
    con.executescript(SCHEMA)
    _migrate(con)
    ins = upd = bad = 0
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if not isinstance(rec, dict) or not rec.get("id") or not rec.get("text"):
                        bad += 1
                        continue
                    row = _norm(rec)
                except Exception as e:
                    print(f"  ⚠️ {os.path.basename(path)}:{ln} 파싱 실패 — {e}", file=sys.stderr)
                    bad += 1
                    continue
                existed = con.execute("SELECT 1 FROM quotes WHERE id=?", (row[0],)).fetchone()
                con.execute(
                    """INSERT INTO quotes
                       (id,text,author,source,orig,tradition,theme,mood,lang_orig,license,verified,note)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET
                         text=excluded.text, author=excluded.author, source=excluded.source,
                         orig=excluded.orig, tradition=excluded.tradition, theme=excluded.theme,
                         mood=excluded.mood, lang_orig=excluded.lang_orig, license=excluded.license,
                         verified=excluded.verified, note=excluded.note""",
                    row,
                )
                if existed:
                    upd += 1
                else:
                    ins += 1
    con.commit()
    con.close()
    print(f"✅ ingest: 신규 {ins} · 갱신 {upd} · 무시 {bad}")


def _rows_to_dicts(cur):
    cols = [c[0] for c in cur.description]
    out = []
    for r in cur.fetchall():
        d = dict(zip(cols, r))
        if "theme" in d and d["theme"]:
            d["theme"] = d["theme"].split(",")
        out.append(d)
    return out


def cmd_list(args):
    con = connect()
    q = "SELECT * FROM quotes WHERE 1=1"
    p = []
    if args.tradition:
        q += " AND tradition=?"; p.append(args.tradition)
    if args.theme:
        q += " AND theme LIKE ?"; p.append(f"%{args.theme}%")
    if args.mood:
        q += " AND mood=?"; p.append(args.mood)
    if args.verified_only:
        q += " AND verified=1"
    q += " ORDER BY id LIMIT ?"; p.append(args.limit)
    rows = _rows_to_dicts(con.execute(q, p))
    con.close()
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def cmd_get(args):
    con = connect()
    rows = _rows_to_dicts(con.execute("SELECT * FROM quotes WHERE id=?", (args.id,)))
    con.close()
    if not rows:
        print(f"(없음) {args.id}", file=sys.stderr); sys.exit(1)
    print(json.dumps(rows[0], ensure_ascii=False, indent=2))


def cmd_random(args):
    con = connect()
    q = "SELECT * FROM quotes WHERE 1=1"
    p = []
    if args.tradition:
        q += " AND tradition=?"; p.append(args.tradition)
    if args.mood:
        q += " AND mood=?"; p.append(args.mood)
    if args.theme:
        q += " AND theme LIKE ?"; p.append(f"%{args.theme}%")
    q += " ORDER BY RANDOM() LIMIT ?"; p.append(args.n)
    rows = _rows_to_dicts(con.execute(q, p))
    con.close()
    print(json.dumps(rows, ensure_ascii=False, indent=2))


def cmd_mark(args):
    """렌더/게시 상태 표시. 중복 방지의 핵심 — 게시된 명언을 DB에서 따로 관리."""
    con = connect()
    _migrate(con)
    sets, p = [], []
    if args.unused:
        sets.append("is_used=0")
    elif args.used:
        sets.append("is_used=1")
    if args.published:
        sets += ["published=1", "is_used=1", "published_at=CURRENT_TIMESTAMP"]
        if args.platform:
            sets.append("published_to=?"); p.append(args.platform)
    if args.unpublish:
        sets += ["published=0", "published_at=NULL", "published_to=NULL"]
    if not sets:
        sets.append("is_used=1")  # 기본: 사용됨 표시
    ph = ",".join("?" for _ in args.ids)
    cur = con.execute(f"UPDATE quotes SET {', '.join(sets)} WHERE id IN ({ph})", p + args.ids)
    con.commit()
    print(f"✅ mark: {cur.rowcount}건 갱신 — {', '.join(sets)} | ids={args.ids}")
    con.close()


def cmd_stats(args):
    con = connect()
    _migrate(con)
    total = con.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
    used = con.execute("SELECT COUNT(*) FROM quotes WHERE is_used=1").fetchone()[0]
    pub = con.execute("SELECT COUNT(*) FROM quotes WHERE published=1").fetchone()[0]
    print(f"총 {total} 건  ·  렌더(is_used) {used}  ·  게시(published) {pub}  ·  미사용(fresh) {total-used}\n")
    print("── tradition ──")
    for trad, n in con.execute("SELECT tradition, COUNT(*) FROM quotes GROUP BY tradition ORDER BY 2 DESC"):
        print(f"  {trad or '(미지정)':10} {n}")
    print("── mood ──")
    for mood, n in con.execute("SELECT mood, COUNT(*) FROM quotes GROUP BY mood ORDER BY 2 DESC"):
        print(f"  {mood or '(미지정)':10} {n}")
    v = con.execute("SELECT COUNT(*) FROM quotes WHERE verified=1").fetchone()[0]
    print(f"\n출처 교차확인(verified=1): {v}/{total}")
    con.close()


def main():
    ap = argparse.ArgumentParser(description="명언 데이터 레이어 (wisdom_library.db)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    pi = sub.add_parser("ingest"); pi.add_argument("paths", nargs="+")
    pl = sub.add_parser("list")
    pl.add_argument("--tradition"); pl.add_argument("--theme"); pl.add_argument("--mood")
    pl.add_argument("--verified-only", action="store_true"); pl.add_argument("--limit", type=int, default=20)
    pg = sub.add_parser("get"); pg.add_argument("id")
    pr = sub.add_parser("random")
    pr.add_argument("--n", type=int, default=5); pr.add_argument("--tradition")
    pr.add_argument("--mood"); pr.add_argument("--theme")
    pm = sub.add_parser("mark", help="렌더/게시 상태 표시 (중복 방지)")
    pm.add_argument("ids", nargs="+")
    pm.add_argument("--used", action="store_true", help="is_used=1")
    pm.add_argument("--unused", action="store_true", help="is_used=0 (리셋)")
    pm.add_argument("--published", action="store_true", help="published=1 + is_used=1 (실제 업로드)")
    pm.add_argument("--platform", help="게시처 csv: yt,tiktok,ig")
    pm.add_argument("--unpublish", action="store_true", help="published 취소")
    sub.add_parser("stats")
    args = ap.parse_args()

    if args.cmd == "init":
        init_db()
    elif args.cmd == "ingest":
        ingest(args.paths)
    elif args.cmd == "list":
        cmd_list(args)
    elif args.cmd == "get":
        cmd_get(args)
    elif args.cmd == "random":
        cmd_random(args)
    elif args.cmd == "mark":
        cmd_mark(args)
    elif args.cmd == "stats":
        cmd_stats(args)


if __name__ == "__main__":
    main()
