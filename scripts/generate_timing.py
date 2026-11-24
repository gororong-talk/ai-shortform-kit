#!/usr/bin/env python3
"""
generate_timing.py — 오디오 MP3 → timing.json 자동 생성

파이프라인:
  1) faster-whisper (large-v3) 로 세그먼트별 start/end/text 추출
  2) 레퍼런스 나레이션 원문이 있으면 Gemini 로 철자/단어 교정
     - 없으면 Whisper 결과 그대로 사용
  3) productions/{slug}/04_timing.json 포맷으로 저장

사용법:
  python3 scripts/generate_timing.py --production 202604220116_청춘의_청구서
  python3 scripts/generate_timing.py --audio path/to.mp3 --out path/to/timing.json
  python3 scripts/generate_timing.py --production <slug> --no-correct  # Gemini 교정 생략

전제:
  - productions/{slug}/03_audio.mp3 존재
  - (옵션) productions/{slug}/02_step3_narration.txt — 원문 나레이션. 있으면 교정에 사용
  - GOOGLE_API_KEY or GEMINI_API_KEY (교정 단계에서만 필요)

의존성:
  pip install faster-whisper google-genai python-dotenv
"""

from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

PROJECT_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────────────────────────────
# 1) faster-whisper 전사
# ─────────────────────────────────────────────────────────────
def transcribe(audio_path: Path, model_size: str = "large-v3") -> list[dict]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("[!] faster-whisper 미설치. `pip install faster-whisper` 실행 필요.", file=sys.stderr)
        sys.exit(2)

    print(f"[1/3] faster-whisper {model_size} 로딩…")
    # CPU 기본 (MPS 미지원). GPU 있으면 device='cuda' 로 변경 가능.
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"[1/3] 전사 시작: {audio_path.name}")
    segments_iter, info = model.transcribe(
        str(audio_path),
        language="ko",
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        beam_size=5,
    )

    segs = []
    for s in segments_iter:
        segs.append({
            "start": round(s.start, 2),
            "end": round(s.end, 2),
            "text": s.text.strip(),
        })
    print(f"[1/3] 완료: {len(segs)} 세그먼트, 언어={info.language} (conf {info.language_probability:.2f})")
    return segs


# ─────────────────────────────────────────────────────────────
# 2) Gemini 기반 교정 (레퍼런스 있을 때)
# ─────────────────────────────────────────────────────────────
CORRECTION_PROMPT = """너는 한국어 STT 결과를 교정하는 편집자다.

아래에 (A) 원본 나레이션 대본과 (B) Whisper 가 추출한 세그먼트 타임라인이 있다.
(B) 의 각 세그먼트 text 를 (A) 의 대본과 매칭해 교정해줘.

규칙:
- start / end 시간은 절대 변경 금지
- 세그먼트 개수와 순서도 변경 금지
- text 만 교정 (숫자 오류, 오타, 동음이의어 교정 포함)
- (A) 에 없는 단어가 나오면 (A) 의 가장 가까운 단어로 치환
- (A) 와 완전히 다른 내용이면 (B) 원문 유지하고 끝에 "[?]" 표시
- 결과는 JSON 배열로만 반환. 설명 텍스트 금지.

출력 형식 (JSON 배열):
[
  {{"start": 14.76, "end": 16.16, "text": "교정된 텍스트"}},
  ...
]

(A) 원본 나레이션:
---
{narration}
---

(B) Whisper 세그먼트:
{segments_json}
"""


