#!/usr/bin/env python3
"""
check_black_frames.py — production flow_images 의 검은(생성실패) 이미지 가드.

왜? fal.ai FLUX 가 가끔 "성공"으로 보고하면서 **완전히 검은 PNG** 를 반환한다
(2026-06-20 baby_hug B07 = 감동 절정 컷이 검은 화면으로 렌더됨, compose 후에야 발견).
generate_images_fal 직후 이걸 돌려 compose 전에 잡는다.

usage:
  python scripts/check_black_frames.py <slug|production_path>
exit 0 = 모두 정상 / exit 1 = 검은 이미지 발견(재생성 필요: generate_images_fal --only N)
"""
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"


def is_black(path):
    """blackframe 필터가 프레임을 거의-검정으로 판정하면 True."""
    out = subprocess.run(
        [FFMPEG, "-v", "info", "-i", path,
         "-vf", "blackframe=amount=95:threshold=32", "-f", "null", "-"],
        capture_output=True, text=True)
    return "blackframe" in out.stderr.lower()


def resolve_dir(arg):
    if os.path.isdir(arg):
        base = arg
    else:
        base = os.path.join(ROOT, "productions", arg)
    imgs = os.path.join(base, "flow_images")
    return imgs if os.path.isdir(imgs) else base


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: check_black_frames.py <slug|production_path>")
    d = resolve_dir(sys.argv[1])
    images = sorted(glob.glob(os.path.join(d, "B*.png")))
    if not images:
        sys.exit(f"❌ 이미지 없음: {d}")
    black = []
    for img in images:
        flag = is_black(img)
        print(f"  {'⚫ BLACK!' if flag else 'ok':10} {os.path.basename(img)}")
        if flag:
            black.append(os.path.basename(img))
    if black:
        beats = ",".join(b[1:3].lstrip("0") for b in black)  # B07.png → 7
        print(f"\n❌ 검은 이미지 {len(black)}개: {', '.join(black)}")
        print(f"   재생성: .venv/bin/python scripts/generate_images_fal.py "
              f"--production <slug> --style <cute|webtoon> --only {beats}")
        sys.exit(1)
    print(f"\n✅ {len(images)}개 이미지 모두 정상 (검은 프레임 없음)")


if __name__ == "__main__":
    main()
