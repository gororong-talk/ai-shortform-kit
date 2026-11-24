"""analytics_report.py — DB → 주간 리포트 + WEEKLY_METRICS.md 자동 갱신.

북극성 = 완주율. 완주율 데이터 있으면 그 기준 정렬, 없으면 조회수 fallback.
사용:
  python scripts/analytics_report.py            # 콘솔 요약 + WEEKLY_METRICS.md 갱신
  python scripts/analytics_report.py --md-only  # WEEKLY_METRICS.md 만 갱신
"""
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import analytics_db as adb

KST = timezone(timedelta(hours=9))
WEEKLY_MD = os.path.join(ROOT, "docs", "WEEKLY_METRICS.md")


def latest_metric_per_video():
    """영상별 가장 최근 측정 1건 (videos JOIN metrics)."""
    c = adb.conn()
    rows = c.execute("""
        SELECT v.slug, v.platform, v.title, v.duration_sec, v.posted_at,
               m.views, m.likes, m.comments, m.shares,
               m.avg_watch_sec, m.completion_rate, m.measured_at, m.source
        FROM videos v
        JOIN metrics m ON m.video_id = v.id
        WHERE m.measured_at = (
            SELECT MAX(measured_at) FROM metrics m2 WHERE m2.video_id = v.id
        )
        ORDER BY
            CASE WHEN m.completion_rate IS NOT NULL THEN 0 ELSE 1 END,
            m.completion_rate DESC, m.views DESC
    """).fetchall()
    c.close()
    return rows


def console_report():
    rows = latest_metric_per_video()
    if not rows:
        print("📊 아직 측정 데이터 없음. analytics/inbox/ 에 스크린샷/CSV 던지고 ingest 하세요.")
        return rows
    print("=" * 78)
    print("📊 주간 성과 리포트 — 북극성: 완주율 (없으면 조회수)")
    print("=" * 78)
    has_cr = [r for r in rows if r["completion_rate"] is not None]
    if has_cr:
        print("\n🏆 완주율 상위 (복제 대상):")
        for r in has_cr[:5]:
            print(f"  {r['completion_rate']*100:5.1f}%  {(r['slug'] or '?')[:30]:<30} [{r['platform']}] 조회 {r['views'] or '-'}")
        # 6건 이상일 때만 하위 별도 표시 (적으면 상위와 중복되어 무의미)
        if len(has_cr) >= 6:
            print("\n📉 완주율 하위 (폐기 검토):")
            for r in has_cr[-3:]:
                print(f"  {r['completion_rate']*100:5.1f}%  {(r['slug'] or '?')[:30]:<30} [{r['platform']}]")
    else:
        print("\n⚠️ 완주율 데이터 0건 — 조회수 기준 표시 (완주율 수집 시 북극성 전환):")
        for r in rows[:8]:
            print(f"  조회 {str(r['views'] or '-'):>7}  {(r['slug'] or '?')[:30]:<30} [{r['platform']}]")
    print()
    return rows


def update_weekly_md():
    rows = latest_metric_per_video()
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    lines = []
    lines.append("# 📊 주간 측정 기록 — 쭌빠 채널 (드라마)\n")
    lines.append("> 북극성 = **완주율 / 평균 시청 유지율**. 조회·좋아요 = 후행 참고용.")
    lines.append(f"> 자동 생성: `scripts/analytics_report.py` · 최종 갱신: {now}")
    lines.append("> 데이터 입력: `analytics/inbox/` 에 스크린샷/CSV → `python scripts/analytics_ingest.py`\n")
    lines.append("---\n")
    lines.append("## 영상별 최신 측정\n")
    if not rows:
        lines.append("_아직 측정 데이터 없음._\n")
    else:
        lines.append("| 영상 (slug) | 플랫폼 | 길이 | 조회 | 좋아요 | 평균시청 | 완주율 | 측정일 | 출처 |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            dur = f"{r['duration_sec']:.0f}s" if r["duration_sec"] else "-"
            cr = f"{r['completion_rate']*100:.0f}%" if r["completion_rate"] is not None else "-"
            aw = f"{r['avg_watch_sec']:.1f}s" if r["avg_watch_sec"] is not None else "-"
            lines.append(f"| {(r['slug'] or '?')[:30]} | {r['platform']} | {dur} | "
                         f"{r['views'] or '-'} | {r['likes'] or '-'} | {aw} | {cr} | "
                         f"{(r['measured_at'] or '-')[:10]} | {r['source'] or '-'} |")
    lines.append("\n---\n")
    lines.append("## 패턴 관찰 (완주율 데이터 누적 시 자동 강화)\n")
    has_cr = [r for r in rows if r["completion_rate"] is not None]
    if len(has_cr) >= 6:
        top = has_cr[:3]
        bot = has_cr[-3:]
        lines.append("### 🏆 상위 패턴 (복제 대상)")
        for r in top:
            lines.append(f"- **{r['completion_rate']*100:.0f}%** {r['slug']} ({r['platform']}, {r['duration_sec']:.0f}s)" if r["duration_sec"] else f"- **{r['completion_rate']*100:.0f}%** {r['slug']}")
        lines.append("\n### 📉 하위 패턴 (폐기 검토)")
        for r in bot:
            lines.append(f"- {r['completion_rate']*100:.0f}% {r['slug']} ({r['platform']})")
    elif has_cr:
        lines.append(f"_완주율 {len(has_cr)}건 수집됨 — 6건 이상이면 상위/하위 패턴 자동 분리. 현재는 전체 순위만:_")
        for r in has_cr:
            lines.append(f"- **{r['completion_rate']*100:.0f}%** {r['slug']} ({r['platform']})")
    else:
        lines.append("_완주율 데이터 0건 — 수집 대기 (TikTok 스크린샷 / YouTube·IG API)._")
    lines.append("\n### 검증 대기 가설")
    lines.append("- Hook 충격 압축형 ([scoffs]/[gasps]) → 1~3초 차단율 ↓ (pudel/eonni)")
    lines.append("- Happy Ending 카타르시스 → 완주율 ↑ (eonni_narr)")
    lines.append("- 가사 곡 vs 나레이션 → 완주율 우위? (chinjeong vs milk/junja)")
    lines.append("- 60s+ vs 30~50s → 완주율 trade-off (도달은 길이 무관 확인됨)\n")

    with open(WEEKLY_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ {os.path.relpath(WEEKLY_MD, ROOT)} 갱신 ({len(rows)}개 영상)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md-only", action="store_true")
    args = ap.parse_args()
    if not args.md_only:
        console_report()
    update_weekly_md()


if __name__ == "__main__":
    main()
