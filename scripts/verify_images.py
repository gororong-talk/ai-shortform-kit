#!/usr/bin/env python3
"""
verify_images.py — 자율생성 이미지 자체검증 QC (사람 없이 불량컷 검출 → 재생성 트리거).

왜? 자율진행은 사람이 매 컷을 못 본다. FLUX 는 레퍼런스 잠금을 써도 확률적으로 가끔 실패한다
(얼굴 드리프트·기괴한 손·가짜 글자·정체성 병합). 이 셋을 자동으로 잡아야 자율생성이 안전.

3중 레이어 (싼 것부터):
  ① black-frame   — ffmpeg, 무료. fal 가 가끔 검은 PNG 반환(이미 check_black_frames 와 동일 로직).
  ② OCR(tesseract) — 무료. 'no text' 인데 글자/워터마크가 박혔는지(가짜 한자·서명) 1차 신호.
  ③ 비전 LLM 판정  — Anthropic vision. 레퍼런스 대비 얼굴 일관·손/손가락 기형·정체성 병합·해부학.
                     ①②가 못 잡는 '주관적' 불량을 잡는다(자율생성의 핵심 안전망).

usage:
  # production 전체(레퍼런스 _ref_<role>.png 자동 인식, 비트별 역할 자동 매칭):
  .venv/bin/python scripts/verify_images.py --production <slug>
  # 단일 이미지 테스트(레퍼런스 지정):
  .venv/bin/python scripts/verify_images.py --image path.png --ref grandpa=_ref_grandpa.png --ref grandma=_ref_grandma.png --scene "노부부 나란히"
  # OCR/비전 끄기:
  .venv/bin/python scripts/verify_images.py --production <slug> --no-vision   # ①②만(무료)
exit 0 = 전부 통과 / exit 1 = high-severity 불량 있음(→ 재생성 권장 비트 출력)
"""
import argparse
import base64
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"
DEFAULT_MODEL = "claude-sonnet-4-6"

RUBRIC = (
    "You are a strict QC reviewer for AI-generated Korean WEBTOON story stills (flat 2D cel-shaded). "
    "You are given the REFERENCE portrait(s) of the recurring character(s) and the IMAGE to check. "
    "Judge ONLY clear defects, not artistic taste. Return STRICT JSON only, no prose:\n"
    '{"ok": true|false, "severity": "none"|"low"|"high", '
    '"issues": [any of: "face_mismatch","malformed_hands","malformed_fingers","floating_object",'
    '"gibberish_text","extra_limbs","extra_people","wrong_outfit_color","identity_bleed","distorted_anatomy"], '
    '"note": "<=15 words"}\n'
    "ALWAYS inspect hands and objects even if no face is visible (a hands/object-only close-up still counts). "
    "A character's RECURRING FEATURES must match its reference: hair (length/shape/parting/volume), glasses "
    "(present/absent AND frame STYLE — rectangular vs round vs rimless, frame color/thickness), outfit color, face. "
    "severity=HIGH if any recurring feature CLEARLY differs from the reference (glasses style changed, hairstyle "
    "changed, outfit color wrong, glasses added/removed), OR malformed hands/fingers (extra/fused/wrong-count/"
    "distorted), OR a ring/object that FLOATS / is unattached, OR ANY text/watermark/signage — whether in the "
    "BACKGROUND (signs, building facades, banners, menu boards, walls) OR in the FOREGROUND on a character/prop "
    "(name tags, badges, apron/clothing labels, embroidered logos, text on cups/packaging/products) — INCLUDING "
    "garbled/fake pseudo-letters or gibberish glyphs that are NOT cleanly readable (these are no-text images, so "
    "BOTH readable text AND fake/garbled glyphs are HIGH; scan BOTH background AND foreground, including labels on "
    "clothing/aprons/name tags even when small), "
    "OR two characters swapped/merged. severity=none ONLY for differences in pose, expression, gaze, camera angle, "
    "or lighting — NOT for recurring features. Be strict on recurring-feature consistency: that is the whole point."
)


def is_black(path):
    out = subprocess.run([FFMPEG, "-v", "info", "-i", str(path),
                          "-vf", "blackframe=amount=95:threshold=32", "-f", "null", "-"],
                         capture_output=True, text=True)
    return "blackframe" in out.stderr.lower()


def ocr_text(path):
    """tesseract 로 추출한 영숫자/한글 텍스트(3자 이상 토큰만). 없으면 ''."""
    try:
        out = subprocess.run(["tesseract", str(path), "-", "--psm", "11", "-l", "eng+kor"],
                             capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return ""
    toks = re.findall(r"[A-Za-z가-힣0-9]{3,}", out)
    # 흔한 OCR 환각 1~2자/기호는 버리고, 3자+ 토큰이 2개 이상이면 '글자 있음' 신호
    return " ".join(toks) if len(toks) >= 2 else ""


def b64(path):
    return base64.standard_b64encode(Path(path).read_bytes()).decode()


def vision_judge(client, model, image_path, ref_map, scene):
    """ref_map = {role: path}. 비전으로 레퍼런스 대비 결함 판정 → dict."""
    content = []
    for role, rp in ref_map.items():
        content.append({"type": "text", "text": f"REFERENCE — character '{role}' must look like this:"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64(rp)}})
    content.append({"type": "text", "text": f"IMAGE to QC (intended scene: {scene or 'n/a'}):"})
    content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64(image_path)}})
    content.append({"type": "text", "text": RUBRIC})
    msg = client.messages.create(model=model, max_tokens=300, temperature=0,
                                 messages=[{"role": "user", "content": content}])
    txt = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    # 파싱 실패는 무음 통과하지 않는다 → low 로 표면화(사람/재시도 유도)
    return {"severity": "low", "issues": ["unparsed"], "note": "판정불가-확인요(" + txt[:40] + ")"}


