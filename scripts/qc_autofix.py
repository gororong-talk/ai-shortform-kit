#!/usr/bin/env python3
"""
qc_autofix.py — 자율 이미지 QC 루프(검출→분류→자동수정→재검증)를 하나로 묶는 래퍼.

왜? 기존 루프는 verify_images 가 결함을 잡아도 자동 대응이 '재생성' 하나뿐이었다.
가짜글자는 재생성해도 또 박히는 헛바퀴가 잦고, 잘 나온 구도까지 버린다.
→ 결함을 종류별로 라우팅한다:
   - 글자/간판만 문제(gibberish_text)  → scrub_text --inpaint(표면교체)로 글자만 제거(구도 보존)
   - 얼굴/손/정체성 등               → generate_images_fal 재생성(기존)
   - 글자인데 1회 스크럽 후에도 남으면 → 재생성으로 에스컬레이션(무한 스크럽 방지)
verify_images 의 판정 함수를 그대로 재사용한다(중복 로직 없음).

정직한 한계: 무인이라 ₩0 blur/clone 은 안 씀(vision 박스 좌표 부정확). 텍스트 자동수정은
인페인트(표면교체)+넉넉한 마스크 경로만 사용. 그래도 예방(no-text 컷에 평면 안 주기)이 1순위.

usage:
  .venv/bin/python scripts/qc_autofix.py --production <slug>            # 깨끗할 때까지 자동(최대 3회)
  .venv/bin/python scripts/qc_autofix.py --production <slug> --dry-run  # 판정·라우팅만 출력(수정 안 함)
  .venv/bin/python scripts/qc_autofix.py --production <slug> --only 6,13 # 특정 비트만
exit 0 = 전부 통과 / exit 1 = 한도 내 못 고친 결함 남음
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import verify_images as V  # is_black, vision_judge, parse_sheet_roles 재사용

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

PY = sys.executable
TEXT_ISSUES = {"gibberish_text"}  # 이 집합에만 속하면 '텍스트만' → 인페인트로 살림
DEFAULT_MODEL = "claude-sonnet-4-6"


def judge_beat(client, model, path, ref_map, scene):
    if V.is_black(path):
        return "high", ["black_frame"]
    v = V.vision_judge(client, model, path, ref_map, scene)
    return v.get("severity", "none"), list(v.get("issues") or [])


def run(cmd):
    print("   $ " + " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, cwd=str(ROOT)).returncode


def scrub_inpaint(slug, beats, pad, model):
    return run([PY, "scripts/scrub_text.py", "--production", slug, "--inpaint",
                "--inpaint-pad", str(pad), "--model", model, "--only", ",".join(map(str, beats))])


def regenerate(slug, beats, ref_roles, fdir, bdir, it):
    # generate_images_fal 은 기존 파일을 건너뛰므로 백업 후 삭제하고 재생성
    bdir.mkdir(exist_ok=True)
    for b in beats:
        p = fdir / f"B{b:02d}.png"
        if p.exists():
            shutil.copy(p, bdir / f"B{b:02d}_regen{it}.png")
            p.unlink()
    cmd = [PY, "scripts/generate_images_fal.py", "--production", slug, "--flux2"]
    for role in ref_roles:
        cmd += ["--ref", f"{role}=flow_images/_ref_{role}.png"]
    cmd += ["--only", ",".join(map(str, beats))]
    return run(cmd)


def main():
    ap = argparse.ArgumentParser(description="자율 QC 루프(검출→분류→인페인트/재생성→재검증)")
    ap.add_argument("--production", required=True)
    ap.add_argument("--max-iter", type=int, default=3)
    ap.add_argument("--inpaint-pad", type=float, default=0.05)
    ap.add_argument("--only", help="대상 비트 제한 (예 6,13)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dry-run", action="store_true", help="판정·라우팅만, 수정 안 함")
    a = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("[err] ANTHROPIC_API_KEY 없음(비전 QC 필요)")
    import anthropic
    client = anthropic.Anthropic()

    prod = ROOT / "productions" / a.production
    fdir = prod / "flow_images"
    bdir = fdir / "_v1_backup"
    ref_files = {Path(p).stem.replace("_ref_", ""): Path(p) for p in glob.glob(str(fdir / "_ref_*.png"))}
    beats_roles, scenes = V.parse_sheet_roles(prod, list(ref_files))
    only = set(int(x) for x in a.only.split(",")) if a.only else None

    def verify_pass():
        flagged = []
        for img in sorted(glob.glob(str(fdir / "B*.png"))):
            beat = int(re.search(r"B(\d+)", Path(img).name).group(1))
            if only and beat not in only:
                continue
            roles = [r for r in beats_roles.get(beat, []) if r in ref_files]
            ref_map = {r: ref_files[r] for r in roles}
            sev, issues = judge_beat(client, a.model, img, ref_map, scenes.get(beat, ""))
            mark = {"high": "❌", "low": "⚠️", "none": "ok"}.get(sev, "ok")
            print(f"   {mark} B{beat:02d}  {','.join(issues) or '-'}")
            if sev == "high":
                flagged.append((beat, issues))
        return flagged

    scrub_done = {}  # beat -> 스크럽 시도 횟수
    print(f"🔁 qc_autofix: {a.production} (max-iter {a.max_iter}, refs={list(ref_files) or '없음'})"
          + (" [DRY-RUN]" if a.dry_run else ""))

    for it in range(1, a.max_iter + 1):
        print(f"\n── 검증 {it}회차 ──")
        flagged = verify_pass()
        if not flagged:
            print("\n✅ 전부 통과 (high 0)")
            sys.exit(0)

        text_beats, regen_beats = [], []
        for beat, issues in flagged:
            text_only = bool(issues) and set(issues) <= TEXT_ISSUES
            if text_only and scrub_done.get(beat, 0) < 1:
                text_beats.append(beat)
            else:
                regen_beats.append(beat)  # 비텍스트 or 이미 스크럽한 텍스트 → 재생성 에스컬레이션
        print(f"\n   라우팅 → 인페인트(텍스트): {text_beats or '-'} | 재생성: {regen_beats or '-'}")

        if a.dry_run:
            print("\n[dry-run] 수정 안 함. 라우팅만 표시하고 종료.")
            sys.exit(1 if flagged else 0)

        if text_beats:
            print("\n🩹 텍스트 인페인트:")
            scrub_inpaint(a.production, text_beats, a.inpaint_pad, a.model)
            for b in text_beats:
                scrub_done[b] = scrub_done.get(b, 0) + 1
        if regen_beats:
            print("\n♻️  재생성:")
            regenerate(a.production, regen_beats, list(ref_files), fdir, bdir, it)

    print(f"\n── 최종 검증 ──")
    flagged = verify_pass()
    if not flagged:
        print("\n✅ 전부 통과")
        sys.exit(0)
    print(f"\n⚠️ {a.max_iter}회 내 못 고친 결함 {len(flagged)}건: " +
          ", ".join(f"B{b:02d}({','.join(i)})" for b, i in flagged) + " → 수동 확인 권장")
    sys.exit(1)


if __name__ == "__main__":
    main()
