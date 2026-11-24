"""analytics_ingest.py — inbox 폴더의 성과 데이터를 DB로 수집.

지원 입력:
  - 스크린샷 (.png/.jpg/.jpeg) → Claude 비전 파싱 (수동 검토 모드 / 또는 --vision-json 으로 사전 추출본 주입)
  - CSV (TikTok Studio / YouTube Studio / 직접 작성) → 컬럼 자동 매핑
  - JSON (구조화된 수동 입력) → 직접 삽입

사용:
  python scripts/analytics_ingest.py                 # inbox 스캔 (CSV/JSON 자동 처리, 스크린샷은 목록만)
  python scripts/analytics_ingest.py --csv <file>    # 특정 CSV 처리
  python scripts/analytics_ingest.py --json <file>   # 구조화 JSON 처리
  python scripts/analytics_ingest.py --manual        # 대화형 1건 입력 (인자 플래그)

스크린샷 파싱 워크플로우 (Claude 세션):
  1. 사용자가 스크린샷을 analytics/inbox/ 에 던짐
  2. Claude(메인 세션)가 Read 로 이미지 보고 숫자 추출
  3. 추출 결과를 JSON 으로 만들어 --json 으로 주입 (아래 JSON 포맷)
  → 별도 비전 API 호출 없이 메인 세션이 직접 읽는 게 가장 정확·저비용
"""
import os
import sys
import csv
import json
import shutil
import argparse
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import analytics_db as adb

INBOX = os.path.join(ROOT, "analytics", "inbox")
PROCESSED = os.path.join(INBOX, "_processed")
KST = timezone(timedelta(hours=9))

# CSV 컬럼명 → 우리 스키마 매핑 (플랫폼별 export 헤더 변형 흡수)
COL_ALIASES = {
    "views": ["views", "video views", "play count", "plays", "조회수", "조회"],
    "likes": ["likes", "like count", "좋아요"],
    "comments": ["comments", "comment count", "댓글"],
    "shares": ["shares", "share count", "공유"],
    "saves": ["saves", "saved", "bookmarks", "저장"],
    "avg_watch_sec": ["average watch time", "avg watch time", "average view duration",
                      "avg_watch_sec", "평균 시청 시간", "평균시청시간"],
    "completion_rate": ["completion rate", "completed", "watched full video",
                        "completion_rate", "완주율", "시청 완료율"],
    "reach": ["reach", "accounts reached", "도달", "도달수"],
    "profile_visits": ["profile visits", "profile views", "프로필 조회", "프로필 방문"],
}


def _norm(s):
    return (s or "").strip().lower()


def _map_columns(headers):
    """CSV 헤더 → {our_field: csv_index}."""
    mapping = {}
    low = [_norm(h) for h in headers]
    for field, aliases in COL_ALIASES.items():
        for a in aliases:
            if _norm(a) in low:
                mapping[field] = low.index(_norm(a))
                break
    return mapping


def _to_num(s):
    if s is None:
        return None
    s = str(s).strip().replace(",", "").replace("%", "")
    if not s or s in ("-", "—", "N/A"):
        return None
    try:
        return float(s) if "." in s else int(s)
    except ValueError:
        return None


def ingest_csv(path, platform=None, slug=None, measured_at=None):
    """CSV 1개 처리. 각 행 = 영상 1개로 가정. platform/slug 없으면 파일명·컬럼에서 추론 시도."""
    measured_at = measured_at or datetime.now(KST).isoformat()
    c = adb.conn()
    n = 0
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        headers = next(reader, [])
        colmap = _map_columns(headers)
        low = [_norm(h) for h in headers]
        # video id / title 컬럼 추론
        vid_idx = next((low.index(x) for x in ["video id", "video", "url", "link", "id"] if x in low), None)
        title_idx = next((low.index(x) for x in ["title", "caption", "name", "제목"] if x in low), None)
        plat_idx = next((low.index(x) for x in ["platform", "플랫폼"] if x in low), None)
        slug_idx = next((low.index(x) for x in ["slug", "production"] if x in low), None)
        for row in reader:
            if not row or not any(row):
                continue
            pid = row[vid_idx].strip() if vid_idx is not None and vid_idx < len(row) else f"{os.path.basename(path)}_{n}"
            plat = (row[plat_idx].strip() if plat_idx is not None and plat_idx < len(row) else None) or platform or "unknown"
            sg = (row[slug_idx].strip() if slug_idx is not None and slug_idx < len(row) else None) or slug
            title = row[title_idx].strip() if title_idx is not None and title_idx < len(row) else None
            vid = adb.upsert_video(c, sg, plat, pid, title=title)
            metric = {field: _to_num(row[idx]) for field, idx in colmap.items() if idx < len(row)}
            # completion_rate 가 % 로 들어오면 0~1 로 정규화
            if metric.get("completion_rate") and metric["completion_rate"] > 1:
                metric["completion_rate"] = metric["completion_rate"] / 100.0
            adb.insert_metric(c, vid, measured_at, source="csv", **metric)
            n += 1
    c.close()
    print(f"  ✅ CSV {os.path.basename(path)}: {n}개 영상 처리")
    return n


