#!/usr/bin/env python3
"""키즈 교육 글자 오버레이 — 큰 자모/단어를 영상 상단에 번인 (2026-06-17 박제).

배경: 한글 교육 영상인데 fal 이미지는 'no text'라(글자 깨짐 방지) 글자가 없고,
나레이션 자막만 작게 깔려 정작 배우는 'ㄴ' 같은 글자가 작게만 보인다. 이 스크립트는
production의 04_timing.json(비트 시간) + _edu_overlay.json(비트별 큰 글자 사양)을 읽어
상단 중앙에 큰 글자를 ASS(libass)로 번인한다. 한글 자모 시리즈 모든 편에 재사용.

  _edu_overlay.json 형식 (키=비트번호 문자열, 값=그 비트에 띄울 줄 목록):
  {
    "2": [{"text":"ㄴ","size":380,"y":330}, {"text":"니은","size":140,"y":620}],
    "3": [{"text":"ㄴ","size":130,"y":160,"color":"&H0080FF&"}, {"text":"나비","size":280,"y":360}]
  }
  - size = 폰트 px(1920 기준), y = 화면 세로 중앙 y(px), color(옵션) = ASS \\c (&Hbbggrr&)
  - 자막은 하단이라 상단(y<700)에 두면 안 겹침. 원본은 06_render_v1_nooverlay.mp4 로 보존(cp).
  - 멱등: 매 실행마다 무오버레이 원본에서 다시 굽는다(스택 안 쌓임).

  python scripts/overlay_kids_letters.py <slug>
"""
import json, os, subprocess, sys, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = "Apple SD Gothic Neo"
# libass(ass 필터)는 ffmpeg-full에만 있음. 일반 /opt/homebrew/bin/ffmpeg엔 없어 필터 파싱 실패.
FF = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
if not os.path.exists(FF):
    FF = "ffmpeg"


def ts(sec):
    cs = int(round(sec * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def main():
    import argparse
    ap = argparse.ArgumentParser(description="키즈 큰 글자 교육 오버레이")
    ap.add_argument("slug")
    ap.add_argument("--refresh", action="store_true",
                    help="현재 06_render_v1.mp4를 무오버레이 원본으로 새로 백업(compose 직후 호출용). "
                         "미지정 시 기존 _nooverlay 재사용(스펙만 바꿔 재적용).")
    args = ap.parse_args()
    slug = args.slug
    pdir = os.path.join(ROOT, "productions", slug)
    timing = json.load(open(os.path.join(pdir, "04_timing.json"), encoding="utf-8"))
    spec = json.load(open(os.path.join(pdir, "_edu_overlay.json"), encoding="utf-8"))
    beats = {str(b["beat"]): b for b in timing["beats"]}
    vid = os.path.join(pdir, "06_render_v1.mp4")
    if not os.path.exists(vid):
        sys.exit(f"no render: {vid}")

    head = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Edu,{FONT},200,&H00FFFFFF,&H000000FF,&H00303030,&H64000000,"
        "1,0,0,0,100,100,0,0,1,7,3,5,0,0,0,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    lines = []
    for bnum, items in spec.items():
        if bnum not in beats:
            continue
        st, en = ts(beats[bnum]["start"]), ts(beats[bnum]["end"])
        for it in items:
            y, fs, txt = it.get("y", 340), it.get("size", 200), it["text"]
            ov = f"\\an5\\pos(540,{y})\\fs{fs}"
            if it.get("color"):
                ov += f"\\c{it['color']}"
            lines.append(f"Dialogue: 0,{st},{en},Edu,,0,0,0,,{{{ov}}}{txt}")
    ass_path = os.path.join(pdir, "_edu_overlay.ass")
    open(ass_path, "w", encoding="utf-8").write(head + "\n".join(lines) + "\n")

    backup = os.path.join(pdir, "06_render_v1_nooverlay.mp4")
    if args.refresh or not os.path.exists(backup):
        shutil.copy2(vid, backup)  # 무오버레이 원본 보존/갱신 (cp, rm 안 함). --refresh=compose 직후 클린본 재백업
    tmp = os.path.join(pdir, "_edu_tmp.mp4")
    cmd = [FF, "-y", "-i", backup, "-vf", f"ass='{ass_path}'",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
           "-c:a", "copy", "-movflags", "+faststart", tmp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1600:], file=sys.stderr)
        sys.exit("❌ ass 오버레이 실패")
    os.replace(tmp, vid)
    print(f"✅ 교육 글자 오버레이 번인 → {vid}\n   (무오버레이 원본=06_render_v1_nooverlay.mp4, 스펙=_edu_overlay.ass)")


if __name__ == "__main__":
    main()
