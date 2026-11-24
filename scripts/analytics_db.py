"""analytics.db — 멀티플랫폼 콘텐츠 성과 저장 레이어.

스키마: videos (production slug ↔ 플랫폼 매핑) / metrics (성과 시계열) / retention (초단위 곡선)
사용:
  python scripts/analytics_db.py --init          # DB 초기화
  python scripts/analytics_db.py --show           # 현황 요약
  python scripts/analytics_db.py --list           # 영상 목록
"""
import os
import sys
import json
import sqlite3
import argparse
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "analytics", "analytics.db")

KST = timezone(timedelta(hours=9))

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT,
    platform TEXT NOT NULL,
    platform_video_id TEXT NOT NULL,
    title TEXT,
    posted_at TEXT,
    duration_sec REAL,
    post_id TEXT,             -- 사연 story_id (stories stories.post_id) — analytics→CVDE 역추적 다리
    created_at TEXT,
    UNIQUE(platform, platform_video_id)
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL REFERENCES videos(id),
    measured_at TEXT NOT NULL,
    age_hours INTEGER,
    views INTEGER,
    likes INTEGER,
    comments INTEGER,
    shares INTEGER,
    saves INTEGER,
    avg_watch_sec REAL,
    completion_rate REAL,
    reach INTEGER,
    profile_visits INTEGER,
    source TEXT,
    raw_json TEXT,
    UNIQUE(video_id, measured_at)
);

CREATE TABLE IF NOT EXISTS retention (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id INTEGER NOT NULL REFERENCES videos(id),
    measured_at TEXT NOT NULL,
    curve_json TEXT,
    UNIQUE(video_id, measured_at)
);

