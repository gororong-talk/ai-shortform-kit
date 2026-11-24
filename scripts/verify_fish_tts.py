#!/usr/bin/env python3
"""Fish Audio S2-Pro TTS 실계정 검증 — 추측 말고 실제 호출로 확인.

검증 항목 (순서대로):
  1) FISH_API_KEY 존재 (.env 또는 셸 env). 없으면 즉시 안내 후 종료.
  2) POST https://api.fish.audio/v1/tts (raw REST, JSON 바디, model: s2-pro 헤더)
     - 한국어 + 감정태그 [excited] 짧은 문장
  3) HTTP 상태별 정직한 진단:
       200 → mp3 저장 + ffprobe로 유효 오디오(길이>0) 확인 = ✅ 작동
       402 → API 크레딧 미충전 (구독≠API크레딧, fish.audio/app/billing에서 충전)
       401/403 → 키 오류/권한 없음
       기타 → 응답 본문 그대로 출력

공식 문서 검증(2026-06-19): 엔드포인트 /v1/tts · 헤더 model=s2-pro|s1 ·
바디 JSON 또는 msgpack(references 클로닝 시만 msgpack) · format 기본 mp3.
키 값은 절대 출력하지 않는다(prefix 4자만).
"""
import os
import sys
import subprocess
import json

import requests
from dotenv import load_dotenv

ENDPOINT = "https://api.fish.audio/v1/tts"
OUT_DIR = "media/_fish_test"
OUT_MP3 = os.path.join(OUT_DIR, "fish_verify.mp3")
# 검증 문장: 한국어 + 감정태그 + 포즈 토큰 (문서 표기법대로)
TEST_TEXT = "[excited] 안녕하세요, 피쉬 오디오 검증입니다. [break] 한국어 발음 확인합니다."


def die(msg, code=1):
    print(msg)
    sys.exit(code)


def main():
    load_dotenv()
    key = os.environ.get("FISH_API_KEY")
    if not key:
        die(
            "❌ FISH_API_KEY 없음 (.env·셸 env 모두).\n"
            "   → 사용자가 .env에 한 줄 추가해야 함:  FISH_API_KEY=fa-...\n"
            "   (보안상 키 입력은 사용자만. Claude는 입력하지 않음.)"
        )
    print(f"🔑 FISH_API_KEY 감지 (len={len(key)}, prefix={key[:4]}***)")

    # reference_id 인자로 받으면 그 보이스, 없으면 기본 보이스
    ref = sys.argv[1] if len(sys.argv) > 1 else None
    payload = {
        "text": TEST_TEXT,
        "format": "mp3",
        "mp3_bitrate": 192,
        "chunk_length": 200,
        "latency": "normal",
        "normalize": True,
    }
    if ref:
        payload["reference_id"] = ref
        print(f"🎙️  reference_id={ref} (지정 보이스)")
    else:
        print("🎙️  reference_id 없음 → 기본 보이스로 테스트")

    headers = {
        "Authorization": f"Bearer {key}",
        "model": "s2-pro",
        "Content-Type": "application/json",
    }

    print(f"📡 POST {ENDPOINT}  (model=s2-pro, JSON)")
    try:
        r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=60)
    except Exception as e:
        die(f"❌ 네트워크/요청 예외: {e}")

    ct = r.headers.get("content-type", "")
    print(f"   ← HTTP {r.status_code}  content-type={ct}  bytes={len(r.content)}")

    if r.status_code == 402:
        die("❌ 402 = API 크레딧 미충전. 구독 크레딧(웹앱전용)≠API크레딧.\n"
            "   → fish.audio/app/billing 에서 API 크레딧 충전 후 재실행.", 2)
    if r.status_code in (401, 403):
        die(f"❌ {r.status_code} = 키 오류/권한 없음. .env의 FISH_API_KEY 확인.\n"
            f"   본문: {r.text[:300]}", 3)
    if r.status_code != 200:
        die(f"❌ 예상밖 상태 {r.status_code}.\n   본문: {r.text[:500]}", 4)

    # 200: 오디오 저장 + 검증
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_MP3, "wb") as f:
        f.write(r.content)
    print(f"💾 저장: {OUT_MP3} ({len(r.content):,} bytes)")

    # ffprobe로 유효 오디오 확인
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", OUT_MP3],
            capture_output=True, text=True, timeout=20,
        )
        dur = float(out.stdout.strip() or 0)
    except Exception as e:
        die(f"⚠️ 저장은 됐으나 ffprobe 실패: {e}", 5)

    if dur <= 0:
        die(f"❌ 오디오 길이 0 — 빈 파일. (응답이 오디오가 아닐 수 있음)", 6)

    print(f"✅ 검증 성공 — 유효 mp3, 길이 {dur:.2f}s. Fish S2-Pro 한국어+감정태그 작동.")
    print(f"   재생: afplay {OUT_MP3}")


if __name__ == "__main__":
    main()
