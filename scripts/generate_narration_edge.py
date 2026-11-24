#!/usr/bin/env python3
"""generate_narration_edge.py — edge-tts SunHi 네이티브 한국어 나레이션 (무료)

Gemini Kore(크레딧 소진)·OpenAI(발음 NG) 대체. ko-KR-SunHiNeural = 무료 네이티브.
구조는 (보관된) generate_narration_openai.py 와 동일 — 백엔드만 edge-tts.
감정 자연어 지시는 불가 → 구간별 말속도(rate)로 다이내믹 보완.
※ edge_tts 모듈 필요 → 격리 venv 로 실행:
   /tmp/edgetts_venv/bin/python scripts/generate_narration_edge.py <slug> [--gap 0.22]

입력 : productions/<slug>/02_step3_narration.txt + _beat_map.json + _clips.json
출력 : 03_audio_narration_only.mp3 + 04_timing.json
"""
import os, sys, re, json, asyncio, argparse, subprocess
import edge_tts

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF="/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"; FP="/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
if not os.path.exists(FF): FF="ffmpeg"
if not os.path.exists(FP): FP="ffprobe"
RATE=24000
VOICE="ko-KR-SunHiNeural"

NUM_FIX=[("28억","이십팔억"),("9천만 원","구천만 원"),("500원","오백 원"),("300만 원","삼백만 원"),("200만 원","이백만 원"),
         ("5만 원","오만 원"),("1000원","천 원"),("10kg","십 킬로"),
         ("6개월","육 개월"),("5년","오년"),("3년","삼년"),("2년","이년"),("1년","일 년"),("3천","삼천"),("7살","일곱 살")]
def norm_num(t):
    for a,b in NUM_FIX: t=t.replace(a,b)
    return t

def rate_for(i, n):
    # 구간별 말속도 (네이티브 단조로움 보완 — subtle ±)
    # 라인 위치 비율(i/n) 기반 — 절대 라인번호로 하면 다른 길이 production에서 감정 곡선이 깨짐
    # (경계값은 broken_engagement 59라인 검증 매핑과 동일하도록 산출)
    if i==1: return "-5%"      # 콜드오픈 첫 라인은 N 무관 보장 (N<=16이면 1/n>0.06이라 구간 소멸)
    p=i/n
    if p<=0.06: return "-5%"   # 콜드오픈: 무게
    if p<=0.29: return "+0%"   # 설정/떡밥
    if p<=0.45: return "+2%"   # 빌드업 진입
    if p<=0.55: return "+4%"   # 본심/폭로 시작
    if p<=0.80: return "+8%"   # 막장 사이다 (에너지)
    if p<=0.95: return "+0%"   # 본색 (담담/차갑게)
    return "-3%"               # CTA: 또렷·나직이

async def _synth(text, rate, outmp3):
    await edge_tts.Communicate(text, VOICE, rate=rate).save(outmp3)

def synth(text, rate, outmp3, retries=3):
    for k in range(retries):
        try:
            asyncio.run(_synth(text, rate, outmp3))
            if os.path.exists(outmp3) and os.path.getsize(outmp3)>500: return
        except Exception as e:
            print(f"   ⚠️ edge 재시도 {k+1}: {str(e)[:80]}")
    raise SystemExit("❌ edge-tts 생성 실패")