def ingest_json(path):
    """구조화 JSON 처리. 포맷:
    {
      "measured_at": "2026-05-31T10:00",   // 선택, 없으면 now
      "records": [
        {"slug":"...", "platform":"tiktok", "platform_video_id":"...",
         "title":"...", "posted_at":"2026-05-26", "duration_sec":51.4, "age_hours":24,
         "views":358, "likes":12, "comments":3, "shares":2,
         "avg_watch_sec":18.2, "completion_rate":0.34, "reach":..., "profile_visits":...}
      ]
    }
    스크린샷에서 메인 세션이 추출한 값을 이 포맷으로 만들어 주입하는 게 표준 경로.
    """
    data = json.loads(open(path, encoding="utf-8").read())
    measured_at = data.get("measured_at") or datetime.now(KST).isoformat()
    c = adb.conn()
    n = 0
    for r in data.get("records", []):
        vid = adb.upsert_video(
            c, r.get("slug"), r["platform"], r["platform_video_id"],
            title=r.get("title"), posted_at=r.get("posted_at"),
            duration_sec=r.get("duration_sec"),
        )
        adb.insert_metric(
            c, vid, r.get("measured_at", measured_at),
            source=r.get("source", "screenshot"),
            age_hours=r.get("age_hours"), views=r.get("views"), likes=r.get("likes"),
            comments=r.get("comments"), shares=r.get("shares"), saves=r.get("saves"),
            avg_watch_sec=r.get("avg_watch_sec"), completion_rate=r.get("completion_rate"),
            reach=r.get("reach"), profile_visits=r.get("profile_visits"),
            raw=r,
        )
        n += 1
    c.close()
    print(f"  ✅ JSON {os.path.basename(path)}: {n}개 레코드 처리")
    return n


def scan_inbox():
    """inbox 스캔 — CSV/JSON 자동 처리, 스크린샷은 목록만 보고."""
    if not os.path.isdir(INBOX):
        print(f"❌ inbox 없음: {INBOX}")
        return
    os.makedirs(PROCESSED, exist_ok=True)
    files = [f for f in os.listdir(INBOX)
             if os.path.isfile(os.path.join(INBOX, f)) and not f.startswith(".")]
    if not files:
        print("inbox 비어 있음.")
        return
    csvs = [f for f in files if f.lower().endswith(".csv")]
    jsons = [f for f in files if f.lower().endswith(".json")]
    imgs = [f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]

    print(f"=== inbox 스캔: CSV {len(csvs)} / JSON {len(jsons)} / 스크린샷 {len(imgs)} ===\n")

    for f in csvs:
        ingest_csv(os.path.join(INBOX, f))
        shutil.move(os.path.join(INBOX, f), os.path.join(PROCESSED, f))
    for f in jsons:
        ingest_json(os.path.join(INBOX, f))
        shutil.move(os.path.join(INBOX, f), os.path.join(PROCESSED, f))

    if imgs:
        print(f"\n📸 스크린샷 {len(imgs)}개 — 메인 세션(Claude)이 직접 읽어야 합니다:")
        for f in imgs:
            print(f"   - analytics/inbox/{f}")
        print("\n   → Claude 에게 '스크린샷 파싱해줘' 라고 하면 Read 로 숫자 추출 후 JSON 주입.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv")
    ap.add_argument("--json")
    ap.add_argument("--platform")
    ap.add_argument("--slug")
    args = ap.parse_args()
    if args.csv:
        ingest_csv(args.csv, platform=args.platform, slug=args.slug)
    elif args.json:
        ingest_json(args.json)
    else:
        scan_inbox()


if __name__ == "__main__":
    main()
