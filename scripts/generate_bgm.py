#!/usr/bin/env python3
"""
generate_bgm.py — ACE Step v1.5 클라우드 API 로 productions/<slug>/03_audio.mp3 생성

파이프라인 Step 3 (Lyria 수동 웹 UI 자리) 를 대체한다.

기본 호출 대상: https://api.acemusic.ai  (FREE 티어, MIT + 상업 이용 허용)
  → 로컬 GPU 서버를 띄운 경우에만 --server 플래그로 127.0.0.1:8002 지정.

전제:
  * .env 에 ACESTEP_API_KEY 가 정의돼 있음 (또는 환경변수)
    - (선택) ACESTEP_BASE_URL 로 베이스 URL 덮어쓰기 가능
  * productions/<slug>/ 에 아래 파일이 이미 존재
    - 00_meta.json                (title / target_duration_sec 등)
    - 03_audio_meta.json          (request.prompt / duration / bpm / vocal_language / seed 등)
    - 02_step3_narration.txt      또는 lyrics.txt  (구조 태그 포함한 가사)

사용:
  python3 scripts/generate_bgm.py --production 202604220116_청춘의_청구서
  python3 scripts/generate_bgm.py --production <slug> --batch 3
  python3 scripts/generate_bgm.py --production <slug> --server http://127.0.0.1:8002  # 로컬

출력:
  productions/<slug>/03_audio.mp3              (batch=1)
  productions/<slug>/03_audio_seed{N}.mp3      (batch>1, 각 시드별)
  productions/<slug>/03_audio_meta.json        (lm_returned / measured 블록 자동 업데이트)

문서: docs/ACE_STEP_GUIDE.md
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("[err] requests 미설치. `pip install requests` 후 재시도", file=sys.stderr)
    sys.exit(1)

# .env 자동 로드 (python-dotenv 가 없어도 실패시키지 않음)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_URL = os.environ.get("ACESTEP_BASE_URL", "https://api.acemusic.ai")
DEFAULT_MODEL = os.environ.get("ACESTEP_MODEL", "acemusic/acestep-v15-turbo")
DEFAULT_TIMEOUT = 660.0  # 11분, 긴 곡 + 재시도 여유


# ──────────────────────────────────────────────────────────
# I/O helpers
# ──────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def resolve_lyrics(prod_dir: Path, meta: dict) -> str:
    """가사 원문 파일 탐색. 우선순위:
    1) 03_audio_meta.json > request.lyrics_ref 명시 경로
    2) lyrics.txt
    3) 02_step3_narration.txt
    """
    ref = meta.get("request", {}).get("lyrics_ref")
    candidates: list[Path] = []
    if ref:
        candidates.append(prod_dir / ref)
    candidates += [
        prod_dir / "lyrics.txt",
        prod_dir / "02_step3_narration.txt",
    ]
    for p in candidates:
        if p.exists() and p.is_file():
            return read_text(p)
    raise FileNotFoundError(
        f"가사 파일을 찾지 못함. {prod_dir} 에 lyrics.txt 또는 02_step3_narration.txt 필요"
    )


# ──────────────────────────────────────────────────────────
# ACE Step 호출 (v1/chat/completions, completion mode)
# 참조: ace_studio_test/ACE-Step-1.5/.claude/skills/acestep/scripts/acestep.sh:994-1028
# ──────────────────────────────────────────────────────────

def build_message_content(prompt: str, lyrics: str | None) -> str:
    """completion 모드는 messages[0].content 를 XML-like 로 감싼다.
    caption 전용: <prompt>...</prompt>
    caption + lyrics: <prompt>...</prompt><lyrics>...</lyrics>
    """
    body = f"<prompt>{prompt}</prompt>"
    if lyrics:
        body += f"<lyrics>{lyrics}</lyrics>"
    return body


def build_request(meta: dict, lyrics: str, model: str, batch: int) -> dict:
    req = meta.get("request", {}) or {}
    prompt = req.get("prompt")
    if not prompt:
        raise ValueError("03_audio_meta.json > request.prompt 가 비어있음")
    duration = req.get("duration")
    if not duration:
        raise ValueError("03_audio_meta.json > request.duration 이 비어있음")

    # audio_config (nested) — acestep.sh:1014-1028 완성형
    audio_config: dict[str, Any] = {
        "format": req.get("format", "mp3"),
        "vocal_language": req.get("vocal_language", "ko"),
        "duration": duration,
    }
    if req.get("bpm") is not None:
        audio_config["bpm"] = req["bpm"]
    if req.get("key_scale"):
        audio_config["key_scale"] = req["key_scale"]
    if req.get("time_signature"):
        audio_config["time_signature"] = req["time_signature"]

    content = build_message_content(prompt, lyrics)

    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "stream": False,
        "thinking": req.get("thinking", True),
        "use_format": req.get("use_format", True),
        "sample_mode": req.get("sample_mode", False),
        "use_cot_caption": req.get("use_cot_caption", True),
        "use_cot_language": req.get("use_cot_language", True),
        "audio_config": audio_config,
    }

    # 선택 파라미터
    if req.get("guidance_scale") is not None:
        payload["guidance_scale"] = req["guidance_scale"]
    if req.get("inference_steps") is not None:
        payload["inference_steps"] = req["inference_steps"]
    if req.get("task_type"):
        payload["task_type"] = req["task_type"]

    # batch (API 는 batch_size 필드를 씀)
    if batch and batch > 1:
        payload["batch_size"] = batch

    # seed: batch>1 이면 콤마 구분 문자열 권장
    seed = req.get("seed")
    if seed is not None:
        if batch > 1 and isinstance(seed, int):
            payload["seed"] = ",".join(str(seed + i) for i in range(batch))
        else:
            payload["seed"] = seed

    return payload


def call_ace_step(base_url: str, api_key: str | None, payload: dict, timeout: float) -> dict:
    url = base_url.rstrip("/") + "/v1/chat/completions"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "ai-content-factory/generate_bgm",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    dur = payload.get("audio_config", {}).get("duration")
    bsz = payload.get("batch_size", 1)
    t0 = time.time()
    print(f"[info] POST {url}  (duration={dur}s, batch={bsz}, model={payload.get('model')})")
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    elapsed = time.time() - t0
    if resp.status_code != 200:
        detail = ""
        try:
            j = resp.json()
            detail = j.get("detail") or (j.get("error") or {}).get("message") or ""
        except Exception:
            detail = resp.text[:500]
        print(f"[err] HTTP {resp.status_code}: {detail}", file=sys.stderr)
        resp.raise_for_status()
    data = resp.json()
    # finish_reason 체크 (completion 모드에서 error 인 경우)
    finish = (data.get("choices") or [{}])[0].get("finish_reason")
    if finish == "error":
        msg = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
        raise RuntimeError(f"generation finish_reason=error: {msg[:500]}")
    print(f"[info] 생성 완료  (elapsed={elapsed:.1f}s)")
    return data


def extract_audio(response: dict) -> list[bytes]:
    """응답에서 MP3 바이너리 배열 추출.
    batch_size=N 이면 N 개 반환.
    data URL 포맷: `data:audio/mp3;base64,<BASE64>`
    """
    audio_list = response["choices"][0]["message"].get("audio") or []
    out: list[bytes] = []
    for item in audio_list:
        url = item.get("audio_url", {}).get("url", "")
        if "," not in url:
            print("[warn] audio_url 포맷 예상과 다름:", url[:60])
            continue
        b64 = url.split(",", 1)[1]
        out.append(base64.b64decode(b64))
    return out


def parse_lm_metadata(response: dict) -> dict:
    """choices[0].message.content 에서 LM 이 확정한 메타 추출 (Markdown)."""
    content = response["choices"][0]["message"].get("content", "") or ""
    result: dict[str, Any] = {}
    patterns = {
        "bpm": r"\*\*BPM:\*\*\s*([\d.]+)",
        "key_scale": r"\*\*Key:\*\*\s*([^\n*]+)",
        "time_signature": r"\*\*Time Signature:\*\*\s*([^\n*]+)",
        "duration_sec": r"\*\*Duration:\*\*\s*([\d.]+)",
    }
    for key, pat in patterns.items():
        m = re.search(pat, content)
        if m:
            val = m.group(1).strip()
            if key in ("bpm", "duration_sec"):
                try:
                    result[key] = float(val)
                except ValueError:
                    pass
            else:
                result[key] = val
    return result


# ──────────────────────────────────────────────────────────
# 실측 (ffprobe)
# ──────────────────────────────────────────────────────────

def measure_audio(path: Path) -> dict:
    """ffprobe 로 실제 길이만 측정. BPM 실측은 수동."""
    try:
        out = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
            stderr=subprocess.STDOUT,
        )
        dur = float(out.strip())
        return {"total_duration_sec": round(dur, 2)}
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
        print(f"[warn] ffprobe 실패 ({e}). 길이 실측 스킵.")
        return {}


# ──────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="ACE Step v1.5 → productions/<slug>/03_audio.mp3 (클라우드 API 기본)"
    )
    ap.add_argument("--production", required=True, help="슬러그 (예: 202604220116_청춘의_청구서)")
    ap.add_argument(
        "--server", default=DEFAULT_BASE_URL,
        help=f"베이스 URL (기본: {DEFAULT_BASE_URL}). 로컬 서버면 http://127.0.0.1:8002",
    )
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--batch", type=int, default=1, help="시드 배치 수 (1~4 권장)")
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="요청 타임아웃 (초).")
    ap.add_argument("--dry-run", action="store_true", help="payload 만 출력하고 종료")
    args = ap.parse_args()

    # API 키 해석 (로컬 서버면 비워도 됨)
    api_key = os.environ.get("ACESTEP_API_KEY")
    is_cloud = args.server.startswith("https://") or "acemusic.ai" in args.server
    if is_cloud and not api_key and not args.dry_run:
        print(
            "[err] ACESTEP_API_KEY 가 설정되지 않음. .env 또는 환경변수에 추가.\n"
            "      발급: https://acemusic.ai/api-key",
            file=sys.stderr,
        )
        sys.exit(1)

    prod_dir = PROJECT_ROOT / "productions" / args.production
    if not prod_dir.exists():
        print(f"[err] 프로덕션 폴더 없음: {prod_dir}", file=sys.stderr)
        sys.exit(1)

    meta_path = prod_dir / "03_audio_meta.json"
    if not meta_path.exists():
        print(f"[err] {meta_path} 없음. ACE_STEP_GUIDE.md §8 스키마로 먼저 작성.", file=sys.stderr)
        sys.exit(1)

    meta = load_json(meta_path)
    lyrics = resolve_lyrics(prod_dir, meta)

    # 보호: 기존 파일이 Lyria 기록물이면 덮어쓰기 차단
    existing_source = (meta.get("source") or "").lower()
    if "lyria" in existing_source and not args.dry_run:
        print(
            f"[err] 03_audio_meta.json > source='{meta.get('source')}'. "
            f"Lyria 기록물로 보존 중. 덮어쓰지 않음.\n"
            f"     신규 ACE Step 생성은 별도 프로덕션 폴더에서 진행.",
            file=sys.stderr,
        )
        sys.exit(2)

    payload = build_request(meta, lyrics, args.model, args.batch)

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    resp = call_ace_step(args.server, api_key, payload, args.timeout)
    audios = extract_audio(resp)
    if not audios:
        print("[err] 응답에 audio 없음", file=sys.stderr)
        sys.exit(3)

    # 저장
    saved_paths: list[Path] = []
    if len(audios) == 1:
        out = prod_dir / "03_audio.mp3"
        out.write_bytes(audios[0])
        saved_paths.append(out)
    else:
        seeds_raw = payload.get("seed", "")
        seeds = str(seeds_raw).split(",") if seeds_raw else [str(i) for i in range(len(audios))]
        for i, blob in enumerate(audios):
            sid = seeds[i] if i < len(seeds) else str(i)
            out = prod_dir / f"03_audio_seed{sid}.mp3"
            out.write_bytes(blob)
            saved_paths.append(out)

    for p in saved_paths:
        print(f"[ok] {p.relative_to(PROJECT_ROOT)}  ({p.stat().st_size:,} bytes)")

    # 메타 업데이트
    meta.setdefault("source", "ACE Step v1.5 Turbo (cloud)")
    meta.setdefault("model", args.model)
    meta["endpoint"] = args.server
    meta["generated_at"] = datetime.now().isoformat(timespec="seconds")
    meta["lm_returned"] = parse_lm_metadata(resp)

    # 단일 파일일 때만 실측 기록 (배치는 수동 A/B 후 최종본 실측)
    if len(saved_paths) == 1:
        measured = measure_audio(saved_paths[0])
        if measured:
            existing_measured = meta.get("measured", {}) or {}
            existing_measured.update(measured)
            meta["measured"] = existing_measured

    dump_json(meta_path, meta)
    print(f"[ok] {meta_path.relative_to(PROJECT_ROOT)} 업데이트")

    if len(saved_paths) > 1:
        print("\n[next] 시드별 청취 → 최종본 선택 → 03_audio.mp3 로 복사:")
        print(f"       cp {saved_paths[0].name}  03_audio.mp3")
        print("       그 후 ffprobe 실측값을 03_audio_meta.json > measured 에 수동 입력")


if __name__ == "__main__":
    main()
