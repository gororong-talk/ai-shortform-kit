#!/usr/bin/env python3
"""
scrub_text.py — FLUX 가 박은 가짜글자/간판/워터마크를 ₩0·재생성 없이 국소 제거.

왜? FLUX 는 'no text' 를 무시하고 간판·외벽·창문 같은 평면에 깨진 가짜글자를 자주 박는다.
재생성은 확률적이고(돈+시간) 잘 나온 구도를 깨뜨릴 위험이 있다. 글자 영역만 검출해
주변 깨끗한 텍스처로 덮거나(clone) 뭉개면(blur) 구도를 보존하면서 글자만 지운다.

방법:
  ① vision LLM 으로 글자 bbox 검출(깨진 가짜글자 포함, 정규화 0..1).  (--detect vision, 기본)
  ② 각 bbox 를 scrub:
     - clone : box 바로 위/아래의 더 깨끗한(저분산) 띠를 복사해 덮음 → 평면(하늘/벽) 배경에 최적.
     - blur  : box 를 강하게 가우시안 블러 → 복잡/보케 배경에 최적(평면엔 띠가 약간 보일 수 있음).
     - auto  : 이웃 띠 분산을 보고 clone(깨끗) / blur(복잡) 자동 선택.  (기본)
  ③ (옵션) verify_images 로 재검증해 글자 사라졌는지 확인.

한계(정직): 글자가 인물·전경의 초점 평면에 박혔거나 배경이 선명·복잡하면 자국이 남을 수 있다.
그 경우는 fal 인페인트(plan B) 또는 프롬프트 예방(평면 제거)으로. 이 도구는 '가장자리/배경 평면' 케이스 최적.

usage:
  # production 전체 자동(글자 있는 컷만 검출→스크럽→백업→덮어쓰기→재검증):
  .venv/bin/python scripts/scrub_text.py --production <slug> --reverify
  # 특정 비트만:
  .venv/bin/python scripts/scrub_text.py --production <slug> --only 6,13
  # 단일 이미지 테스트(원본 보존, 결과 따로 저장):
  .venv/bin/python scripts/scrub_text.py --image in.png --out out.png --method clone
  # vision 못 잡을 때 수동 박스(정규화 x0,y0,x1,y1, 반복가능):
  .venv/bin/python scripts/scrub_text.py --image in.png --out out.png --box 0.1,0.13,0.9,0.27
"""
import argparse
import base64
import glob
import json
import os
import re
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

DEFAULT_MODEL = "claude-sonnet-4-6"

DETECT_PROMPT = (
    "This is an AI-generated Korean WEBTOON still that is supposed to contain NO text at all. "
    "Find EVERY region that contains letters/text/signage/watermark/menu board/banner/ribbon text — "
    "CRUCIALLY including garbled or fake pseudo-letters and gibberish glyphs that are NOT cleanly readable "
    "(FLUX often bakes fake letters onto signs, building facades, windows and walls). Scan the BACKGROUND, not just the subject. "
    "Return STRICT JSON only, no prose: {\"boxes\":[{\"x0\":0-1,\"y0\":0-1,\"x1\":0-1,\"y1\":0-1,\"what\":\"short\"}]}. "
    "Coordinates normalized 0..1 (x from left edge, y from top edge). Make each box TIGHT around the text plus a small margin. "
    "If there is genuinely no text anywhere, return {\"boxes\":[]}."
)


def b64(path):
    return base64.standard_b64encode(Path(path).read_bytes()).decode()


def detect_boxes(client, model, path):
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64(path)}},
        {"type": "text", "text": DETECT_PROMPT},
    ]
    msg = client.messages.create(model=model, max_tokens=400, temperature=0,
                                 messages=[{"role": "user", "content": content}])
    txt = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    m = re.search(r"\{.*\}", txt, re.DOTALL)
    if not m:
        return []
    try:
        return json.loads(m.group(0)).get("boxes", []) or []
    except Exception:
        return []


def _region_stddev(im, box):
    box = _clamp(im, box)
    if box[2] - box[0] < 2 or box[3] - box[1] < 2:
        return 999.0
    st = ImageStat.Stat(im.crop(box))
    return sum(st.stddev) / len(st.stddev)


def _clamp(im, box):
    W, H = im.size
    x0, y0, x1, y1 = box
    return (max(0, min(int(x0), W)), max(0, min(int(y0), H)),
            max(0, min(int(x1), W)), max(0, min(int(y1), H)))


