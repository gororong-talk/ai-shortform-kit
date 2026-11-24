#!/usr/bin/env python3
"""
prep_upload.py <slug> [--no-open]

업로드 준비 완료 시 사용자의 수동작업을 최소화한다(2026-06-20 사용자 지침: "파일을 찾아다니지
않게 Finder 띄워주고, 캡션 클립보드 복사 명령을 영상 폴더에 같이 둬라").

하는 일:
  1) 영상 폴더의 _pubmeta.json 을 읽어 플랫폼별 '캡션 복사' 더블클릭 파일을 폴더에 떨군다.
     - macOS .command (더블클릭 = Terminal 실행 = pbcopy 로 클립보드 복사). 캡션은 파일 안에 내장.
     - 파일명(한글): 유튜브_제목_복사.command / 유튜브_설명_복사.command / 틱톡_캡션_복사.command / 인스타_캡션_복사.command
  2) Finder 로 영상 폴더를 열고 영상 파일을 선택(reveal)한다 → 바로 드래그 가능.
     (--no-open 또는 비대화/cron 환경에서는 Finder 를 열지 않는다.)

지원: productions/<slug>/  또는 wisdom_out/<slug>/  (둘 다 _pubmeta.json + video 필드 사용)

★ production 파이프라인의 '업로드 준비 완료'(_pubmeta 생성 직후) 표준 마지막 단계로 항상 실행.
"""
import argparse
import json
import os
import stat
import subprocess
import sys

import wisdom_publish_guard  # 명언 채널 단건 ≤15s 게이트 (2026-06-25 재발방지)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EOF = "__PREP_UPLOAD_EOF__"  # 캡션엔 절대 안 나오는 heredoc 구분자

# 플랫폼 → [(파일명, 캡션을 뽑는 함수)]
def platform_files(plat, data):
    """data = pubmeta['platforms'][plat] dict. returns list of (filename, label, text)."""
    if not isinstance(data, dict) or "na" in data:
        return []
    out = []
    if plat == "youtube":
        if data.get("title"):
            out.append(("유튜브_제목_복사.command", "유튜브 제목", data["title"]))
        if data.get("description"):
            out.append(("유튜브_설명_복사.command", "유튜브 설명", data["description"]))
    else:
        if data.get("caption"):
            ko = {"tiktok": "틱톡_캡션_복사.command", "instagram": "인스타_캡션_복사.command"}.get(
                plat, f"{plat}_캡션_복사.command")
            label = {"tiktok": "틱톡 캡션", "instagram": "인스타 캡션"}.get(plat, f"{plat} 캡션")
            out.append((ko, label, data["caption"]))
    return out


def write_command(path, label, text):
    # 복사 후 터미널 창 자동 닫기: 셸이 끝난 뒤(0.6s) 분리된 프로세스가 front window 를 닫는다.
    # 셸 종료 후에 닫아야 macOS "프로세스 실행 중" 확인창이 안 뜬다(detach=nohup → 셸 SIGHUP 무시).
    autoclose = (
        r'''nohup bash -c 'sleep 0.6; osascript -e "tell application \"Terminal\" '''
        r'''to close front window"' >/dev/null 2>&1 &'''
    )
    script = (
        "#!/bin/bash\n"
        f"cat <<'{EOF}' | pbcopy\n"
        f"{text}\n"
        f"{EOF}\n"
        f'echo "✅ {label}이 클립보드에 복사됐습니다. 업로드 칸에 Cmd+V 로 붙여넣으세요."\n'
        f"{autoclose}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(script)
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def check_render_freshness(folder, video_path):
    """렌더가 소스 에셋(이미지/오디오/타이밍)보다 오래되면 경고하고 stale 목록을 돌려준다(호출자가 차단).
    ★ 2026-06-23 재발방지: cafe_farewell 에서 가짜글자 수정 이미지가 렌더 뒤에 갱신됐는데
    재렌더를 안 해 stale 영상(수정 미반영)이 업로드 직전까지 갔다. 업로드 마지막 관문에서
    'render < source 에셋' 을 검출해 게시 전에 잡는다."""
    if not os.path.exists(video_path):
        return []
    vmtime = os.path.getmtime(video_path)
    sources = []
    img_dir = os.path.join(folder, "flow_images")
    if os.path.isdir(img_dir):
        for f in os.listdir(img_dir):
            if f.startswith("_") or f.startswith("."):
                continue  # _ref_*, _v1_backup 등 비-소스 제외
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".mp4")):
                sources.append(os.path.join(img_dir, f))
    for f in ("03_audio_narration_only.mp3", "04_timing.json"):
        p = os.path.join(folder, f)
        if os.path.exists(p):
            sources.append(p)
    stale = [s for s in sources if os.path.getmtime(s) > vmtime + 1]  # 1s 여유
    if stale:
        print("\n" + "=" * 64)
        print("⚠️  STALE 렌더 경고 — 영상이 소스 에셋보다 오래됨!")
        print(f"   영상 {os.path.basename(video_path)} 수정시각보다 '늦게' 바뀐 소스:")
        for s in sorted(stale, key=os.path.getmtime, reverse=True)[:12]:
            rel = os.path.relpath(s, folder)
            print(f"     · {rel}")
        print("   → 이 수정들이 영상에 반영 안 됐을 수 있음. 재렌더 후 다시 prep 하세요:")
        print("     PATH=/opt/homebrew/bin:$PATH .venv/bin/python "
              "scripts/compose_narration.py <slug> --kenburns")
        print("=" * 64 + "\n")
    return stale


