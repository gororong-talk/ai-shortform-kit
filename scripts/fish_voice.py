#!/usr/bin/env python3
"""Fish Audio 보이스 레지스트리 헬퍼 — data/fish_voices.json 기반.

사용:
  python scripts/fish_voice.py list                  # 등록 보이스 표
  python scripts/fish_voice.py list --role 사연        # 역할 필터
  python scripts/fish_voice.py say <key> ["텍스트"]    # 그 보이스로 TTS 생성+재생
  python scripts/fish_voice.py say <key> --no-play     # 재생 없이 파일만

검증된 raw REST(/v1/tts, model: s2-pro, JSON). 키는 .env FISH_API_KEY(비노출).
샘플 저장: media/_fish_test/voice_<key>.mp3
"""
import os
import sys
import json
import subprocess

import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "data", "fish_voices.json")
OUT_DIR = os.path.join(ROOT, "media", "_fish_test")
ENDPOINT = "https://api.fish.audio/v1/tts"
DEFAULT_TEXT = "[slightly sad] 안녕하세요. 이건 보이스 청취용 샘플입니다. [break] [determined] 잘 어울리는지 들어봐 주세요."


def load_registry():
    with open(REG, encoding="utf-8") as f:
        return json.load(f)


def cmd_list(reg, role=None):
    rows = reg["voices"]
    if role:
        rows = [v for v in rows if any(role in r for r in v.get("roles", []))]
    print(f"{'key':24}{'gender':7}{'audition':9}{'title'}")
    for v in rows:
        a = "들어봄" if v.get("audition") else "-"
        print(f"{v['key']:24}{v.get('gender','?'):7}{a:9}{v['title']}  {v.get('roles')}")
    print(f"\n총 {len(rows)}개. 배정: {json.dumps(reg.get('assignments',{}),ensure_ascii=False)}")


def cmd_say(reg, key, text, play=True):
    v = next((x for x in reg["voices"] if x["key"] == key), None)
    if not v:
        sys.exit(f"❌ key '{key}' 없음. `list`로 확인.")
    load_dotenv(os.path.join(ROOT, ".env"))
    api = os.environ.get("FISH_API_KEY")
    if not api:
        sys.exit("❌ FISH_API_KEY 없음(.env). 사용자가 추가해야 함.")
    headers = {"Authorization": f"Bearer {api}", "model": "s2-pro", "Content-Type": "application/json"}
    payload = {"text": text, "reference_id": v["id"], "format": "mp3",
               "mp3_bitrate": 192, "latency": "normal", "normalize": True, "chunk_length": 200}
    print(f"🎙️ {key} ({v['title']}) ← {text[:50]}…")
    r = requests.post(ENDPOINT, headers=headers, json=payload, timeout=90)
    if r.status_code != 200:
        sys.exit(f"❌ HTTP {r.status_code}: {r.text[:200]}")
    os.makedirs(OUT_DIR, exist_ok=True)
    fn = os.path.join(OUT_DIR, f"voice_{key}.mp3")
    with open(fn, "wb") as f:
        f.write(r.content)
    print(f"💾 {fn} ({len(r.content):,}B)")
    if play:
        subprocess.run(["afplay", fn])


def main():
    a = sys.argv[1:]
    if not a or a[0] == "list":
        role = a[a.index("--role") + 1] if "--role" in a else None
        cmd_list(load_registry(), role)
    elif a[0] == "say" and len(a) >= 2:
        key = a[1]
        play = "--no-play" not in a
        rest = [x for x in a[2:] if not x.startswith("--")]
        text = rest[0] if rest else DEFAULT_TEXT
        cmd_say(load_registry(), key, text, play)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
