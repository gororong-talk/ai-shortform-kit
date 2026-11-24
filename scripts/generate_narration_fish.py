#!/usr/bin/env python3
"""generate_narration_fish.py — Fish Audio S2-Pro 감정 나레이션 (신규 1순위, 결제·검증됨 2026-06-19)

음질·감정 표현이 edge SunHi 우위라 신규 표준. 위계: Fish > SunHi > Gemini Kore(막힘) > ElevenLabs.
구조는 generate_narration_edge.py 와 동일 — 백엔드만 edge-tts → Fish raw REST(/v1/tts, model: s2-pro, JSON).
검증 호출 형태: scripts/verify_fish_tts.py · scripts/fish_voice.py (실계정 200 OK 확인).

edge 와 다른 점 (이것만):
  1) TTS 백엔드 = Fish REST (requests). edge venv(/tmp/edgetts_venv) 불필요 — requests+dotenv 만 있으면 됨.
  2) 보이스 = data/fish_voices.json 의 assignments 로 자동 배정 (00_meta.json 의 track/channel/format 기반).
       사연숏폼 f_soft_shorts · 롱폼 f_storytelling · 명언 f_anchor_calm · 키즈/토리 char_cat_cute.
       --voice <key|reference_id> 로 강제 가능.
  3) 감정 = 라인 앞 인라인 태그([slightly sad]/[angry]/[determined] 등) 그대로 반영(draft-narration 의도 경로).
       태그 없는 라인은 --emotion-profile(auto) 로 위치기반 보수적 태깅(open·폭로·CTA 만).
       edge 의 구간별 rate 변주를 Fish 에선 감정태그가 대체.

같은 점 (compose 계약 유지 — 절대 바꾸지 말 것):
  - 입력 productions/<slug>/02_step3_narration.txt (S## 라인) + _beat_map.json + _clips.json
  - 라인별 합성 → 디코드 PCM 길이로 길이 측정(ffprobe 아님) → --gap 무음 → stereo 44.1k apad mp3
  - 출력 03_audio_narration_only.mp3(stereo, padded) + 04_timing.json (top: total_duration/narration/beats/subtitles)
    → compose_narration.py 가 이 정확한 스키마를 읽고 오디오 후처리는 안 함. Fish 도 완성형 mp3 를 내야 함.

실행:
  .venv/bin/python scripts/generate_narration_fish.py <slug> [--gap 0.22] [--voice <key>] [--emotion-profile auto]
  (requests + python-dotenv 필요. 키 = .env 의 FISH_API_KEY, 하드코딩 금지·비노출)
"""
import os, sys, re, json, argparse, subprocess

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"; FP = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
if not os.path.exists(FF): FF = "ffmpeg"
if not os.path.exists(FP): FP = "ffprobe"
RATE = 24000
ENDPOINT = "https://api.fish.audio/v1/tts"
REG_PATH = os.path.join(ROOT, "data", "fish_voices.json")

# edge 모듈과 동일한 한국어 숫자 정규화 (Fish normalize=True 와 병용 — 핵심 금액은 한글 고정)
NUM_FIX = [("28억", "이십팔억"), ("9천만 원", "구천만 원"), ("500원", "오백 원"), ("300만 원", "삼백만 원"), ("200만 원", "이백만 원"),
           ("5만 원", "오만 원"), ("1000원", "천 원"), ("10kg", "십 킬로"),
           ("6개월", "육 개월"), ("5년", "오년"), ("3년", "삼년"), ("2년", "이년"), ("1년", "일 년"), ("3천", "삼천"), ("7살", "일곱 살")]


def norm_num(t):
    for a, b in NUM_FIX:
        t = t.replace(a, b)
    return t