def check_publish_warnings(meta):
    """게시 전 정책 게이트 — 해시태그 초과(>8)·broad 필러(#fyp 등)·본문 추출 실패 등을
    업로드 직전 마지막 관문에서 표면화한다(2026-06-24 #5: lint 함수는 있었으나 게시 게이트에
    미연결 → FC-029처럼 17/39 정책 드리프트가 났다). 해시태그는 손편집 대비 '라이브 재계산'.
    """
    warns = list(meta.get("_warnings") or [])
    try:                                   # parse 시점 _warnings는 캡션 손편집 시 stale → 라이브 재계산 병합
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        from parse_upload_meta import hashtag_warnings
        for w in hashtag_warnings(meta):
            if w not in warns:
                warns.append(w)
    except Exception:
        pass
    # 잡음 제거: 영상 없음/본문 실패 같은 치명 경고는 위에 별도 표시되므로 정책류만 강조
    if not warns:
        return
    print("\n" + "=" * 64)
    print("⚠️  게시 전 점검 — 정책/메타 경고:")
    for w in warns:
        print(f"     · {w}")
    if any(("해시태그" in w or "필러" in w) for w in warns):
        print("   → 해시태그 ≤8·니치 우선, broad 필러(#fyp #추천 등) 제거 후 게시 권장"
              " (정책 = CHANNEL_GROWTH_PLAYBOOK §해시태그).")
    print("=" * 64)


def resolve(slug):
    for base in ("productions", "wisdom_out"):
        d = os.path.join(ROOT, base, slug)
        if os.path.isfile(os.path.join(d, "_pubmeta.json")):
            return d
    sys.exit(f"❌ _pubmeta.json 을 찾을 수 없음: productions/{slug}/ 또는 wisdom_out/{slug}/")


def main():
    ap = argparse.ArgumentParser(description="업로드 준비: Finder 열기 + 캡션 복사 명령 드롭")
    ap.add_argument("slug")
    ap.add_argument("--no-open", action="store_true", help="Finder 를 열지 않음(cron/비대화)")
    ap.add_argument("--force", action="store_true", help="게시 표준 게이트(단건 ≤15s) 위반도 강행")
    a = ap.parse_args()

    folder = resolve(a.slug)
    meta = json.load(open(os.path.join(folder, "_pubmeta.json"), encoding="utf-8"))
    video = meta.get("video", "06_render_v1.mp4")
    video_path = os.path.join(folder, video)

    # ★ 게시 표준 게이트 — 명언 채널 영상은 단건 ≤15초여야(컴필레이션·15s초과 차단).
    #   생성 후 게시 직전 마지막 관문. --force 로만 우회.
    gate = wisdom_publish_guard.report(folder, meta)
    if gate and not a.force:
        sys.exit("⛔ 게시 표준 위반으로 prep 중단. 단건 ≤15s 로 다시 만들거나 --force 로 강행.")

    made = []
    for plat, data in meta.get("platforms", {}).items():
        for fname, label, text in platform_files(plat, data):
            p = os.path.join(folder, fname)
            write_command(p, label, text)
            made.append(fname)

    # ★ 2026-08-08: 고정댓글도 .command 로 낸다.
    #   `_pubmeta.pinned_comment`(전환장치 3종 중 하나, 정보형 사연은 여기에 확장 정보가 들어간다)가
    #   여태 어디로도 전달되지 않아, 게시는 자동인데 고정댓글만 매번 손으로 파일을 열어 긁고 있었다.
    #   게시 프로그램 는 고정댓글을 달지 않으므로(플랫폼 UI 미지원) 이 경로가 유일한 전달 수단이다.
    pinned = (meta.get("pinned_comment") or "").strip()
    if pinned:
        p = os.path.join(folder, "고정댓글_복사.command")
        write_command(p, "고정댓글", pinned)
        made.append("고정댓글_복사.command")

    print(f"📁 {folder}")
    print(f"🎬 영상: {video}  ({'있음' if os.path.exists(video_path) else '⚠️ 없음'})")
    # 2026-11-17: 경고만 하던 것을 차단으로 — 경고는 스크롤에 묻혀 옛 영상이 게시 직전까지 갔다
    if check_render_freshness(folder, video_path) and not a.force:
        sys.exit("⛔ stale 렌더 — 재렌더 후 다시 prep 하세요 (--force 로만 강행)")
    check_publish_warnings(meta)
    if made:
        print("📋 캡션 복사 파일(더블클릭 = 클립보드 복사):")
        for m in made:
            print(f"   · {m}")
    else:
        print("⚠️ 캡션 플랫폼 없음(전부 na?)")

    if not a.no_open:
        target = video_path if os.path.exists(video_path) else folder
        # -R: 파일을 Finder 에서 선택(reveal)해서 연다 → 바로 드래그
        subprocess.run(["open", "-R", target] if os.path.exists(video_path) else ["open", folder])
        print("🪟 Finder 열림 — 영상이 선택된 상태입니다. 업로드 칸으로 드래그하세요.")
    else:
        print("(--no-open: Finder 안 열음)")


if __name__ == "__main__":
    main()
