#!/usr/bin/env python3
"""stt_with_fixes.py — FC-018+019 fix 적용된 STT 정식 파이프라인

dirty_inlaws / chinjeong 검증 패턴을 영구 스크립트로 정식화.
임시 /tmp/dirty_stt_pipeline.py + /tmp/fix_dirty_timing.py 통합.

사용법:
  python scripts/stt_with_fixes.py --production 202605010005_dirty_inlaws
  python scripts/stt_with_fixes.py --production <slug> --no-correct  # Gemini 교정 생략
  python scripts/stt_with_fixes.py --production <slug> --no-split    # 라인 분할 생략

산출:
  productions/<slug>/04_timing.json (FC-018+019 fix 적용)

전제:
  - productions/<slug>/03_audio.mp3 존재
  - productions/<slug>/02_step3_narration.txt 존재 (initial_prompt 용)
  - GOOGLE_API_KEY 또는 GEMINI_API_KEY (Gemini 교정 단계용)

FC 회피:
  - FC-018: vad_filter=False + initial_prompt + Gemini 텍스트 교정
  - FC-019: 멀티라인 분할 (음절 비례 시간 배분)
  - FC-019b: 긴 세그먼트 추가 분할 (원본 가사 라인 매칭)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    # load_dotenv() quirk + 빈 환경변수 회피 — dotenv_values + 빈값 덮어쓰기 패턴
    # (shell 에 빈 문자열로 export 된 키도 .env 값으로 덮어씀)
    from dotenv import dotenv_values
    for _k, _v in dotenv_values(ROOT / ".env").items():
        if _v and not os.environ.get(_k):
            os.environ[_k] = _v
except ImportError:
    pass


# ============================================================
# 1. faster-whisper 전사 (FC-018 fix)
# ============================================================
def transcribe(audio_path: Path, lyrics_text: str, model_size: str = "large-v3") -> tuple[list[dict], object]:
    """vad_filter=False + initial_prompt + word_timestamps."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("❌ faster-whisper 미설치 — pip install faster-whisper", file=sys.stderr)
        sys.exit(2)

    print(f"[1/4] faster-whisper {model_size} 로딩…")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"[1/4] 전사 시작 (FC-018 fix: vad off + initial_prompt)…")
    t0 = time.time()
    segs_iter, info = model.transcribe(
        str(audio_path),
        language="ko",
        vad_filter=False,
        beam_size=5,
        initial_prompt=lyrics_text,
        word_timestamps=True,
        temperature=0.0,
        condition_on_previous_text=True,
    )
    segs = []
    for s in segs_iter:
        segs.append({
            "start": round(s.start, 2),
            "end": round(s.end, 2),
            "text": s.text.strip(),
        })
    elapsed = time.time() - t0
    print(f"[1/4] ✅ {len(segs)} 세그먼트 ({elapsed:.0f}s, lang={info.language})")
    if segs:
        cov = segs[-1]["end"] / info.duration * 100
        print(f"      커버: {segs[-1]['end']:.1f}s / {info.duration:.1f}s ({cov:.0f}%)")
    return segs, info


# ============================================================
# 2. 텍스트 교정 (FC-018 fix step 2) — Claude / Gemini 선택
# ============================================================
CORRECTION_PROMPT_TEMPLATE = """당신은 한국어 노래 가사 정렬 전문가입니다.

(A) 원본 가사를 기준으로 (B) Whisper 받아쓴 세그먼트의 텍스트만 교정하세요.

규칙:
1. start/end 그대로 유지 (수정 금지).
2. 텍스트만 원본 가사의 해당 부분으로 교체.
3. 한 세그먼트에 여러 라인이 있을 수 있고, 한 라인이 두 세그먼트에 걸칠 수도 있음.
4. 원본에 없는 텍스트 추가 금지.
5. 숫자는 원본 표기 그대로 (예: '백이십' → '120' 변환 금지).
6. 영문 라인 그대로.
7. 출력은 반드시 JSON 배열, 세그먼트 수 동일.

출력 형식:
[{{"start": 0.0, "end": 14.76, "text": "교정된 텍스트"}}, ...]

(A) 원본:
{orig}

(B) Whisper:
{whisper}
"""


# 실제 교정에 사용된 모델 추적 (method 문자열 정확성)
LAST_CORRECTION_MODEL = "none"


def _apply_corrected(segs: list[dict], corrected: list[dict], label: str) -> list[dict]:
    """공통 후처리 — 세그먼트 수 검증 + diff 카운트 + 시간 보존."""
    global LAST_CORRECTION_MODEL
    if len(corrected) != len(segs):
        print(f"[!] 세그먼트 수 불일치 ({len(corrected)} vs {len(segs)}) — 원본 유지")
        return segs
    diff = sum(
        1 for i, c in enumerate(corrected)
        if c.get("text", "").strip() != segs[i]["text"].strip()
    )
    for i, c in enumerate(corrected):
        c["start"] = segs[i]["start"]
        c["end"] = segs[i]["end"]
    print(f"[2/4] ✅ 교정 diff {diff}/{len(segs)} ({label})")
    LAST_CORRECTION_MODEL = label
    return corrected