# ── 보이스 자동 배정 ─────────────────────────────────────────────────────────
def resolve_voice(prod, override):
    """(key, reference_id, title) 반환. override = voices key 또는 raw reference_id."""
    reg = json.load(open(REG_PATH, encoding="utf-8"))
    voices = {v["key"]: v for v in reg["voices"]}
    assign = reg.get("assignments", {})

    def by_key(k):
        v = voices.get(k)
        return (k, v["id"], v.get("title", "")) if v else (k, k, "(raw id)")

    if override:
        if override in voices:
            return by_key(override)
        return (override, override, "(raw reference_id)")  # 32-hex 직접 지정 허용

    meta = {}
    mp = os.path.join(prod, "00_meta.json")
    if os.path.exists(mp):
        try:
            meta = json.load(open(mp, encoding="utf-8"))
        except Exception:
            pass
    track = (meta.get("track") or "").lower()
    channel = meta.get("channel") or ""
    fmt = (meta.get("format") or "").lower()
    dur = meta.get("target_duration_sec") or 0
    base = os.path.basename(prod).lower()

    if track == "kids_edu" or "토리" in channel or "mascot" in base:
        return by_key(assign.get("kids_mascot_mascot", "char_cat_cute"))
    if "하루" in channel or "your_wisdom_channel" in channel or base.startswith("wisdom"):
        return by_key(assign.get("wisdom", "f_anchor_calm"))
    longish = ("long" in fmt) or (isinstance(dur, (int, float)) and dur > 150)
    return by_key(assign.get("sayeon_long" if longish else "sayeon_short",
                             "f_storytelling" if longish else "f_soft_shorts"))


def auto_profile(voice_key):
    if voice_key in ("char_cat_cute", "kid_bright"):
        return "kids"
    if voice_key == "f_anchor_calm":
        return "wisdom"
    return "sayeon"


# 문서화된 감정 태그만 사용 (_meta.emotion_tags). 검증되지 않은 태그가 그대로 읽히는 사고 방지.
def emotion_for(i, n, profile):
    """태그 없는 라인의 보수적 fallback. 인라인 태그가 있으면 이 함수는 안 탐."""
    if profile in ("none", "neutral"):
        return ""
    p = i / n
    if profile == "kids":
        return "excited" if i == 1 else ""      # 인트로만 밝게, 나머지는 voice 자연 프로소디
    if profile == "wisdom":
        return ""                                # 차분 voice 가 톤 담당 — 위험 태그 회피
    # sayeon 막장 사이다 아크 — 보수적(오픈/폭로/CTA 만, 과태깅 금지)
    if i == 1:
        return "slightly sad"                    # 콜드오픈: 무게
    if i == n:
        return "determined"                      # CTA: 단호
    if 0.48 <= p <= 0.56:
        return "angry"                           # 폭로 구간(단일 존)
    return ""


TAG_RE = re.compile(r"^((?:\s*\[[^\]]+\])+)\s*(.*)$", re.S)


def split_tags(s):
    m = TAG_RE.match(s)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return "", s.strip()


# ── Fish 합성 ────────────────────────────────────────────────────────────────
def fish_synth(text, ref_id, api, outmp3, retries=3):
    headers = {"Authorization": f"Bearer {api}", "model": "s2-pro", "Content-Type": "application/json"}
    payload = {"text": text, "format": "mp3", "mp3_bitrate": 192,
               "latency": "normal", "normalize": True, "chunk_length": 200}
    if ref_id:
        payload["reference_id"] = ref_id
    last = ""
    for k in range(retries):
        try:
            r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=120)
            if r.status_code == 200 and len(r.content) > 500:
                with open(outmp3, "wb") as f:
                    f.write(r.content)
                return
            if r.status_code in (401, 403):
                raise SystemExit(f"❌ Fish 인증 실패 {r.status_code} — .env FISH_API_KEY 확인 ({r.text[:120]})")
            if r.status_code == 402:
                raise SystemExit("❌ Fish 402 = API 크레딧 미충전 (구독≠API크레딧). fish.audio/app/billing 충전 후 재실행.")
            last = f"HTTP {r.status_code}: {r.text[:160]}"
        except SystemExit:
            raise
        except Exception as e:
            last = str(e)[:160]
        print(f"   ⚠️ Fish 재시도 {k + 1}: {last}")
    raise SystemExit(f"❌ Fish TTS 생성 실패: {last}")


