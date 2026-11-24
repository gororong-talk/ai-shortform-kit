"""TikTok Content.csv → analytics.db. video_id 앵커 정규식 파싱 (깨진 따옴표 대응).

★ 2026-06-24 자동화(#6): 예전엔 신규 TikTok 게시마다 이 파일의 VID dict와 MEAS 상수를
   '소스코드 직접 편집'으로 갱신해야 했다(안 하면 행이 slug 매칭 실패 → vid 그대로 적재).
   이제 video_id→slug 매핑을 게시대장(_pubmeta.published.tiktok.url)에서 자동 도출하고,
   측정시각(MEAS)은 --measured-at 또는 CSV 파일 mtime에서 자동 도출한다 → 코드 편집 0회.
   (publish_ledger mark 가 tiktok URL을 박으면 그게 이 매핑의 원천이 된다.)
   URL 없이 'yes'로만 기록된 과거 게시는 video_id 추출 불가 → FALLBACK_VID로만 보강.

사용:
  .venv/bin/python scripts/ingest_tiktok_csv.py                       # CSV mtime을 측정시각으로
  .venv/bin/python scripts/ingest_tiktok_csv.py --csv /tmp/x.csv --measured-at 2026-06-24T17:30
"""
import sys, re, os, json, glob, argparse, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analytics_db as adb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# video_id → (slug, 짧은 제목) — URL 없이 'yes'로만 기록된 과거 게시 보강용 폴백.
# (신규 게시는 _pubmeta tiktok URL에서 자동 매핑되므로 여기 추가할 필요 없음.)
FALLBACK_VID = {
    "7643127164107345173": ("202605210000_junja_yorkie", "6대지랄견 순자 (요크셔)"),
    "7643862096920333589": ("202605251700_pudel_jangkun", "새벽 세 시 푸들 장군이"),
    "7643321785194269973": ("202605220000_minam_cat", "같은 고양이 미남이"),
    "7643775813359357205": ("202605240000_myeongjeol_no_marriage", "결혼하기 진짜 싫다"),
    "7642317959200853269": ("202605190000_milk_sleep", "잠 자세 우유"),
    "7640848751904722197": ("202605101115_puppy_rescue", "비닐봉지 두 생명 (v1)"),
    "7641216878127353108": ("202605101115_puppy_rescue", "비닐봉지 두 생명 (v2)"),
    "7638081041823108372": ("202605041854_hyungbu_house", "키워준 형부의 집"),
    "7635720975039958293": ("202605010005_dirty_inlaws", "시댁 가면 행주 한 장"),
    "7632512212904529172": ("misc_lyrics_compilation", "리듬에 실어 전하는 사연"),
    "7634514302111698196": ("202604251015_chinjeong_gift", "안마의자 백만원"),
    "7633836767753276693": ("202604251015_chinjeong_gift", "외동 결혼 사 년차"),
}

URL_VID = re.compile(r"/video/(\d+)")


def _short_title(d, slug):
    plats = d.get("platforms", {}) or {}
    cap = (plats.get("tiktok", {}) or {}).get("caption") or ""
    if cap:
        return cap.splitlines()[0][:50]
    return ((plats.get("youtube", {}) or {}).get("title") or slug)[:50]


def build_vid_map():
    """게시대장(_pubmeta.published.tiktok.url)에서 video_id→(slug,title) 자동 도출."""
    m = {}
    for base in ("productions", "wisdom_out"):
        for pm in glob.glob(os.path.join(ROOT, base, "*", "_pubmeta.json")):
            try:
                d = json.load(open(pm, encoding="utf-8"))
            except Exception:
                continue
            tt = (d.get("published", {}) or {}).get("tiktok")
            url = tt.get("url") if isinstance(tt, dict) else None
            if not url:
                continue
            mm = URL_VID.search(url)
            if not mm:
                continue
            slug = d.get("slug") or os.path.basename(os.path.dirname(pm))
            m[mm.group(1)] = (slug, _short_title(d, slug))
    return m


def main():
    ap = argparse.ArgumentParser(description="TikTok Content.csv → analytics.db (VID/MEAS 자동)")
    ap.add_argument("--csv", default="/tmp/tiktok_csv/Content.csv")
    ap.add_argument("--measured-at", dest="measured_at",
                    help="측정 시각 YYYY-MM-DDTHH:MM (생략 시 CSV 파일 mtime)")
    a = ap.parse_args()

    CSV = a.csv
    if not os.path.exists(CSV):
        sys.exit(f"❌ CSV 없음: {CSV}")
    # 측정 시각: 명시값 > CSV mtime
    MEAS = a.measured_at or datetime.datetime.fromtimestamp(
        os.path.getmtime(CSV)).strftime("%Y-%m-%dT%H:%M")

    # 폴백 + 자동(_pubmeta) 병합 — 자동이 폴백을 덮어씀
    VID = {**FALLBACK_VID, **build_vid_map()}

    # 라인 단위 정규식: video_id + 뒤 5개 필드 (post, likes, comments, shares, views)
    PAT = re.compile(r'/video/(\d+)","([^"]+)","(\d+)","(\d+)","(\d+)","(\d+)"')

    raw = open(CSV, encoding="utf-8-sig").read()
    c = adb.conn()
    c.execute("DELETE FROM metrics"); c.execute("DELETE FROM retention"); c.execute("DELETE FROM videos"); c.commit()

    n = matched = 0
    for m in PAT.finditer(raw):
        vid, post, likes, comments, shares, views = m.groups()
        slug, title = VID.get(vid, (None, vid))
        if slug:
            matched += 1
        vrow = adb.upsert_video(c, slug, "tiktok", vid, title=title, posted_at=post)
        adb.insert_metric(c, vrow, MEAS, source="csv",
                          views=int(views), likes=int(likes),
                          comments=int(comments), shares=int(shares))
        n += 1
    print(f"CSV {n}개 ingest (정규식 파싱) · slug 매핑 {matched}/{n} · 측정시각 {MEAS} · 매핑원천 {len(VID)}건")
    if n and matched < n:
        print(f"  ⚠️ {n-matched}건은 slug 미매핑(vid 그대로 적재) — 해당 게시에 publish_ledger mark --tiktok <url> 박으면 다음부터 자동.")

    # hongi/eonni (CSV 누락 — 최근 게시, 스크린샷 보강)
    for slug, vid, title, posted, mm in [
        ("202605262325_hongi_rescue","hongi_20260530","나이 들어 버려진 강아지 (홍이)","2026-05-30",
         {"views":331,"likes":24,"comments":1,"avg_watch_sec":18.19,"completion_rate":0.106}),
        ("202605292004_eonni_uphill_narr","eonni_20260531","사돈 신분상승 (나레이션)","2026-05-31",
         {"views":289,"likes":9,"comments":1}),
    ]:
        vrow = adb.upsert_video(c, slug, "tiktok", vid, title=title, posted_at=posted)
        adb.insert_metric(c, vrow, MEAS, source="screenshot", **mm)
    print("hongi/eonni 추가")

    # 완주율 (junja/pudel — chrome_mcp 추출값)
    for vid, cr, aw, drop in [("7643127164107345173",0.15,22.43,1), ("7643862096920333589",0.008,3.08,2)]:
        vrow = c.execute("SELECT id FROM videos WHERE platform_video_id=?", (vid,)).fetchone()
        if vrow:
            adb.insert_metric(c, vrow["id"], MEAS, source="chrome_mcp",
                              completion_rate=cr, avg_watch_sec=aw, raw={"retention_drop_sec":drop})
    print("완주율 junja/pudel 보존")
    c.close()


if __name__ == "__main__":
    main()