def correct_with_claude(segs: list[dict], orig_lines: list[str]) -> list[dict]:
    """Claude Sonnet 으로 가사 교정 (FC-028 이후 기본 — Gemini 의존성 제거)."""
    try:
        from anthropic import Anthropic
    except ImportError:
        print("[!] anthropic SDK 미설치 — Gemini 폴백 시도", file=sys.stderr)
        return correct_with_gemini(segs, orig_lines)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[!] ANTHROPIC_API_KEY 없음 — Gemini 폴백 시도", file=sys.stderr)
        return correct_with_gemini(segs, orig_lines)

    print(f"[2/4] Claude 가사 교정 ({len(segs)} 세그먼트)…")
    client = Anthropic(api_key=api_key)

    prompt = CORRECTION_PROMPT_TEMPLATE.format(
        orig=chr(10).join(orig_lines),
        whisper=json.dumps(segs, ensure_ascii=False, indent=2),
    )

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=8192,
            temperature=0.1,
            system="당신은 한국어 가사 정렬 전문가입니다. 사용자가 요청하면 반드시 JSON 배열만 출력하고 다른 텍스트는 절대 출력하지 않습니다.",
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "["},  # JSON prefill
            ],
        )
        # Prefill 적용 — 응답은 "..." 형식으로 시작 (앞에 [ 가 이미 있음)
        text = "[" + msg.content[0].text
    except Exception as e:
        print(f"[!] Claude 호출 실패: {e} — Gemini 폴백 시도", file=sys.stderr)
        return correct_with_gemini(segs, orig_lines)

    try:
        # JSON 끝에 다른 텍스트 있을 경우 ] 찾아서 자르기
        end_idx = text.rfind("]")
        if end_idx > 0:
            text = text[: end_idx + 1]
        corrected = json.loads(text)
    except Exception as e:
        print(f"[!] Claude 응답 파싱 실패: {e} — 원본 유지", file=sys.stderr)
        return segs

    return _apply_corrected(segs, corrected, "Claude")


def correct_with_gemini(segs: list[dict], orig_lines: list[str]) -> list[dict]:
    """Gemini 2.5 Flash 폴백 (FC-028 이후 Claude 가 기본, Gemini 는 폴백)."""
    try:
        from google import genai
    except ImportError:
        print("[!] google-genai 미설치 — 교정 생략", file=sys.stderr)
        return segs

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[!] GOOGLE_API_KEY 없음 — 교정 생략", file=sys.stderr)
        return segs

    print(f"[2/4] Gemini 가사 교정 ({len(segs)} 세그먼트)…")
    client = genai.Client(api_key=api_key)

    prompt = CORRECTION_PROMPT_TEMPLATE.format(
        orig=chr(10).join(orig_lines),
        whisper=json.dumps(segs, ensure_ascii=False, indent=2),
    )

    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"temperature": 0.1, "response_mime_type": "application/json"},
        )
        corrected = json.loads(resp.text)
    except Exception as e:
        print(f"[!] Gemini 호출/파싱 실패: {e} — 원본 유지", file=sys.stderr)
        return segs

    return _apply_corrected(segs, corrected, "Gemini")


# ============================================================
# 3. 멀티라인 분할 (FC-019 fix)
# ============================================================
def split_multiline(segs: list[dict]) -> list[dict]:
    """한 세그먼트 안 \\n 으로 묶인 여러 라인을 음절 비례로 시간 분배."""
    new_segs = []
    for s in segs:
        text = s["text"].strip()
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if len(lines) <= 1:
            new_segs.append({"start": s["start"], "end": s["end"], "text": lines[0] if lines else ""})
            continue
        dur = s["end"] - s["start"]
        weights = [max(len(ln), 1) for ln in lines]
        total_w = sum(weights)
        cur = s["start"]
        for ln, w in zip(lines, weights):
            seg_dur = dur * w / total_w
            new_segs.append({"start": round(cur, 2), "end": round(cur + seg_dur, 2), "text": ln})
            cur += seg_dur
    return new_segs


# ============================================================
# 4. 긴 세그먼트 추가 분할 (FC-019b — 원본 라인 매칭)
# ============================================================
def normalize(s: str) -> str:
    out = []
    for ch in s:
        if ch.isspace() or ch in '"\'""''`':
            continue
        out.append(ch)
    return "".join(out)