def mp3_to_pcm(mp3):
    r=subprocess.run([FF,"-v","error","-i",mp3,"-f","s16le","-ar",str(RATE),"-ac","1","-"],
                     capture_output=True)
    if r.returncode!=0 or not r.stdout:  # 빈 PCM을 조용히 이어붙이면 라인 누락+타이밍 드리프트
        raise SystemExit(f"❌ pcm 디코드 실패: {(r.stderr or b'').decode(errors='replace')[:120]}")
    return r.stdout

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("slug"); ap.add_argument("--gap",type=float,default=0.22)
    a=ap.parse_args()
    prod=os.path.join(ROOT,"productions",a.slug); adir=os.path.join(prod,"audio"); os.makedirs(adir,exist_ok=True)
    lines=[m.group(1).strip() for l in open(os.path.join(prod,"02_step3_narration.txt"),encoding="utf-8")
           if (m:=re.match(r"^S\d{2}\s+(.*)$", l.strip()))]
    if not lines: raise SystemExit("❌ 02_step3_narration.txt 에서 S## 라인을 못 찾음")
    N=len(lines); print(f"📖 라인 {N}개 (edge SunHi, 네이티브 한국어)")
    # _beat_map 키는 라인번호("1".."N"). "S01" 같은 키면 전 라인이 조용히 1:1 폴백돼 컷 매핑이 무너진다(2026-06-24).
    # TTS(유료) 호출 전에 검사한다 — 생성 뒤에 막으면 돈만 쓰고 멈춘다(2026-11-17 구매자 키트 시험에서 발견).
    _bm = os.path.join(prod, "_beat_map.json")
    if os.path.exists(_bm):
        _keys = json.load(open(_bm, encoding="utf-8"))
        _miss = [str(i) for i in range(1, N + 1) if str(i) not in _keys]
        if _miss:
            sys.exit(f"⛔ _beat_map.json 에 라인번호 키 없음: {_miss[:10]} (키 예: {list(_keys)[:3]}) — 키는 \"1\",\"2\"... 라인번호")
    pcm=bytearray(); line_time=[]; t=0.0; tmp=os.path.join(adir,"_edge_line.mp3")
    for i,ln in enumerate(lines,1):
        rt=rate_for(i,N)
        synth(norm_num(ln), rt, tmp)
        b=mp3_to_pcm(tmp); pcm+=b
        sp=len(b)/(RATE*2); g=0.0 if i==N else a.gap
        pcm+=b"\x00"*(int(g*RATE)*2)
        line_time.append((round(t,3),round(t+sp+g,3))); t+=sp+g
        print(f"   L{i:02d} {sp:.2f}s ({rt}) → {t:.2f}s | {ln[:22]}")
    if os.path.exists(tmp): os.remove(tmp)
    raw=os.path.join(adir,"03_narration_raw.pcm"); open(raw,"wb").write(pcm)
    out=os.path.join(prod,"03_audio_narration_only.mp3")
    out_tmp=out[:-4]+"_tmp.mp3"  # 직접 쓰면 실패 시 부분 파일이 이전 성공본을 덮어씀
    r=subprocess.run([FF,"-y","-loglevel","error","-f","s16le","-ar",str(RATE),"-ac","1","-i",raw,
        "-ac","2","-af","volume=1.1,dynaudnorm=p=0.9:f=250:g=15,apad=pad_dur=1.2","-b:a","192k","-ar","44100",out_tmp])
    if r.returncode!=0 or not os.path.exists(out_tmp): raise SystemExit("❌ 최종 mp3 인코드 실패 (이전 성공본·raw pcm 보존)")
    os.replace(out_tmp,out); os.remove(raw)
    total=round(t+1.2,3); print(f"✅ 03_audio_narration_only.mp3  {total}s ({total/60:.2f}분)")
    # 비트 매핑 (generate_narration 과 동일)
    bm=os.path.join(prod,"_beat_map.json")
    line2beats=json.load(open(bm,encoding="utf-8")) if os.path.exists(bm) else {str(i):[i] for i in range(1,N+1)}
    fimg=os.path.join(prod,"flow_images")
    clips_path=os.path.join(prod,"_clips.json"); clip_set=set()
    if os.path.exists(clips_path):
        try: clip_set=set(int(x) for x in json.load(open(clips_path,encoding="utf-8")).get("clips",[]))
        except Exception: pass
    def fname(b):
        if b in clip_set: return f"B{b:02d}.mp4"
        return f"B{b:02d}.mp4" if os.path.exists(os.path.join(fimg,f"B{b:02d}.mp4")) else f"B{b:02d}.png"
    beats=[]; subs=[]
    for li,(s,e) in enumerate(line_time,1):
        subs.append({"line":li,"text":lines[li-1],"start":s,"end":e})
        bts=line2beats.get(str(li),[li])
        if len(bts)==1: beats.append({"beat":bts[0],"file":fname(bts[0]),"start":s,"end":e})
        else:
            step=(e-s)/len(bts)
            for k,bn in enumerate(bts): beats.append({"beat":bn,"file":fname(bn),"start":round(s+k*step,3),"end":round(s+(k+1)*step,3)})
    beats.sort(key=lambda x:x["start"])  # 시간순 — 비트 재사용(회상 컷) 시 비트번호 정렬은 어긋남
    json.dump({"total_duration":total,"narration":"03_audio_narration_only.mp3","beats":beats,"subtitles":subs},
              open(os.path.join(prod,"04_timing.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=2)
    print(f"✅ 04_timing.json  {len(beats)} beats / {len(subs)} subs")

if __name__=="__main__": main()