def parse_sheet_roles(prod, role_names):
    """08 의 각 비트 프롬프트에서 등장 역할 추출 → {beat: [roles]}, {beat: scene요약}."""
    md = prod / "08_image_prompts.md"
    beats, scenes = {}, {}
    if not md.exists():
        return beats, scenes
    text = md.read_text(encoding="utf-8")
    for m in re.finditer(r"^##\s+B(\d+)\b([^\n]*)\n(.*?)(?=^##\s+B\d+\b|^---\s*$|\Z)", text, re.M | re.S):
        b = int(m.group(1)); label = m.group(2).strip(" —-"); body = m.group(3).lower()
        beats[b] = [r for r in role_names if re.search(r"\b" + re.escape(r.lower()) + r"\b", body)]
        scenes[b] = label[:60]
    return beats, scenes


def report(rows):
    bad = [r for r in rows if r["sev"] == "high"]
    for r in rows:
        icon = {"high": "❌", "low": "⚠️", "none": "ok"}.get(r["sev"], "ok")
        extra = f" [{','.join(r['issues'])}]" if r["issues"] else ""
        print(f"  {icon:3} {r['name']:14}{extra}  {r['note']}")
    if bad:
        beats = ",".join(str(r["beat"]) for r in bad if r.get("beat"))
        print(f"\n❌ high-severity {len(bad)}건 → 재생성 권장" + (f": --only {beats}" if beats else ""))
        return 1
    print(f"\n✅ {len(rows)}컷 통과 (high-severity 0)")
    return 0


def main():
    ap = argparse.ArgumentParser(description="자율생성 이미지 자체검증 QC (black/OCR/비전)")
    ap.add_argument("--production")
    ap.add_argument("--image", help="단일 이미지 테스트")
    ap.add_argument("--ref", action="append", metavar="ROLE=PATH", help="단일 모드 레퍼런스")
    ap.add_argument("--scene", help="단일 모드 장면 설명")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--no-vision", action="store_true", help="비전 끄고 ①②(무료)만")
    a = ap.parse_args()

    client = None
    if not a.no_vision:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("[warn] ANTHROPIC_API_KEY 없음 → --no-vision 으로 진행"); a.no_vision = True
        else:
            import anthropic
            client = anthropic.Anthropic()

    rows = []

    def check_one(path, ref_map, scene, beat=None, name=None):
        name = name or Path(path).name
        if is_black(path):
            return {"name": name, "beat": beat, "sev": "high", "issues": ["black_frame"], "note": "검은 이미지"}
        if client:
            v = vision_judge(client, a.model, path, ref_map, scene)
            return {"name": name, "beat": beat, "sev": v.get("severity", "none"),
                    "issues": list(v.get("issues") or []), "note": v.get("note", "")}
        # 비전 끔(--no-vision): OCR 만으로 텍스트누출 1차 점검(만화 텍스처 환각 있어 보조용).
        ocr = ocr_text(path)
        if ocr:
            return {"name": name, "beat": beat, "sev": "low", "issues": ["ocr_text?"], "note": f"OCR:'{ocr[:24]}'"}
        return {"name": name, "beat": beat, "sev": "none", "issues": [], "note": "(비전 off — 텍스트만 점검)"}

    if a.image:
        ref_map = {}
        for spec in a.ref or []:
            role, _, p = spec.partition("=")
            rp = Path(p)
            if not rp.is_absolute() and not rp.exists():
                rp = ROOT / p
            ref_map[role] = rp
        print(f"🔎 단일: {a.image}  (refs={list(ref_map)}, vision={'on' if client else 'off'})")
        rows.append(check_one(a.image, ref_map, a.scene))
        sys.exit(report(rows))

    if not a.production:
        sys.exit("usage: --production <slug> 또는 --image <path>")
    prod = ROOT / "productions" / a.production
    fdir = prod / "flow_images"
    ref_files = {Path(p).stem.replace("_ref_", ""): Path(p)
                 for p in glob.glob(str(fdir / "_ref_*.png"))}
    beats_roles, scenes = parse_sheet_roles(prod, list(ref_files))
    imgs = sorted(glob.glob(str(fdir / "B*.png")))
    print(f"🔎 {a.production}: {len(imgs)}컷 · 레퍼런스={list(ref_files) or '없음(텍스트 사연)'} · "
          f"vision={'on(' + a.model + ')' if client else 'off'}")
    for img in imgs:
        beat = int(re.search(r"B(\d+)", Path(img).name).group(1))
        roles = beats_roles.get(beat, [])
        ref_map = {r: ref_files[r] for r in roles if r in ref_files}
        rows.append(check_one(img, ref_map, scenes.get(beat, ""), beat=beat))
    sys.exit(report(rows))


if __name__ == "__main__":
    main()