def mp3_to_pcm(mp3):
    r = subprocess.run([FF, "-v", "error", "-i", mp3, "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-"],
                       capture_output=True)
    if r.returncode != 0 or not r.stdout:  # 빈 PCM 을 조용히 이어붙이면 라인 누락+타이밍 드리프트
        raise SystemExit(f"❌ pcm 디코드 실패: {(r.stderr or b'').decode(errors='replace')[:120]}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser(description="Fish Audio S2-Pro 감정 나레이션 (edge 인터페이스 호환)")
    ap.add_argument("slug")
    ap.add_argument("--gap", type=float, default=0.22)
    ap.add_argument("--voice", help="fish_voices.json key 또는 raw reference_id (미지정=00_meta 기반 자동)")
    ap.add_argument("--emotion-profile", default="auto",
                    choices=["auto", "sayeon", "kids", "wisdom", "neutral", "none"],
                    help="인라인 태그 없는 라인의 fallback 감정 (기본 auto=voice 기반)")
    ap.add_argument("--no-emotion", action="store_true", help="fallback 감정 태깅 끔(인라인 태그는 유지)")
    a = ap.parse_args()

    load_dotenv(os.path.join(ROOT, ".env"))
    api = os.environ.get("FISH_API_KEY")
    if not api:
        raise SystemExit("❌ FISH_API_KEY 없음(.env). 사용자가 .env 에 FISH_API_KEY=fa-... 추가해야 함(비노출).")
    print(f"🔑 FISH_API_KEY 감지 (len={len(api)}, prefix={api[:4]}***)")

    prod = os.path.join(ROOT, "productions", a.slug)
    adir = os.path.join(prod, "audio"); os.makedirs(adir, exist_ok=True)

    vkey, ref_id, vtitle = resolve_voice(prod, a.voice)
    profile = "none" if a.no_emotion else (auto_profile(vkey) if a.emotion_profile == "auto" else a.emotion_profile)
    print(f"🎙️  voice = {vkey} ({vtitle}) | reference_id={ref_id[:8]}… | emotion-profile={profile}")
    print(f"     (다른 보이스로 바꾸려면 --voice <key>, 청취 = scripts/fish_voice.py say <key>)")

    src = os.path.join(prod, "02_step3_narration.txt")
    lines = [m.group(1).strip() for l in open(src, encoding="utf-8")
             if (m := re.match(r"^S\d{2}\s+(.*)$", l.strip()))]
    if not lines:
        raise SystemExit("❌ 02_step3_narration.txt 에서 S## 라인을 못 찾음")
    N = len(lines); print(f"📖 라인 {N}개 (Fish S2-Pro, 네이티브 한국어 + 감정태그)")
    # _beat_map 키는 라인번호("1".."N"). "S01" 같은 키면 전 라인이 조용히 1:1 폴백돼 컷 매핑이 무너진다(2026-06-24).
    # TTS(유료) 호출 전에 검사한다 — 생성 뒤에 막으면 돈만 쓰고 멈춘다(2026-11-17 구매자 키트 시험에서 발견).
    _bm = os.path.join(prod, "_beat_map.json")
    if os.path.exists(_bm):
        _keys = json.load(open(_bm, encoding="utf-8"))
        _miss = [str(i) for i in range(1, N + 1) if str(i) not in _keys]
        if _miss:
            sys.exit(f"⛔ _beat_map.json 에 라인번호 키 없음: {_miss[:10]} (키 예: {list(_keys)[:3]}) — 키는 \"1\",\"2\"... 라인번호")

    pcm = bytearray(); line_time = []; t = 0.0; tmp = os.path.join(adir, "_fish_line.mp3")
    # ⚠️ 자막 텍스트(display)는 TTS 텍스트와 분리: 감정태그([slightly sad] 등)와 숫자정규화(오년)를
    #    빼고 원문만 자막에 쓴다. 안 그러면 '[slightly sad]'가 영상 자막에 번인됨(Fish 전용 함정).
    display = []
    for i, ln in enumerate(lines, 1):
        lead, body = split_tags(ln)
        display.append(body)                 # 자막용: 태그 제거·원본 숫자 유지
        tts_body = norm_num(body)
        if not lead and profile != "none":
            emo = emotion_for(i, N, profile)
            if emo:
                lead = f"[{emo}]"
        text = (lead + " " + tts_body).strip() if lead else tts_body
        fish_synth(text, ref_id, api, tmp)
        b = mp3_to_pcm(tmp); pcm += b
        sp = len(b) / (RATE * 2); g = 0.0 if i == N else a.gap
        pcm += b"\x00" * (int(g * RATE) * 2)
        line_time.append((round(t, 3), round(t + sp + g, 3))); t += sp + g
        tag_disp = lead if lead else "·"
        print(f"   L{i:02d} {sp:.2f}s {tag_disp:14} → {t:.2f}s | {body[:22]}")
    if os.path.exists(tmp):
        os.remove(tmp)

    raw = os.path.join(adir, "03_narration_raw.pcm"); open(raw, "wb").write(pcm)
    out = os.path.join(prod, "03_audio_narration_only.mp3")
    out_tmp = out[:-4] + "_tmp.mp3"  # 직접 쓰면 실패 시 부분 파일이 이전 성공본을 덮어씀
    r = subprocess.run([FF, "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", raw,
                        "-ac", "2", "-af", "volume=1.1,dynaudnorm=p=0.9:f=250:g=15,apad=pad_dur=1.2",
                        "-b:a", "192k", "-ar", "44100", out_tmp])
    if r.returncode != 0 or not os.path.exists(out_tmp):
        raise SystemExit("❌ 최종 mp3 인코드 실패 (이전 성공본·raw pcm 보존)")
    os.replace(out_tmp, out); os.remove(raw)
    total = round(t + 1.2, 3); print(f"✅ 03_audio_narration_only.mp3  {total}s ({total / 60:.2f}분)")

    # 비트 매핑 (generate_narration_edge 와 동일 — compose 계약)
    bm = os.path.join(prod, "_beat_map.json")
    line2beats = json.load(open(bm, encoding="utf-8")) if os.path.exists(bm) else {str(i): [i] for i in range(1, N + 1)}
    fimg = os.path.join(prod, "flow_images")
    clips_path = os.path.join(prod, "_clips.json"); clip_set = set()
    if os.path.exists(clips_path):
        try:
            clip_set = set(int(x) for x in json.load(open(clips_path, encoding="utf-8")).get("clips", []))
        except Exception:
            pass

    def fname(b):
        if b in clip_set:
            return f"B{b:02d}.mp4"
        return f"B{b:02d}.mp4" if os.path.exists(os.path.join(fimg, f"B{b:02d}.mp4")) else f"B{b:02d}.png"

    beats = []; subs = []
    for li, (s, e) in enumerate(line_time, 1):
        subs.append({"line": li, "text": display[li - 1], "start": s, "end": e})  # 태그·정규화 제거된 원문
        bts = line2beats.get(str(li), [li])
        if len(bts) == 1:
            beats.append({"beat": bts[0], "file": fname(bts[0]), "start": s, "end": e})
        else:
            step = (e - s) / len(bts)
            for k, bn in enumerate(bts):
                beats.append({"beat": bn, "file": fname(bn), "start": round(s + k * step, 3), "end": round(s + (k + 1) * step, 3)})
    beats.sort(key=lambda x: x["start"])  # 시간순 — 비트 재사용(회상 컷) 시 비트번호 정렬은 어긋남
    json.dump({"total_duration": total, "narration": "03_audio_narration_only.mp3", "beats": beats, "subtitles": subs},
              open(os.path.join(prod, "04_timing.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ 04_timing.json  {len(beats)} beats / {len(subs)} subs")


if __name__ == "__main__":
    main()
