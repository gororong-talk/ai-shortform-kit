#!/usr/bin/env python3
"""compress_for_delivery.py — 완성 영상을 앱 채널로 안전 전달하기 위한 압축 + 신선도 가드.

배경(2026-06-26 박제): 사연 production 의 마지막 단계는 늘 `ffmpeg -crf 30`으로
06_render*.mp4 를 ~10MB 로 줄여 SendUserFile(앱 채팅)로 보내는 것이었다. 손으로 칠 때 2가지가 샜다:
  1) 임계값(~25MB)·플래그를 매번 기억에서 재유도 → secret_wedding(2026-06-26): 30MB 를
     그대로 보냈다가 앱 다운로드 실패 → 수동 재압축·재전송(왕복 손실, CONTINUITY ⑧ 실사례).
  2) 이미지 고치고 재렌더 안 한 stale mp4 전달 위험 — 이 전달 경로(SendUserFile)는
     prep_upload 의 freshness 가드를 안 거친다([[stale-render-and-foreground-text-qc]]).
→ 이 스크립트가 (1) 렌더가 소스 에셋보다 오래됐는지(stale) 먼저 막고, (2) 크면 crf30 으로
  압축해 앱 다운로드 안전 상한 아래로 보장한다. 마지막 `DELIVER: <path>` 줄을 SendUserFile 한다.

사용:
  python scripts/compress_for_delivery.py <slug>
  python scripts/compress_for_delivery.py <slug> --crf 32 --ceiling-mb 20
  python scripts/compress_for_delivery.py --file productions/<slug>/06_render_v1.mp4
  python scripts/compress_for_delivery.py <slug> --force      # stale 경고 무시하고 진행
"""
import argparse, glob, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD = os.path.join(ROOT, "productions")
WISDOM_OUT = os.path.join(ROOT, "wisdom_out")


def _mb(path):
    return os.path.getsize(path) / (1024 * 1024)


def _duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True, check=True).stdout.strip()
        return float(out)
    except Exception:
        return 0.0


def _find_prod_dir(slug):
    for base in (PROD, WISDOM_OUT):
        d = os.path.join(base, slug)
        if os.path.isdir(d):
            return d
        hits = [h for h in sorted(glob.glob(os.path.join(base, f"*{slug}*"))) if os.path.isdir(h)]
        if hits:
            return hits[0]
    return None


def _find_render(prod_dir):
    cands = glob.glob(os.path.join(prod_dir, "06_render*.mp4")) + \
            glob.glob(os.path.join(prod_dir, "video.mp4"))            # wisdom
    cands = [c for c in cands if "_app" not in os.path.basename(c)]    # 산출물 제외
    return max(cands, key=os.path.getmtime) if cands else None


def _stale_sources(prod_dir, render):
    """render 보다 나중에 수정된 소스 에셋(이미지/오디오/타이밍) = stale 신호."""
    rt = os.path.getmtime(render)
    newer = []
    for pat in ("flow_images/B*.png", "flow_images/B*.mp4", "audio/03_audio*.mp3",
                "03_audio*.mp3", "04_timing.json"):
        for f in glob.glob(os.path.join(prod_dir, pat)):
            if os.path.getmtime(f) > rt + 1:           # 1s 여유(동시생성 오탐 방지)
                newer.append(os.path.relpath(f, prod_dir))
    return sorted(newer)


def _encode(src, dst, crf):
    subprocess.run(
        ["ffmpeg", "-y", "-i", src,
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf), "-preset", "slow",
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", dst],
        check=True, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser(description="앱 전달용 압축 + 신선도(stale) 가드")
    ap.add_argument("slug", nargs="?", help="production slug (또는 --file)")
    ap.add_argument("--file", help="직접 mp4 경로 (slug 대신)")
    ap.add_argument("--crf", type=int, default=30,
                    help="x264 CRF (기본 30 — 저모션 KenBurns 무손실급)")
    ap.add_argument("--ceiling-mb", type=float, default=24.0,
                    help="앱 다운로드 안전 상한 MB (기본 24 — 넘으면 crf 올려 재압축)")
    ap.add_argument("--skip-under-mb", type=float, default=12.0,
                    help="이 크기 미만 원본은 무손실로 그대로 전달(기본 12)")
    ap.add_argument("--force", action="store_true", help="stale 경고 무시하고 진행")
    ap.add_argument("--out", help="출력 경로(기본 <render>_app.mp4)")
    a = ap.parse_args()

    # 1) 입력 영상 결정 (slug → newest 06_render*.mp4 / video.mp4, 또는 --file)
    if a.file:
        render = os.path.abspath(a.file)
        if not os.path.exists(render):
            sys.exit(f"❌ 파일 없음: {render}")
        prod_dir = os.path.dirname(render)
    else:
        if not a.slug:
            sys.exit("❌ slug 또는 --file 필요")
        prod_dir = _find_prod_dir(a.slug)
        if not prod_dir:
            sys.exit(f"❌ production 폴더 못 찾음: {a.slug}")
        render = _find_render(prod_dir)
        if not render:
            sys.exit(f"❌ 06_render*.mp4 / video.mp4 없음: {prod_dir}")

    src_mb = _mb(render)
    print(f"🎬 대상: {os.path.relpath(render, ROOT)}  ({src_mb:.1f}MB, {_duration(render):.0f}s)")

    # 2) ★ stale 가드 — 렌더보다 나중에 고친 소스가 있으면 옛 영상 전달 위험(전달경로 freshness)
    stale = _stale_sources(prod_dir, render)
    if stale:
        print("\n🚨 STALE 렌더 의심 — 아래 소스가 렌더보다 나중에 수정됨(재렌더 먼저):", file=sys.stderr)
        for s in stale[:12]:
            print(f"   · {s}", file=sys.stderr)
        if not a.force:
            sys.exit("→ 재렌더(/compose-narration 등) 후 다시 실행, 또는 --force 로 무시.")
        print("   (--force: 무시하고 진행)", file=sys.stderr)

    # 3) 이미 작으면 무손실로 그대로 전달
    if src_mb <= a.skip_under_mb:
        print(f"✅ 이미 작음(≤{a.skip_under_mb:.0f}MB) — 압축 불필요. 원본 그대로 전달.")
        print(f"DELIVER: {render}")
        return

    # 4) crf 압축 → 상한 넘으면 crf 올려 재시도(최대 40)
    out = a.out or os.path.join(
        prod_dir, os.path.splitext(os.path.basename(render))[0] + "_app.mp4")
    crf, mb = a.crf, None
    while True:
        print(f"⚙️  ffmpeg crf{crf} 압축 → {os.path.basename(out)} ...")
        _encode(render, out, crf)
        mb = _mb(out)
        print(f"   → {mb:.1f}MB  (원본 {src_mb:.1f}MB, {100 * mb / src_mb:.0f}%)")
        if mb <= a.ceiling_mb or crf >= 40:
            break
        crf += 4
        print(f"   상한 {a.ceiling_mb:.0f}MB 초과 → crf{crf} 재압축")
    if mb > a.ceiling_mb:
        print(f"⚠️  여전히 {mb:.1f}MB > 상한 {a.ceiling_mb:.0f}MB (crf{crf}) — 해상도 축소 검토.",
              file=sys.stderr)
    else:
        print(f"✅ 앱 전달 안전: {mb:.1f}MB ≤ {a.ceiling_mb:.0f}MB")
    print(f"DELIVER: {out}")


if __name__ == "__main__":
    main()
