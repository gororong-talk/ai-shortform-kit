#!/usr/bin/env python3
"""
wisdom_publish_guard.py — 명언 채널(@your_wisdom_channel) 게시 표준 검증.

★ 표준 (불변): **영상 1편 = 명언 1개 · ≤15초.** (코드 MAX_VIDEO_SEC=15, 게시 8건 전부 단건)
★ 재발방지 (2026-06-25): 주제 컴필레이션(9편·1:30)을 잘못 만들어 게시 단계까지 갔다.
  채널 표준은 단건 ≤15s인데 그걸 위반. → 생성 후·게시 전 게이트에서 '단건 ≤15s'를
  자동 검증해 비표준 영상을 차단(prep_upload·휴대폰 전송 스크립트 둘 다 이 모듈을 호출).

검사 대상 = 명언 채널 영상만 (사연/키즈는 길이 제한 없음 → 통과).
판정 신호:
  · 단건 여부 = _pubmeta 에 다중 'theme' 블록(count>1 / quote_ids>1) 또는 slug 'theme_*' → 위반
  · 길이     = ffprobe duration > 15s(+여운 오차) → 위반
"""
import json
import os
import subprocess

MAX_SEC = 15.0
TOL = 0.6  # render_video 여운/인코딩 오차 허용 (10~13.4s 정상, theme/compile 은 60s+ 라 충분히 구분)
WISDOM_HANDLE = "@your_wisdom_channel"


def video_duration(path):
    """ffprobe 로 영상 길이(초). 실패 시 None."""
    if not path or not os.path.exists(path):
        return None
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, text=True)
        return float(r.stdout.strip())
    except Exception:
        return None


def is_wisdom(meta, folder=""):
    """명언 채널(@your_wisdom_channel) 게시물인가 — channel_handle 우선, 폴더 경로(wisdom_out) 보조."""
    if (meta or {}).get("channel_handle") == WISDOM_HANDLE:
        return True
    return (os.sep + "wisdom_out" + os.sep) in (folder.rstrip(os.sep) + os.sep)


def _is_multi(meta, folder):
    slug = str((meta or {}).get("slug") or os.path.basename(folder.rstrip(os.sep)))
    th = (meta or {}).get("theme")
    if slug.startswith("theme_"):
        return True, None
    if isinstance(th, dict):
        n = th.get("count")
        if (n or 0) > 1 or len(th.get("quote_ids") or []) > 1:
            return True, (n if n is not None else len(th.get("quote_ids") or []))
    return False, None


def check(folder, meta=None):
    """(ok: bool, problems: list[str]). 명언 채널 영상만 검사하고 그 외/판정불가는 ok."""
    if meta is None:
        mp = os.path.join(folder, "_pubmeta.json")
        if not os.path.isfile(mp):
            return True, []
        try:
            meta = json.load(open(mp, encoding="utf-8"))
        except Exception:
            return True, []
    if not is_wisdom(meta, folder):
        return True, []
    problems = []
    multi, n = _is_multi(meta, folder)
    if multi:
        problems.append(f"단건 위반: 주제 컴필레이션({n if n else '다중'}편). "
                        f"명언 채널 = 영상 1편에 명언 1개.")
    v = os.path.join(folder, (meta or {}).get("video", "video.mp4"))
    dur = video_duration(v)
    if dur is not None and dur > MAX_SEC + TOL:
        problems.append(f"길이 위반: {dur:.1f}초 > {MAX_SEC:.0f}초. 명언 채널 = ≤15초.")
    return (len(problems) == 0), problems


def report(folder, meta=None):
    """게이트용 출력 헬퍼 — 위반 시 박스 경고 출력하고 problems 반환(없으면 [])."""
    ok, problems = check(folder, meta)
    if not ok:
        print("\n" + "=" * 64)
        print("⛔ 명언 채널 게시 표준 위반 — 단건 ≤15초 아님!")
        for p in problems:
            print(f"     · {p}")
        print("   → 단건 렌더로 다시: wisdom_render.py --id <quote_id> (또는 --fresh 1).")
        print("     주제 컴필레이션은 이 채널 게시 대상 아님.")
        print("=" * 64 + "\n")
    return problems


if __name__ == "__main__":
    import sys
    folders = sys.argv[1:] or ["."]
    bad = 0
    for f in folders:
        ok, problems = check(f)
        tag = "✅ OK" if ok else "⛔ 위반"
        print(f"{tag}  {f}")
        for p in problems:
            print(f"     · {p}")
        bad += 0 if ok else 1
    sys.exit(1 if bad else 0)
