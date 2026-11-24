#!/usr/bin/env python3
"""generate_narration.py — Gemini TTS 감정 나레이션 생성 + 라인/비트 타이밍

uncle_car(#13)에서 검증한 신규 나레이션 표준을 스크립트화.
- 입력: productions/<slug>/02_step3_narration.txt  (S01.. 라인)
- 감정: productions/<slug>/_narration_emotion.json  {"1":"분하게 또박또박", ...}  (있으면 라인별 적용)
        없으면 00_meta.narration_tone 기반 기본 디렉티브 1개를 전 라인 적용
- 비트: productions/<slug>/_beat_map.json  {"1":[1,2], "2":[3,4], ...}  (하이브리드; 있으면 35비트 분할)
        없으면 1라인=1비트 (B{n:02d})
- 출력: 03_audio_narration_only.mp3  +  04_timing.json

TTS: gemini-2.5-flash-preview-tts, voice 기본 Kore, 한국어. GOOGLE_API_KEY(.env).
PCM(L16 24kHz mono) → ffmpeg-full 로 -ac 2 + dynaudnorm 후처리.
숫자 한글교정(오백 원/삼백만 원/오만 원/오년 ...)으로 발음 안정.

사용:  python scripts/generate_narration.py <slug> [--voice Kore] [--gap 0.22]
"""
import os, re, sys, json, time, base64, argparse, subprocess
import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FP = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
if not os.path.exists(FF): FF = "ffmpeg"
if not os.path.exists(FP): FP = "ffprobe"
RATE = 24000
CLIP_BEATS_DEFAULT = set()  # 하이브리드면 _beat_map + 파일존재로 판정

# 숫자→한글 발음 교정 (확장 가능)
NUM_FIX = [("9천만 원","구천만 원"),("500원","오백 원"),("300만 원","삼백만 원"),("200만 원","이백만 원"),
           ("5만 원","오만 원"),("1000원","천 원"),("10kg","십 킬로"),
           ("6개월","육 개월"),("5년","오년"),("3년","삼년"),("1년","일 년"),("3천","삼천"),("7살","일곱 살")]

def norm_num(t):
    for a,b in NUM_FIX: t = t.replace(a,b)
    return t

def tone_default_directive(tone:str)->str:
    t = tone or ""
    if any(k in t for k in ["분노","각성","폭로"]): return "감정을 담아, 차분하게 시작해 점점 단호하고 날카롭게"
    if any(k in t for k in ["감동","위로","따뜻"]): return "따뜻하고 잔잔하게, 진심을 담아"
    if any(k in t for k in ["코믹","체념","사고뭉치"]): return "가볍고 리듬감 있게"
    if any(k in t for k in ["슬픔","회한"]): return "차분하고 먹먹하게"
    return "또박또박 차분하게"

def dur(f):
    return float(subprocess.run([FP,"-v","error","-show_entries","format=duration","-of","csv=p=0",f],
                                capture_output=True,text=True).stdout.strip() or 0)

