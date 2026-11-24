#!/usr/bin/env python3
"""
wisdom_bgm.py — 명언 영상용 mood별 앰비언트 BGM (배경음).

두 가지 백엔드:
  1) procedural (기본) — ffmpeg 로 사인톤 화음 패드를 합성. 즉시·₩0·**보컬 0 보장**(instrumental 확실)
     명상/지혜 콘텐츠에 어울리는 따뜻한 앰비언트 패드. 검증 가능(구성이 결정적).
  2) ace (옵션) — ACE Step v1.5 클라우드(api.acemusic.ai)로 더 리치한 음악 생성.
     ⚠️ 노래 모델이라 보컬 누수 가능 + 느림(~6분/30초). 귀로 확인 필요.

mood → 화음/팔레트는 themes.json/quotes 의 mood 와 1:1 (평온/각성/단호/위안/경건).

사용:
  python scripts/wisdom_bgm.py --gen                 # 5 mood 패드 생성(procedural)
  python scripts/wisdom_bgm.py --gen --backend ace   # ACE Step 으로 생성(느림)
  python scripts/wisdom_bgm.py --mux-themes          # wisdom_out/themes/*.mp4 에 mood BGM 입히기
  python scripts/wisdom_bgm.py --mux <video.mp4> --mood 평온
출력: data/wisdom/bgm/<mood>.mp3
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BGM_DIR = os.path.join(ROOT, "data", "wisdom", "bgm")
THEMES_PATH = os.path.join(ROOT, "data", "wisdom", "themes.json")
THEMES_OUT = os.path.join(ROOT, "wisdom_out", "themes")

# mood → (화음 주파수 Hz 4음, 성격). 루트가 가장 크게, 위로 갈수록 작게.
MOOD_CHORD = {
    "평온": [130.81, 196.00, 261.63, 329.63],   # C3 G3 C4 E4  — C major, 맑고 잔잔
    "각성": [146.83, 220.00, 293.66, 392.00],   # D3 A3 D4 G4  — Dsus, 사색·열림
    "단호": [110.00, 164.81, 220.00, 261.63],   # A2 E3 A3 C4  — A minor, 묵직·결연
    "위안": [87.31, 130.81, 174.61, 220.00],    # F2 C3 F3 A3  — F major, 따뜻
    "경건": [73.42, 110.00, 146.83, 220.00],    # D2 A2 D3 A3  — 완전5도, 성스러움
}
VOLS = [0.26, 0.20, 0.15, 0.11]
TREM = [0.10, 0.13, 0.11, 0.12]
DUR = 60


def gen_pad_procedural(mood, out, dur=DUR):
    freqs = MOOD_CHORD[mood]
    inputs = []
    parts = []
    for i, f in enumerate(freqs):
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={f}:duration={dur}"]
        parts.append(f"[{i}]volume={VOLS[i]},tremolo=f={TREM[i]}:d=0.4[t{i}]")
    n = len(freqs)
    # 공기감용 핑크노이즈 베드
    inputs += ["-f", "lavfi", "-i", f"anoisesrc=color=pink:duration={dur}:amplitude=0.012"]
    parts.append(f"[{n}]lowpass=f=850,volume=0.5[bed]")
    mix_in = "".join(f"[t{i}]" for i in range(n)) + "[bed]"
    chain = (
        f"{mix_in}amix=inputs={n + 1}:normalize=0,"
        f"lowpass=f=2400,aecho=0.8:0.7:70|150|290:0.5|0.3|0.18,"
        f"afade=t=in:d=2.5,afade=t=out:st={dur - 2.5}:d=2.5,"
        f"loudnorm=I=-23:TP=-3:LRA=7[out]"
    )
    fc = ";".join(parts) + ";" + chain
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", "[out]",
           "-ac", "2", "-ar", "44100", "-t", str(dur), "-c:a", "libmp3lame", "-q:a", "4", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1200:], file=sys.stderr)
        sys.exit(f"❌ 패드 생성 실패 ({mood})")


def gen_pad_ace(mood, out, dur=DUR):
    import pathlib
    for line in pathlib.Path(os.path.join(ROOT, ".env")).read_text().splitlines():
        if line.strip() and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import generate_bgm as g
    prompts = {
        "평온": "calm meditative ambient instrumental, soft felt piano and warm pad, very slow, peaceful, spacious reverb, lo-fi, no vocals, no lyrics, no drums",
        "각성": "contemplative cinematic ambient instrumental, slow solo piano with subtle strings, reflective, awakening, minimal, no vocals, no lyrics",
        "단호": "solemn determined ambient instrumental, low strings and deep cello, slow, dignified, resolute, no vocals, no lyrics, no drums",
        "위안": "warm comforting ambient instrumental, soft acoustic guitar and gentle piano, hopeful, healing, tender, no vocals, no lyrics",
        "경건": "sacred reverent ambient drone instrumental, wordless choir-like pad and soft bells, spiritual, meditative, slow, no vocals, no lyrics",
    }
    meta = {"request": {"prompt": prompts[mood], "duration": dur, "format": "mp3", "vocal_language": "ko"}}
    payload = g.build_request(meta, "", g.DEFAULT_MODEL, 1)
    data = g.call_ace_step(g.DEFAULT_BASE_URL, os.environ.get("ACESTEP_API_KEY"), payload, 600)
    audio = g.extract_audio(data)
    if not audio:
        sys.exit(f"❌ ACE 오디오 없음 ({mood})")
    open(out, "wb").write(audio[0])


def cmd_gen(args):
    os.makedirs(BGM_DIR, exist_ok=True)
    moods = [args.mood] if args.mood else list(MOOD_CHORD)
    for m in moods:
        out = os.path.join(BGM_DIR, f"{m}.mp3")
        print(f"▶ {m} ({args.backend}) → {out}")
        if args.backend == "ace":
            gen_pad_ace(m, out)
        else:
            gen_pad_procedural(m, out)
        print(f"  ✅ {out}")


def _dur(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path]).decode().strip()
    return float(out)


def mux(video, bgm, vol=0.85):
    """무음 영상에 BGM 입히기 (루프+페이드아웃, 영상 길이에 맞춤, 비디오 재인코딩 없음)."""
    d = _dur(video)
    tmp = video[:-4] + "_bgm_tmp.mp4"
    cmd = ["ffmpeg", "-y", "-i", video, "-stream_loop", "-1", "-i", bgm,
           "-map", "0:v", "-map", "1:a",
           "-af", f"volume={vol},afade=t=out:st={max(0, d - 2.5):.3f}:d=2.5",
           "-t", f"{d:.3f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
           "-movflags", "+faststart", tmp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1200:], file=sys.stderr)
        sys.exit(f"❌ mux 실패 {video}")
    os.replace(tmp, video)


def cmd_mux_themes(args):
    themes = {t["id"]: t for t in json.load(open(THEMES_PATH, encoding="utf-8"))}
    if not os.path.isdir(THEMES_OUT):
        sys.exit(f"주제 영상 폴더 없음: {THEMES_OUT}")
    vids = sorted(f for f in os.listdir(THEMES_OUT) if f.endswith(".mp4"))
    done = 0
    for v in vids:
        tid = v[:-4]
        t = themes.get(tid)
        mood = (t or {}).get("mood", "평온")
        bgm = os.path.join(BGM_DIR, f"{mood}.mp3")
        if not os.path.exists(bgm):
            print(f"  (건너뜀) {v} — {mood} BGM 없음 (먼저 --gen)")
            continue
        mux(os.path.join(THEMES_OUT, v), bgm)
        done += 1
        print(f"  ✅ {v}  ({mood})")
    print(f"\n{done}/{len(vids)} 주제 영상에 BGM 입힘")


def main():
    ap = argparse.ArgumentParser(description="명언 영상 mood별 앰비언트 BGM")
    ap.add_argument("--gen", action="store_true", help="mood 패드 생성")
    ap.add_argument("--backend", choices=["procedural", "ace"], default="procedural")
    ap.add_argument("--mood", help="특정 mood만 (평온/각성/단호/위안/경건)")
    ap.add_argument("--mux-themes", action="store_true", help="wisdom_out/themes/*.mp4 에 BGM 입히기")
    ap.add_argument("--mux", help="단일 영상에 BGM 입히기 (영상 경로)")
    args = ap.parse_args()

    if args.gen:
        cmd_gen(args)
    if args.mux_themes:
        cmd_mux_themes(args)
    if args.mux:
        if not args.mood:
            ap.error("--mux 에는 --mood 필요")
        mux(args.mux, os.path.join(BGM_DIR, f"{args.mood}.mp3"))
        print(f"✅ {args.mux} ({args.mood})")
    if not (args.gen or args.mux_themes or args.mux):
        ap.error("--gen / --mux-themes / --mux 중 하나 필요")


if __name__ == "__main__":
    main()