CREATE INDEX IF NOT EXISTS idx_metrics_video ON metrics(video_id);
CREATE INDEX IF NOT EXISTS idx_videos_slug ON videos(slug);
CREATE INDEX IF NOT EXISTS idx_videos_post ON videos(post_id);
"""


def _migrate(c):
    """기존 DB에 누락된 컬럼을 멱등 추가. 신규 DB는 SCHEMA가 이미 가지므로 no-op.

    videos.post_id = analytics→사연(CVDE) 역추적 다리. 이 컬럼이 없으면 완주율을
    slug까지만 따라갈 수 있고 story_id/CVDE 하위점수로는 못 잇는다 (2026-06-28 박제).
    """
    has_videos = c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='videos'").fetchone()
    if not has_videos:
        return
    cols = {r[1] for r in c.execute("PRAGMA table_info(videos)")}
    if "post_id" not in cols:
        c.execute("ALTER TABLE videos ADD COLUMN post_id TEXT")
        c.execute("CREATE INDEX IF NOT EXISTS idx_videos_post ON videos(post_id)")
        c.commit()


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    _migrate(c)
    return c


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = conn()
    c.executescript(SCHEMA)
    c.commit()
    c.close()
    print(f"✅ DB 초기화: {DB_PATH}")


def norm_posted_at(s, today=None):
    """플랫폼마다 다른 게시일 문자열 → 'YYYY-MM-DD'. 못 읽으면 원문 그대로(정보 보존).

    2026-11-17: YT CSV='Aug 10, 2026', TikTok='5월 24일'(연도 없음), 나머지 ISO 가 섞여
    날짜 계산이 깨졌다. 연도 없는 한국어는 올해로 보되, 미래가 되면 작년으로.
    """
    if not s:
        return s
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(s[:10] if fmt == "%Y-%m-%d" else s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    import re
    m = re.fullmatch(r"(\d{1,2})월\s*(\d{1,2})일", s)
    if m:
        today = today or datetime.now(KST).date()
        d = today.replace(month=int(m[1]), day=int(m[2]))
        if d > today:
            d = d.replace(year=d.year - 1)
        return d.isoformat()
    return s


def upsert_video(c, slug, platform, platform_video_id, title=None,
                 posted_at=None, duration_sec=None, post_id=None):
    """영상 등록 (있으면 메타 갱신). video_id 반환.

    post_id(사연 story_id)를 주면 forward-fill로 다리를 즉시 박는다. 안 줘도
    build_cvde_labels.py 의 self-heal 백필이 slug→00_meta.json 으로 사후 보정한다.
    """
    posted_at = norm_posted_at(posted_at)
    now = datetime.now(KST).isoformat()
    c.execute("""
        INSERT INTO videos (slug, platform, platform_video_id, title, posted_at, duration_sec, post_id, created_at)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(platform, platform_video_id) DO UPDATE SET
            slug=COALESCE(excluded.slug, videos.slug),
            title=COALESCE(excluded.title, videos.title),
            posted_at=COALESCE(excluded.posted_at, videos.posted_at),
            duration_sec=COALESCE(excluded.duration_sec, videos.duration_sec),
            post_id=COALESCE(excluded.post_id, videos.post_id)
    """, (slug, platform, platform_video_id, title, posted_at, duration_sec, post_id, now))
    c.commit()
    row = c.execute(
        "SELECT id FROM videos WHERE platform=? AND platform_video_id=?",
        (platform, platform_video_id)
    ).fetchone()
    return row["id"]


def insert_metric(c, video_id, measured_at, source="manual", **kwargs):
    """성과 측정 1건 삽입 (같은 video_id+measured_at 이면 갱신)."""
    fields = ["views", "likes", "comments", "shares", "saves",
              "avg_watch_sec", "completion_rate", "reach", "profile_visits", "age_hours"]
    vals = {f: kwargs.get(f) for f in fields}
    raw = json.dumps(kwargs.get("raw", {}), ensure_ascii=False)
    c.execute("""
        INSERT INTO metrics (video_id, measured_at, age_hours, views, likes, comments,
            shares, saves, avg_watch_sec, completion_rate, reach, profile_visits, source, raw_json)
        VALUES (:vid,:m,:age_hours,:views,:likes,:comments,:shares,:saves,
            :avg_watch_sec,:completion_rate,:reach,:profile_visits,:src,:raw)
        ON CONFLICT(video_id, measured_at) DO UPDATE SET
            views=COALESCE(excluded.views, metrics.views),
            likes=COALESCE(excluded.likes, metrics.likes),
            comments=COALESCE(excluded.comments, metrics.comments),
            shares=COALESCE(excluded.shares, metrics.shares),
            saves=COALESCE(excluded.saves, metrics.saves),
            avg_watch_sec=COALESCE(excluded.avg_watch_sec, metrics.avg_watch_sec),
            completion_rate=COALESCE(excluded.completion_rate, metrics.completion_rate),
            reach=COALESCE(excluded.reach, metrics.reach),
            profile_visits=COALESCE(excluded.profile_visits, metrics.profile_visits),
            source=excluded.source, raw_json=excluded.raw_json
    """, {"vid": video_id, "m": measured_at, "src": source, "raw": raw, **vals})
    c.commit()


def show():
    if not os.path.exists(DB_PATH):
        print("❌ DB 없음 — python scripts/analytics_db.py --init 먼저 실행")
        return
    c = conn()
    nv = c.execute("SELECT COUNT(*) n FROM videos").fetchone()["n"]
    nm = c.execute("SELECT COUNT(*) n FROM metrics").fetchone()["n"]
    print(f"=== analytics.db 현황 ===")
    print(f"영상: {nv}개 / 측정 기록: {nm}건")
    print()
    by_plat = c.execute("SELECT platform, COUNT(*) n FROM videos GROUP BY platform").fetchall()
    for r in by_plat:
        print(f"  {r['platform']}: {r['n']}개")
    c.close()


def list_videos():
    c = conn()
    rows = c.execute("""
        SELECT v.slug, v.platform, v.title,
               m.views, m.completion_rate, m.measured_at
        FROM videos v
        LEFT JOIN metrics m ON m.video_id = v.id
        ORDER BY v.posted_at DESC, v.platform
    """).fetchall()
    if not rows:
        print("(영상 없음)")
        return
    print(f"{'slug':<32} {'plat':<10} {'views':>7} {'완주율':>7}  측정일")
    print("-" * 80)
    for r in rows:
        cr = f"{r['completion_rate']*100:.0f}%" if r["completion_rate"] else "-"
        v = r["views"] if r["views"] else "-"
        print(f"{(r['slug'] or '?')[:32]:<32} {r['platform']:<10} {str(v):>7} {cr:>7}  {r['measured_at'] or '-'}")
    c.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.init:
        init_db()
    elif args.show:
        show()
    elif args.list:
        list_videos()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