def correct_with_gemini(segs: list[dict], narration: str) -> list[dict]:
    try:
        from google import genai
    except ImportError:
        print("[!] google-genai 미설치. 교정 생략.", file=sys.stderr)
        return segs

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[!] GOOGLE_API_KEY/GEMINI_API_KEY 없음. 교정 생략.", file=sys.stderr)
        return segs

    print(f"[2/3] Gemini 교정 중… ({len(segs)} 세그먼트)")
    client = genai.Client(api_key=api_key)

    prompt = CORRECTION_PROMPT.format(
        narration=narration.strip(),
        segments_json=json.dumps(segs, ensure_ascii=False, indent=2),
    )

    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "temperature": 0.1,
            "response_mime_type": "application/json",
        },
    )

    try:
        corrected = json.loads(resp.text)
    except Exception as e:
        print(f"[!] Gemini 응답 파싱 실패: {e}. Whisper 원본 유지.", file=sys.stderr)
        return segs

    if len(corrected) != len(segs):
        print(f"[!] 교정 후 세그먼트 수 불일치 ({len(corrected)} vs {len(segs)}). 원본 유지.", file=sys.stderr)
        return segs

    # start/end 는 원본 값으로 강제 (Gemini 가 실수로 바꾸는 것 방지)
    for i, c in enumerate(corrected):
        c["start"] = segs[i]["start"]
        c["end"] = segs[i]["end"]

    # 교정 diff 리포트
    diff_count = sum(1 for i, c in enumerate(corrected) if c["text"] != segs[i]["text"])
    print(f"[2/3] 교정 완료: {diff_count}/{len(segs)} 세그먼트 수정됨")
    return corrected


# ─────────────────────────────────────────────────────────────
# 3) timing.json 포맷으로 저장
# ─────────────────────────────────────────────────────────────
def save_timing(segs: list[dict], audio_path: Path, out_path: Path):
    full_text = " ".join(s["text"] for s in segs).strip()
    payload = {
        "audio_file": audio_path.name,
        "language": "ko",
        "total_segments": len(segs),
        "full_text": full_text,
        "segments": segs,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[3/3] 저장 완료: {out_path} ({len(segs)} 세그먼트, {len(full_text)} 문자)")


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="MP3 → timing.json 자동 생성")
    ap.add_argument("--production", type=str, help="productions/ 하위 슬러그 폴더명 (예: 202604220116_청춘의_청구서)")
    ap.add_argument("--audio", type=str, help="오디오 파일 경로 (--production 미사용 시)")
    ap.add_argument("--narration", type=str, help="레퍼런스 나레이션 파일 (--production 미사용 시)")
    ap.add_argument("--out", type=str, help="출력 timing.json 경로 (--production 미사용 시)")
    ap.add_argument("--model", type=str, default="large-v3", help="faster-whisper 모델 크기 (default: large-v3)")
    ap.add_argument("--no-correct", action="store_true", help="Gemini 교정 생략")
    args = ap.parse_args()

    if args.production:
        prod_dir = PROJECT_DIR / "productions" / args.production
        if not prod_dir.is_dir():
            print(f"[!] production 폴더 없음: {prod_dir}", file=sys.stderr)
            sys.exit(1)
        audio_path = prod_dir / "03_audio.mp3"
        narration_path = prod_dir / "02_step3_narration.txt"
        out_path = prod_dir / "04_timing.json"
    else:
        if not args.audio or not args.out:
            print("[!] --production 또는 (--audio + --out) 중 하나 필요", file=sys.stderr)
            sys.exit(1)
        audio_path = Path(args.audio)
        narration_path = Path(args.narration) if args.narration else None
        out_path = Path(args.out)

    if not audio_path.is_file():
        print(f"[!] 오디오 파일 없음: {audio_path}", file=sys.stderr)
        sys.exit(1)

    # 1) Whisper 전사
    segs = transcribe(audio_path, model_size=args.model)

    # 2) Gemini 교정 (옵션)
    if not args.no_correct and narration_path and narration_path.is_file():
        narration = narration_path.read_text(encoding="utf-8")
        segs = correct_with_gemini(segs, narration)
    else:
        reason = "--no-correct" if args.no_correct else "나레이션 레퍼런스 없음"
        print(f"[2/3] 교정 건너뜀 ({reason})")

    # 3) 저장
    save_timing(segs, audio_path, out_path)


if __name__ == "__main__":
    main()
