#!/usr/bin/env python3
"""tighten_narration.py — 나레이션 영상을 재-TTS 없이 빠르게 (페이스 조임)

uncle_car(137s)·ex_90million(124.6s) 둘 다 "늘어진다" 나옴 → 재사용 유틸.
- 기존 03_audio_narration_only.mp3 를 atempo 로 가속(피치 보존)
- 04_timing.json 의 모든 시간을 비례 축소
- (기본) compose_narration 재실행 → 06_render_v1.mp4 갱신

⭐ 원본 보존·멱등: 첫 실행 때 03_audio_pre_tighten.mp3 / 04_timing_pre_tighten.json 백업.
   이후 매 실행은 *원본에서* 다시 계산 → 다른 --speed 로 재실행해도 누적 안 됨.

사용:  python scripts/tighten_narration.py <slug> [--speed 1.12] [--no-recompose]

⚠️ 기본 배속 1.12 (2026-07-25 조정) — 2026-06-26 사용자 지침("자연속도 우선,
늘어질 때만 ≤1.10~1.15 배") 반영. 예전 기본값 1.18은 그 지침보다 과속이었음.
"""
import os, sys, json, shutil, argparse, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"; FP = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
if not os.path.exists(FF): FF = "ffmpeg"
if not os.path.exists(FP): FP = "ffprobe"

def dur(f):
    return float(subprocess.run([FP,"-v","error","-show_entries","format=duration","-of","csv=p=0",f],
                                capture_output=True,text=True).stdout.strip() or 0)

def atempo_chain(s):  # atempo 단일은 0.5~2.0 → 범위 밖이면 체인
    s=float(s); parts=[]
    while s > 2.0: parts.append("atempo=2.0"); s/=2.0
    while s < 0.5: parts.append("atempo=0.5"); s/=0.5
    parts.append(f"atempo={s:.6f}")
    return ",".join(parts)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("slug")
    ap.add_argument("--speed",type=float,default=1.12)
    ap.add_argument("--no-recompose",action="store_true")
    ap.add_argument("--kenburns",action="store_true",help="재합성 시 compose에 전달 — 롱폼/스틸(Ken Burns) 빌드면 필수. 빼먹으면 정지화면으로 재렌더됨")
    a=ap.parse_args()
    if a.speed <= 0: raise SystemExit("speed > 0 이어야 함")
    prod=os.path.join(ROOT,"productions",a.slug); adir=os.path.join(prod,"audio"); os.makedirs(adir,exist_ok=True)
    audio=os.path.join(prod,"03_audio_narration_only.mp3"); timing=os.path.join(prod,"04_timing.json")
    if not (os.path.exists(audio) and os.path.exists(timing)):
        raise SystemExit("❌ 03_audio_narration_only.mp3 / 04_timing.json 필요 (generate-narration 먼저)")
    pre_a=os.path.join(adir,"03_audio_pre_tighten.mp3"); pre_t=os.path.join(prod,"04_timing_pre_tighten.json")
    # 원본 백업 (최초 1회) — 이후 항상 원본에서 재계산(멱등)
    if not os.path.exists(pre_a): shutil.copy(audio, pre_a)
    if not os.path.exists(pre_t): shutil.copy(timing, pre_t)
    print(f"원본 {dur(pre_a):.1f}s → ×{a.speed} 가속")
    # 오디오 가속
    tmp=os.path.join(adir,"_tighten_tmp.mp3")
    subprocess.run([FF,"-y","-loglevel","error","-i",pre_a,"-filter:a",atempo_chain(a.speed),
                    "-b:a","192k","-ar","44100",tmp])
    os.replace(tmp, audio)
    # 타이밍 비례 축소 (원본에서)
    T=json.load(open(pre_t,encoding="utf-8")); s=a.speed
    for b in T["beats"]: b["start"]=round(b["start"]/s,3); b["end"]=round(b["end"]/s,3)
    for u in T["subtitles"]: u["start"]=round(u["start"]/s,3); u["end"]=round(u["end"]/s,3)
    T["total_duration"]=round(T.get("total_duration",dur(pre_a))/s,3)
    json.dump(T, open(timing,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ 오디오 {dur(audio):.1f}s + 타이밍 재계산")
    # 재합성
    if not a.no_recompose:
        cargs=[sys.executable, os.path.join(ROOT,"scripts","compose_narration.py"), a.slug]
        if a.kenburns: cargs.append("--kenburns")
        r=subprocess.run(cargs)
        if r.returncode!=0: raise SystemExit("❌ compose 실패")
    else:
        print("   (--no-recompose) → /compose-narration 직접 실행 필요")

if __name__=="__main__":
    main()