def _feather_mask(w, h, frac=0.14):
    inset = max(3, int(min(w, h) * frac))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rectangle((inset, inset, w - inset, h - inset), fill=255)
    return mask.filter(ImageFilter.GaussianBlur(inset))


def scrub_blur(im, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    radius = max(10, int(min(w, h) * 0.55))
    reg = im.crop(box).filter(ImageFilter.GaussianBlur(radius))
    im.paste(reg, (x0, y0), _feather_mask(w, h))
    return "blur"


def scrub_clone(im, box):
    """box 바로 위/아래 중 더 깨끗한(저분산) 동일크기 띠를 복사해 덮음. 불가하면 blur 폴백."""
    W, H = im.size
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    gap = max(2, int(0.008 * H))
    cands = []
    for src in [(x0, y0 - h - gap, x1, y0 - gap), (x0, y1 + gap, x1, y1 + h + gap)]:
        if src[1] >= 0 and src[3] <= H and src[0] >= 0 and src[2] <= W and src[3] > src[1]:
            cands.append((_region_stddev(im, src), src))
    if not cands:
        return scrub_blur(im, box)
    cands.sort(key=lambda c: c[0])
    src = im.crop(cands[0][1]).resize((w, h))
    im.paste(src, (x0, y0), _feather_mask(w, h))
    return f"clone(std={cands[0][0]:.0f})"


INPAINT_MODEL = "fal-ai/flux-pro/v1/fill"
# ★핵심(실증 2026-06-23): "배경을 그대로 이어 채워라"는 실패한다 — FLUX Fill 도 건물/간판 평면을
# 보면 가짜 글자를 '다시' 그린다(negative 무시). 반드시 텍스트 안 생기는 '다른 표면'으로 REPLACE 하라
# (보케/하늘/흐린 잎/단색 벽). 그래야 깔끔히 사라진다.
INPAINT_PROMPT = ("Replace this entire region with a soft, plain, out-of-focus blurred background — gentle warm "
                  "round bokeh lights or a smooth night sky or a plain wall — with NO buildings, NO structures, "
                  "NO signs, NO letters, NO text, NO logos. Flat Korean webtoon illustration style, smooth and clean.")


def _mask_for(im, boxes, pad):
    """흰=인페인트 영역, 검정=보존. 검출 박스 부정확을 흡수하려 넉넉히 + 가장자리 약간 페더."""
    W, H = im.size
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for b in boxes:
        px = _clamp(im, ((b["x0"] - pad) * W, (b["y0"] - pad) * H, (b["x1"] + pad) * W, (b["y1"] + pad) * H))
        if px[2] > px[0] and px[3] > px[1]:
            d.rectangle(px, fill=255)
    return m.filter(ImageFilter.GaussianBlur(max(3, int(0.006 * H))))


def inpaint_fal(path, boxes, prompt, pad):
    """plan B: fal FLUX Fill 로 마스크 영역만 재생성(주변과 일치) → 글자 깔끔 제거. 마스크가 부정확해도 강함."""
    import fal_client
    im = Image.open(path).convert("RGB")
    mask = _mask_for(im, boxes, pad)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        mp = Path(td) / "mask.png"
        mask.save(mp)
        img_url = fal_client.upload_file(str(path))
        mask_url = fal_client.upload_file(str(mp))
        result = fal_client.subscribe(INPAINT_MODEL, arguments={
            "image_url": img_url, "mask_url": mask_url, "prompt": prompt,
            "num_images": 1, "safety_tolerance": "2", "output_format": "png",
        }, with_logs=False)
    imgs = (result or {}).get("images") or []
    if not imgs or not imgs[0].get("url"):
        raise RuntimeError(f"fal fill 응답에 url 없음: {str(result)[:200]}")
    r = requests.get(imgs[0]["url"], timeout=120)
    r.raise_for_status()
    return r.content


def scrub_image(path, out, boxes, method, pad):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    acts = []
    for b in boxes:
        x0, y0, x1, y1 = b["x0"], b["y0"], b["x1"], b["y1"]
        # normalized → pixel, with padding
        px = [(x0 - pad) * W, (y0 - pad) * H, (x1 + pad) * W, (y1 + pad) * H]
        box = _clamp(im, px)
        if box[2] - box[0] < 4 or box[3] - box[1] < 4:
            continue
        if method == "blur":
            how = scrub_blur(im, box)
        elif method == "clone":
            how = scrub_clone(im, box)
        else:  # auto → blur (안전: clone 은 검출 박스가 부정확하면 인접부의 진짜 글자를 복제할 위험 → opt-in)
            how = scrub_blur(im, box)
        acts.append(f"{box} {b.get('what','text')} → {how}")
    im.save(out)
    return acts


def main():
    ap = argparse.ArgumentParser(description="가짜글자/간판 국소 제거(₩0, 재생성 없이)")
    ap.add_argument("--production")
    ap.add_argument("--only", help="비트 번호 (예 6,13)")
    ap.add_argument("--image", help="단일 이미지 입력")
    ap.add_argument("--out", help="단일 모드 출력(미지정 시 _scrub.png)")
    ap.add_argument("--method", choices=["auto", "blur", "clone"], default="auto")
    ap.add_argument("--pad", type=float, default=0.012, help="박스 패딩(정규화)")
    ap.add_argument("--box", action="append", help="수동 박스 x0,y0,x1,y1 (정규화), 반복가능")
    ap.add_argument("--detect", choices=["vision", "manual"], default="vision")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--inpaint", action="store_true", help="plan B: fal FLUX Fill 로 마스크 영역 재생성(유료·깔끔·부정확마스크에 강함)")
    ap.add_argument("--prompt", default=INPAINT_PROMPT, help="인페인트 프롬프트")
    ap.add_argument("--inpaint-pad", type=float, default=0.03, help="인페인트 마스크 패딩(넉넉히)")
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--reverify", action="store_true", help="끝나고 verify_images 재실행")
    a = ap.parse_args()

    manual_boxes = []
    for spec in a.box or []:
        v = [float(x) for x in spec.split(",")]
        manual_boxes.append({"x0": v[0], "y0": v[1], "x1": v[2], "y1": v[3], "what": "manual"})

    client = None
    if a.detect == "vision" and not manual_boxes:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("[err] ANTHROPIC_API_KEY 없음 → --box 로 수동 지정하거나 키 설정")
        import anthropic
        client = anthropic.Anthropic()

    def boxes_for(path):
        if manual_boxes:
            return manual_boxes
        return detect_boxes(client, a.model, path)

    def apply_one(path, out, boxes):
        if a.inpaint:
            Path(out).write_bytes(inpaint_fal(path, boxes, a.prompt, a.inpaint_pad))
            return [f"inpaint {len(boxes)}박스 → {INPAINT_MODEL}"]
        return scrub_image(path, out, boxes, a.method, a.pad)

    # 단일 이미지 모드
    if a.image:
        out = a.out or str(Path(a.image).with_suffix("")) + "_scrub.png"
        boxes = boxes_for(a.image)
        print(f"🧽 {a.image}: 박스 {len(boxes)}개 detect")
        if not boxes:
            print("  (글자 없음 → 변경 없음)"); return
        acts = apply_one(a.image, out, boxes)
        for x in acts:
            print("  ✂︎ " + x)
        print(f"✅ {out}")
        return

    # production 모드
    if not a.production:
        sys.exit("usage: --production <slug> 또는 --image <path>")
    prod = ROOT / "productions" / a.production
    fdir = prod / "flow_images"
    bdir = fdir / "_v1_backup"
    bdir.mkdir(exist_ok=True)
    only = set(int(x) for x in a.only.split(",")) if a.only else None
    imgs = sorted(glob.glob(str(fdir / "B*.png")))
    n_changed = 0
    for img in imgs:
        beat = int(re.search(r"B(\d+)", Path(img).name).group(1))
        if only and beat not in only:
            continue
        boxes = boxes_for(img)
        if not boxes:
            continue
        if not a.no_backup:
            Image.open(img).convert("RGB").save(bdir / f"{Path(img).stem}_pretext.png")
        acts = apply_one(img, img, boxes)
        if acts:
            n_changed += 1
            print(f"🧽 B{beat:02d}: {len(acts)}개 처리")
            for x in acts:
                print("   ✂︎ " + x)
    print(f"\n✅ {n_changed}컷 스크럽 완료" + (" (백업: _v1_backup/*_pretext.png)" if not a.no_backup and n_changed else ""))

    if a.reverify and n_changed:
        print("\n🔎 재검증:")
        os.system(f'{sys.executable} {ROOT}/scripts/verify_images.py --production {a.production}')


if __name__ == "__main__":
    main()