def tts(key, voice, text, retries=5):
    url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={key}"
    body={"contents":[{"parts":[{"text":text}]}],
          "generationConfig":{"responseModalities":["AUDIO"],
            "speechConfig":{"voiceConfig":{"prebuiltVoiceConfig":{"voiceName":voice}}}}}
    for i in range(retries):
        r=requests.post(url,json=body,timeout=120)
        if r.status_code==200:
            return base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
        print(f"   ⚠️ TTS {r.status_code} (try {i+1}): {r.text[:120]}")
        time.sleep(8 if r.status_code==429 else 3)
    raise SystemExit("❌ TTS 생성 실패")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--voice",default="Kore")
    ap.add_argument("--gap",type=float,default=0.22)
    a=ap.parse_args()
    load_dotenv(os.path.join(ROOT,".env"))
    key=os.getenv("GOOGLE_API_KEY")
    if not key: raise SystemExit("❌ GOOGLE_API_KEY 없음 (.env)")
    prod=os.path.join(ROOT,"productions",a.slug); adir=os.path.join(prod,"audio"); os.makedirs(adir,exist_ok=True)

    lines=[m.group(1).strip() for l in open(os.path.join(prod,"02_step3_narration.txt"),encoding="utf-8")
           if (m:=re.match(r"^S\d{2}\s+(.*)$", l.strip()))]
    if not lines: raise SystemExit("❌ 02_step3_narration.txt 에서 S## 라인을 못 찾음")
    N=len(lines); print(f"📖 라인 {N}개")

    # 감정 디렉티브
    emo_path=os.path.join(prod,"_narration_emotion.json")
    if os.path.exists(emo_path):
        emo=json.load(open(emo_path,encoding="utf-8")); print("🎭 라인별 감정맵 사용")
    else:
        try: tone=json.load(open(os.path.join(prod,"00_meta.json"),encoding="utf-8")).get("narration_tone","")
        except Exception: tone=""
        d=tone_default_directive(tone); emo={str(i):d for i in range(1,N+1)}
        print(f"🎭 감정맵 없음 → 톤 기본 디렉티브: '{d}'")
    def gaps(i):  # 감정맵에 {"gap_3":0.35} 식 선택 오버라이드 가능
        return float(emo.get(f"gap_{i}", a.gap))

    pcm=bytearray(); line_time=[]; t=0.0
    for i,ln in enumerate(lines,1):
        directive=emo.get(str(i)) or tone_default_directive("")
        b=tts(key,a.voice,f"{directive}: {norm_num(ln)}"); pcm+=b
        sp=len(b)/(RATE*2); g=0.0 if i==N else gaps(i)
        pcm+=b"\x00"*(int(g*RATE)*2)
        line_time.append((round(t,3),round(t+sp+g,3))); t+=sp+g
        print(f"   L{i:02d} {sp:.2f}s → {t:.2f}s | {ln[:24]}")
        time.sleep(0.6)
    rawpcm=os.path.join(adir,"03_narration_raw.pcm"); open(rawpcm,"wb").write(pcm)
    out=os.path.join(prod,"03_audio_narration_only.mp3")
    out_tmp=out[:-4]+"_tmp.mp3"  # 원자적 쓰기 — 실패 시 부분 파일이 이전 성공본 덮어쓰는 것 방지
    r=subprocess.run([FF,"-y","-loglevel","error","-f","s16le","-ar",str(RATE),"-ac","1","-i",rawpcm,
        "-ac","2","-af","volume=1.15,dynaudnorm=p=0.9:f=250:g=15,apad=pad_dur=1.2","-b:a","192k","-ar","44100",out_tmp])
    if r.returncode!=0 or not os.path.exists(out_tmp): raise SystemExit("❌ 최종 mp3 인코드 실패 (이전 성공본·raw pcm 보존)")
    os.replace(out_tmp,out); os.remove(rawpcm)
    total=round(t+1.2,3); print(f"✅ 03_audio_narration_only.mp3  {total}s")

    # 비트 매핑
    bm_path=os.path.join(prod,"_beat_map.json")
    line2beats=json.load(open(bm_path,encoding="utf-8")) if os.path.exists(bm_path) else {str(i):[i] for i in range(1,N+1)}
    fimg=os.path.join(prod,"flow_images")
    # 클립 비트 판정: _clips.json 의 designation 우선(순서 무관) → 없으면 파일존재 fallback
    clips_path=os.path.join(prod,"_clips.json")
    clip_set=set()
    if os.path.exists(clips_path):
        try: clip_set=set(int(x) for x in json.load(open(clips_path,encoding="utf-8")).get("clips",[]))
        except Exception: pass
    def fname(b):
        if b in clip_set: return f"B{b:02d}.mp4"
        mp4=os.path.join(fimg,f"B{b:02d}.mp4")
        return f"B{b:02d}.mp4" if os.path.exists(mp4) else f"B{b:02d}.png"
    beats=[]; subs=[]
    for li,(s,e) in enumerate(line_time,1):
        subs.append({"line":li,"text":lines[li-1],"start":s,"end":e})
        bts=line2beats.get(str(li),[li])
        if len(bts)==1:
            beats.append({"beat":bts[0],"file":fname(bts[0]),"start":s,"end":e})
        else:
            step=(e-s)/len(bts)
            for k,bn in enumerate(bts):
                beats.append({"beat":bn,"file":fname(bn),"start":round(s+k*step,3),"end":round(s+(k+1)*step,3)})
    beats.sort(key=lambda x:x["start"])  # 시간순 — 비트 재사용(회상 컷) 시 비트번호 정렬은 어긋남
    json.dump({"total_duration":total,"narration":"03_audio_narration_only.mp3","beats":beats,"subtitles":subs},
              open(os.path.join(prod,"04_timing.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(f"✅ 04_timing.json  {len(beats)} beats / {len(subs)} subs")

if __name__=="__main__":
    main()