def split_long_segments(segs: list[dict], orig_lines: list[str], threshold: float = 10.0) -> list[dict]:
    """길이 threshold 초 이상 세그먼트를 원본 라인 head 매칭으로 분할."""
    new_segs = []
    line_idx = 0
    for s in segs:
        text = s["text"].strip()
        dur = s["end"] - s["start"]
        if dur < threshold:
            new_segs.append(s)
            continue
        text_norm = normalize(text)
        matched_lines = []
        cur_idx = line_idx
        while cur_idx < len(orig_lines):
            orig = orig_lines[cur_idx]
            orig_norm = normalize(orig)
            if not orig_norm:
                cur_idx += 1
                continue
            head = orig_norm[:6]
            if head and head in text_norm:
                matched_lines.append(orig)
                pos = text_norm.find(head)
                text_norm = text_norm[pos + len(orig_norm):]
                cur_idx += 1
            else:
                break
        if not matched_lines:
            new_segs.append(s)
            continue
        weights = [max(len(ln), 1) for ln in matched_lines]
        total_w = sum(weights)
        cur_t = s["start"]
        for ln, w in zip(matched_lines, weights):
            seg_dur = dur * w / total_w
            new_segs.append({
                "start": round(cur_t, 2),
                "end": round(cur_t + seg_dur, 2),
                "text": ln,
            })
            cur_t += seg_dur
        line_idx = cur_idx
    return new_segs


# ============================================================
# 메인
# ============================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--production", required=True, help="production slug")
    ap.add_argument("--no-correct", action="store_true", help="텍스트 교정 생략")
    ap.add_argument("--no-split", action="store_true", help="멀티라인 분할 생략")
    ap.add_argument("--no-split-long", action="store_true", help="긴 세그먼트 추가 분할 생략")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument(
        "--correction-model",
        default="claude",
        choices=["claude", "gemini"],
        help="텍스트 교정 LLM (기본 claude — FC-028 이후 Gemini 의존성 제거). 'gemini' 강제 시 폴백 모드",
    )
    args = ap.parse_args()

    prod = ROOT / "productions" / args.production
    audio = prod / "03_audio.mp3"
    lyrics_path = prod / "02_step3_narration.txt"
    out_path = prod / "04_timing.json"

    if not audio.exists():
        print(f"❌ {audio} 없음")
        sys.exit(1)
    if not lyrics_path.exists():
        print(f"❌ {lyrics_path} 없음")
        sys.exit(1)

    # 가사 본문에서 [LYRICS] 이후 + 섹션태그 제외
    raw = lyrics_path.read_text(encoding="utf-8")
    if "[LYRICS]" in raw:
        raw = raw.split("[LYRICS]", 1)[1]
    orig_lines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("["):
            continue
        if line.startswith("(") and line.endswith(")"):
            continue
        orig_lines.append(line)
    prompt_text = " / ".join(orig_lines)
    print(f"📝 원본 가사: {len(orig_lines)} 라인 ({len(prompt_text)}자 prompt)")

    # 기존 timing 백업
    if out_path.exists():
        backup_dir = prod / "_backup_stt"
        backup_dir.mkdir(exist_ok=True)
        backup = backup_dir / f"04_timing.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        shutil.copy(out_path, backup)
        print(f"📦 기존 timing 백업: {backup.name}")

    # STEP 1: 전사
    segs, info = transcribe(audio, prompt_text, model_size=args.model)

    # STEP 2: 텍스트 교정 (Claude 기본, --correction-model gemini 시 Gemini)
    if not args.no_correct:
        if args.correction_model == "claude":
            segs = correct_with_claude(segs, orig_lines)
        else:
            segs = correct_with_gemini(segs, orig_lines)

    # STEP 3: 멀티라인 분할
    if not args.no_split:
        before = len(segs)
        segs = split_multiline(segs)
        print(f"[3/4] ✅ 멀티라인 분할: {before} → {len(segs)}")

    # STEP 4: 긴 세그먼트 추가 분할
    if not args.no_split_long:
        before = len(segs)
        segs = split_long_segments(segs, orig_lines, threshold=10.0)
        if len(segs) != before:
            print(f"[4/4] ✅ 긴 세그먼트 분할: {before} → {len(segs)}")
        else:
            print(f"[4/4] 긴 세그먼트 없음 (모두 < 10s)")

    # 저장
    out = {
        "audio_file": "03_audio.mp3",
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "total_segments": len(segs),
        "full_text": " ".join(s["text"] for s in segs),
        "segments": segs,
        "method": f"faster-whisper {args.model} + initial_prompt + VAD off + {LAST_CORRECTION_MODEL} correction (requested={args.correction_model}) + multiline+longseg split (FC-018+019 fix, FC-028 mitigation)",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"💾 저장: {out_path}")
    if segs:
        cov = segs[-1]["end"] / info.duration * 100
        print(f"   세그먼트: {len(segs)}, 커버: {segs[-1]['end']:.1f}s ({cov:.0f}%)")


if __name__ == "__main__":
    main()
