#!/usr/bin/env python3
"""
generate_images_fal.py — fal.ai FLUX 로 productions/<slug>/flow_images/B##.png 생성

막힌 Gemini-image(2.5-flash-image, 429) + Flow 월구독을 대체하는 종량제 이미지 백엔드.
키·SDK 이미 보유: .env FAL_KEY + .venv fal_client 0.13.1.

두 가지 모드:
  ① 텍스트→이미지 (기본): FLUX schnell/dev. 단일 사물·배경·마스코트(토리)엔 충분.
  ② ★레퍼런스 잠금 (--ref, 2026-06-21 신설): 인물 사연처럼 **같은 사람 얼굴이 비트마다
     유지돼야** 할 때. 캐릭터 레퍼런스 1장을 받아 매 비트를 fal-ai/flux-pro/kontext 로
     "같은 인물, 새 장면"으로 편집 → 얼굴·헤어·의상 일관. 2인 비트는 kontext multi.

단가(2026-06): schnell ~₩12/장 · dev ~₩45 · kontext ~₩54/장 · kontext-multi ~₩108/장.

입력 : productions/<slug>/08_image_prompts.md   (## B##  (S##) — 설명 \n 영문프롬프트)
출력 : productions/<slug>/flow_images/B##.png    (1080×1920, compose_narration 이 바로 읽음)

사용:
  # 1장 스모크/레퍼런스 생성(schnell, 손 숨김·정면):
  .venv/bin/python scripts/generate_images_fal.py --prompt "Korean webtoon portrait ..., no text" --out flow_images/_ref_grandpa.png
  # production 전체 (텍스트→이미지):
  .venv/bin/python scripts/generate_images_fal.py --production <slug>
  # ★레퍼런스 잠금: 비트 프롬프트에 등장하는 ROLE 토큰을 가진 레퍼런스로 Kontext 편집:
  .venv/bin/python scripts/generate_images_fal.py --production <slug> \
        --ref grandpa=flow_images/_ref_grandpa.png --ref grandma=flow_images/_ref_grandma.png
  .venv/bin/python scripts/generate_images_fal.py --production <slug> --only 4,7 --ref ...

⚠️ FLUX 는 guidance-distilled 라 **negative 프롬프트를 무시**한다(2026-06-21 확인).
   "NOT photorealistic" 식은 오히려 그 단어를 그리라고 주입하는 꼴 → 모두 **positive 표현**으로.
   손/반지: FLUX 최악 약점 → 프롬프트에서 손은 프레임 밖/단순하게, **반지·보석 클로즈업 금지**.
"""
from __future__ import annotations
import os, re, io, sys, time, argparse, subprocess
from pathlib import Path

try:
    import requests
except ImportError:
    print("[err] requests 미설치", file=sys.stderr); sys.exit(1)
try:
    from PIL import Image
except ImportError:
    print("[err] Pillow 미설치", file=sys.stderr); sys.exit(1)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
W, H = 1080, 1920
COST_PER_IMG = {"schnell": 0.009, "dev": 0.033}
COST_KONTEXT = {"single": 0.04, "multi": 0.08}
DEFAULT_SIZE = "portrait_16_9"
KONTEXT_SINGLE = "fal-ai/flux-pro/kontext"
KONTEXT_MULTI = "fal-ai/flux-pro/kontext/max/multi"

# FLUX 는 기본이 사실주의로 기울어 납작한 2D 웹툰을 강하게 못박아야 한다.
# ★전부 positive (FLUX 는 negative 무시 → "NOT 3d" 류는 harmful, 제거).
# ★손/반지 가드 내장: 손은 단순/프레임밖, 보석 클로즈업 금지(FC-022 / 2026-06-21 elder_love 교훈).
WEBTOON_PREFIX = ("flat 2D Korean webtoon manhwa illustration, bold clean black ink linework, "
                  "flat cel shading, anime style, limited flat matte colors, simple drawn illustration, "
                  "characters shown waist-up, hands relaxed and simple or out of frame, clean natural "
                  "five-finger hands, no jewelry close-ups, no readable text. ")
CUTE_PREFIX = ("adorable soft pastel storybook illustration, kawaii, rounded chubby shapes, "
               "big expressive sparkly eyes, gentle warm golden lighting, cozy wholesome mood, "
               "children's picture book art, flat 2D illustration, simple clean hands, no readable text. ")


def wrap_style(prompt: str, style: str) -> str:
    """style=webtoon(기본)=납작한 2D / cute=파스텔 동화풍 / none=원문. negative 미부착(FLUX 무시)."""
    if style == "webtoon":
        return WEBTOON_PREFIX + prompt
    if style == "cute":
        return CUTE_PREFIX + prompt
    return prompt


def parse_prompt_sheet(md: Path) -> list[dict]:
    if not md.exists():
        raise FileNotFoundError(f"08_image_prompts.md 없음: {md}")
    text = md.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r'^##\s+B(\d+)\b[^\n]*\n(.*?)(?=^##\s+B\d+\b|^---\s*$|\Z)',
                         text, re.MULTILINE | re.DOTALL):
        beat = int(m.group(1))
        prompt = m.group(2).strip()
        if prompt:
            out.append({"beat": beat, "prompt": prompt})
    return sorted(out, key=lambda x: x["beat"])


def fal_generate(prompt: str, model: str, size: str) -> bytes:
    """텍스트→이미지: fal.ai FLUX schnell/dev."""
    import fal_client
    app = f"fal-ai/flux/{model}"
    result = fal_client.subscribe(app, arguments={
        "prompt": prompt, "image_size": size, "num_images": 1, "enable_safety_checker": True,
    }, with_logs=False)
    return _first_image_bytes(result)


_REF_URL_CACHE: dict[str, str] = {}


def upload_ref(path: Path) -> str:
    """레퍼런스 PNG 를 fal 에 업로드(한 번만, URL 캐시)."""
    import fal_client
    k = str(path)
    if k not in _REF_URL_CACHE:
        _REF_URL_CACHE[k] = fal_client.upload_file(str(path))
    return _REF_URL_CACHE[k]


def fal_generate_kontext(scene_prompt: str, ref_paths: list[Path], roles: list[str]) -> tuple[bytes, str]:
    """레퍼런스 잠금: flux-pro/kontext 로 '같은 인물, 새 장면' 편집. 2인↑이면 kontext multi."""
    import fal_client
    urls = [upload_ref(p) for p in ref_paths]
    keep = "Keep the SAME " + " and ".join(roles) + \
           " — identical face, hairstyle, and outfit colors as in the reference image(s)"
    prompt = (f"{keep}. Flat 2D Korean webtoon manhwa style, clean black ink linework, flat cel shading. "
              f"New scene: {scene_prompt} "
              f"Characters waist-up, hands relaxed and simple or out of frame, clean five-finger hands, "
              f"no jewelry close-ups, no readable text.")
    if len(urls) == 1:
        app, args, kind = KONTEXT_SINGLE, {"image_url": urls[0]}, "single"
    else:
        app, args, kind = KONTEXT_MULTI, {"image_urls": urls}, "multi"
    args.update({"prompt": prompt, "aspect_ratio": "9:16", "guidance_scale": 3.5,
                 "num_images": 1, "output_format": "png", "safety_tolerance": "2"})
    result = fal_client.subscribe(app, arguments=args, with_logs=False)
    return _first_image_bytes(result), kind


FLUX2_EDIT = "fal-ai/flux-2-pro/edit"


def fal_generate_flux2(scene_prompt: str, ref_paths: list[Path], roles: list[str]) -> bytes:
    """멀티 인물 잠금 = FLUX.2 edit. @imageN 으로 인물↔레퍼런스 바인딩 → Kontext multi 병합 회피.
    (2026-06-21 실증: Kontext multi는 4인에서 병합/복제, FLUX.2 @imageN 은 인물별 결합으로 구분 유지.)"""
    import fal_client
    urls = [upload_ref(p) for p in ref_paths]
    prompt = scene_prompt
    for i, role in enumerate(roles, 1):
        # 'ROLE (외형블록)' → '@imageN (the role)' : 외형 텍스트 제거(FLUX.2가 색이름을 글자로 굽는 것 방지).
        # 레퍼런스 이미지가 외형을 담당하므로 바인딩만 남긴다.
        prompt = re.sub(re.escape(role) + r"\s*\([^)]*\)", f"@image{i} (the {role.lower()})",
                        prompt, flags=re.IGNORECASE)
        prompt = re.sub(r"\b" + re.escape(role) + r"\b", f"@image{i}", prompt, flags=re.IGNORECASE)
    prompt = ("Flat 2D Korean webtoon manhwa illustration, clean black ink linework, cel shading, flat matte colors. "
              + prompt + " Keep each person exactly as their reference image (same face, hair, glasses, outfit colors). "
              "Hands simple. ABSOLUTELY NO text, letters, words, or signage anywhere in the image.")
    result = fal_client.subscribe(FLUX2_EDIT, arguments={
        "image_urls": urls, "prompt": prompt, "image_size": "portrait_16_9", "num_images": 1,
    }, with_logs=False)
    return _first_image_bytes(result)


def _first_image_bytes(result) -> bytes:
    imgs = (result or {}).get("images") or []
    if not imgs or not imgs[0].get("url"):
        raise RuntimeError(f"fal 응답에 image url 없음: {str(result)[:200]}")
    r = requests.get(imgs[0]["url"], timeout=120)
    r.raise_for_status()
    return r.content


def roles_in_prompt(prompt: str, role_names: list[str]) -> list[str]:
    """비트 프롬프트에 등장하는 등록 ROLE(예 GRANDPA/GRANDMA/NARRATOR) 추출(순서 유지)."""
    low = prompt.lower()
    return [r for r in role_names if re.search(r"\b" + re.escape(r.lower()) + r"\b", low)]


def cover_fit(raw: bytes, w: int, h: int) -> Image.Image:
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    sw, sh = img.size
    scale = max(w / sw, h / sh)
    img = img.resize((round(sw * scale), round(sh * scale)), Image.LANCZOS)
    nw, nh = img.size
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def parse_refs(specs: list[str], prod: Path) -> dict[str, Path]:
    refs: dict[str, Path] = {}
    for spec in specs or []:
        role, _, p = spec.partition("=")
        role = role.strip()
        if not role or not p:
            print(f"[err] --ref 형식: role=경로 (받음: {spec})", file=sys.stderr); sys.exit(1)
        rp = Path(p)
        if not rp.is_absolute():
            rp = prod / p
        if not rp.exists():
            print(f"[err] 레퍼런스 없음: {rp}", file=sys.stderr); sys.exit(1)
        refs[role] = rp
    return refs


def _reveal_finder(target):
    """완성된 이미지를 Finder 로 띄워 사용자가 직접 검수 (2026-06-25 사용자 지침: 자동 비전QC
    대신 사람이 눈으로 본다). macOS 한정 · --no-open 으로 억제(cron/비대화)."""
    if sys.platform != "darwin":
        return
    try:
        p = str(target)
        if os.path.isfile(p):
            subprocess.run(["open", "-R", p])      # 파일 → 폴더에서 선택(reveal)
        elif os.path.isdir(p):
            subprocess.run(["open", p])            # 폴더 → 그 창 열어 전체 검수
        print(f"🪟 Finder 열림 — 이미지 직접 검수: {p}")
    except Exception as e:
        print(f"(Finder 열기 실패: {e})", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="fal.ai FLUX 이미지 생성 (텍스트→이미지 + 레퍼런스 잠금)")
    ap.add_argument("--production", help="슬러그 — 08_image_prompts.md 전체 → flow_images/B##.png")
    ap.add_argument("--prompt", help="단일 프롬프트(스모크/레퍼런스 생성). --out 과 함께")
    ap.add_argument("--out", help="단일 모드 출력 경로")
    ap.add_argument("--model", default="schnell", choices=["schnell", "dev"], help="기본 schnell(저가)")
    ap.add_argument("--size", default=DEFAULT_SIZE, help=f"fal image_size (기본 {DEFAULT_SIZE})")
    ap.add_argument("--style", default="webtoon", choices=["webtoon", "cute", "none"],
                    help="webtoon(기본) / cute / none. 텍스트→이미지 비트에만 적용")
    ap.add_argument("--ref", action="append", metavar="ROLE=PATH",
                    help="★레퍼런스 잠금: 비트에 ROLE(예 grandpa) 등장 시 그 레퍼런스로 Kontext 편집. 반복가능")
    ap.add_argument("--flux2", action="store_true",
                    help="멀티 인물 비트를 FLUX.2 edit(@imageN 바인딩)로 — Kontext multi 4인 병합 회피(2026-06-21 실증)")
    ap.add_argument("--only", help="비트 번호만 (예: 1,31)")
    ap.add_argument("--dry-run", action="store_true", help="파싱·플랜만, fal 호출 0")
    ap.add_argument("--no-open", action="store_true", help="완료 후 Finder 안 열음(cron/비대화)")
    a = ap.parse_args()

    if not os.environ.get("FAL_KEY") and not a.dry_run:
        print("[err] FAL_KEY 미설정 (.env 확인)", file=sys.stderr); sys.exit(1)

    unit = COST_PER_IMG.get(a.model, 0.01)

    # ── 단일 모드 (스모크 / 레퍼런스 생성) ──
    if a.prompt:
        if not a.out:
            print("[err] --prompt 는 --out 필요", file=sys.stderr); sys.exit(1)
        if a.dry_run:
            print(f"[dry] model={a.model}\n  {a.prompt[:120]}...\n  → {a.out}"); return
        outp = Path(a.out)
        if not outp.is_absolute() and a.production:
            outp = PROJECT_ROOT / "productions" / a.production / a.out
        t0 = time.time()
        print(f"[info] fal-ai/flux/{a.model} 생성 중... (style={a.style})")
        raw = fal_generate(wrap_style(a.prompt, a.style), a.model, a.size)
        outp.parent.mkdir(parents=True, exist_ok=True)
        cover_fit(raw, W, H).save(outp)
        print(f"[ok] {outp}  ({outp.stat().st_size//1024}KB, {time.time()-t0:.1f}s, ~${unit:.3f})")
        if not a.no_open:
            _reveal_finder(outp)
        return

    if not a.production:
        print("[err] --production 또는 --prompt/--out 필요", file=sys.stderr); sys.exit(1)
    prod = PROJECT_ROOT / "productions" / a.production
    if not prod.exists():
        print(f"[err] production 폴더 없음: {prod}", file=sys.stderr); sys.exit(1)
    items = parse_prompt_sheet(prod / "08_image_prompts.md")
    if a.only:
        keep = {int(x) for x in a.only.split(",")}
        items = [it for it in items if it["beat"] in keep]
    if not items:
        print("[err] 08_image_prompts.md 에서 B## 프롬프트를 못 찾음", file=sys.stderr); sys.exit(1)

    refs = parse_refs(a.ref, prod)
    role_names = list(refs.keys())

    # ⚠️ 가드: 비트가 ROLE 토큰을 'absent/not present' 바로 옆에 쓰면 roles_in_prompt 가
    #    단어경계로 토큰을 잡아 '있음'으로 오판 → 부재 인물이 레퍼런스로 그려진다.
    #    (sidaek_secret 2026-06-25 발견) 부재 인물은 토큰 대신 'no one else present' 로.
    if role_names:
        absent_re = re.compile(r"\b(absent|not present|away|gone|no longer (?:here|present))\b")
        for it in items:
            low = it["prompt"].lower()
            for r in role_names:
                for m in re.finditer(r"\b" + re.escape(r.lower()) + r"\b", low):
                    if absent_re.search(low[m.end():m.end() + 24]):
                        print(f"⚠️  B{it['beat']:02d}: '{r}' 토큰이 부재표현 옆에 있음 — "
                              f"roles_in_prompt 가 '있음'으로 오판해 {r} 가 그려질 수 있음. "
                              f"부재 인물은 'no one else present' 같은 토큰 없는 표현으로.",
                              file=sys.stderr)
                        break

        # ⚠️ 가드2 (2026-06-26 박제, solo_parenting B02/B16/B20): --ref 키가 흔한 공통명사
        #    (특히 baby)면 소품 합성어("baby bottle/carrier/toys") 안에서도 roles_in_prompt
        #    가 \b 로 잡아 → solo/부재 비트에 ref 인물이 그려진다. 가드1(부재표현)이 못 잡는
        #    케이스(부재단어가 옆에 없음). solo 마커 있는 비트에서 키의 '모든' 출현이 소품
        #    합성어의 머리면 경고(등장 비트는 solo 마커가 없어 정탐으로 침묵 → 오탐≈0).
        PROP_NOUNS = {
            "bottle", "carrier", "sling", "toy", "toys", "sock", "socks", "monitor",
            "food", "formula", "blanket", "seat", "stroller", "cot", "crib", "wipes",
            "diaper", "diapers", "clothes", "shoes", "photo", "picture", "doll",
            "stuff", "stuffed", "things", "items", "mobile", "bib", "pram", "playpen",
        }
        solo_re = re.compile(r"\b(single character|no one else present|"
                             r"no other people|alone|by (?:him|her)self)\b")
        def _next_word(text, end):
            tail = text[end:].split()
            return tail[0].rstrip(",.;:!?'\")") if tail else ""
        for it in items:
            low = it["prompt"].lower()
            if not solo_re.search(low):
                continue                       # solo 마커 없으면 등장 비트(정탐) → 침묵
            for r in role_names:
                matches = list(re.finditer(r"\b" + re.escape(r.lower()) + r"\b", low))
                if matches and all(_next_word(low, m.end()) in PROP_NOUNS for m in matches):
                    snip = low[matches[0].start():matches[0].end() + 14].strip()
                    print(f"⚠️  B{it['beat']:02d}: solo 비트인데 '{r}' 키가 소품 합성어"
                          f"('{snip}…')에만 등장 — roles_in_prompt 가 단어경계로 잡아 "
                          f"--ref {r} 바인딩 → 부재 {r} 가 그려질 수 있음. 공통명사 회피"
                          f"(예: baby bottle→feeding bottle, baby carrier→front carrier sling).",
                          file=sys.stderr)
                    break

    # ⚠️ 가드(2026-11-17): --ref 역할 이름이 어느 비트 프롬프트에도 없으면 그 레퍼런스는 한 번도 안 붙는다.
    #   예: 프롬프트는 WIFE, 레퍼런스는 narrator → 아내 컷이 전부 text-only로 생성돼 얼굴이 드리프트(조용한 오류).
    for r in role_names:
        if not any(r in roles_in_prompt(it["prompt"], role_names) for it in items):
            print(f"⚠️  --ref {r} 가 어느 비트에도 안 붙습니다 — 프롬프트에 '{r.upper()}' 토큰이 없음. "
                  f"프롬프트의 인물 토큰을 레퍼런스 이름과 맞추세요.", file=sys.stderr)

    fdir = prod / "flow_images"; fdir.mkdir(parents=True, exist_ok=True)
    todo = [it for it in items if not (fdir / f"B{it['beat']:02d}.png").exists()]
    skip = len(items) - len(todo)

    # 플랜: 각 비트가 텍스트→이미지 vs 레퍼런스(single/multi)
    def plan(it):
        present = roles_in_prompt(it["prompt"], role_names) if refs else []
        if not present:
            return ("text", [], unit)
        kind = "single" if len(present) == 1 else "multi"
        return (kind, present, COST_KONTEXT[kind])
    est = sum(plan(it)[2] for it in todo)
    mode = f"레퍼런스 잠금({','.join(role_names)})" if refs else f"텍스트→이미지({a.model})"
    print(f"📋 {len(items)} 비트 (이미 있음 {skip} 건너뜀) → 생성 {len(todo)} | {mode} "
          f"| 예상 ~${est:.2f} (≈₩{round(est*1350)})")
    if a.dry_run:
        for it in todo:
            kind, present, c = plan(it)
            tag = f"{kind}:{'+'.join(present)}" if present else "text"
            print(f"  [dry] B{it['beat']:02d}  [{tag}]  {it['prompt'][:70]}...")
        return

    ok = fail = 0; fails = []
    for i, it in enumerate(todo, 1):
        out = fdir / f"B{it['beat']:02d}.png"
        kind, present, _ = plan(it)
        try:
            t0 = time.time()
            if present and a.flux2:   # --flux2 = 인물 등장 비트 전부 FLUX.2(단일도) → 화풍 균일
                raw = fal_generate_flux2(it["prompt"], [refs[r] for r in present], present)
                tag = f"flux2:{'+'.join(present)}"
            elif present:
                raw, k = fal_generate_kontext(it["prompt"], [refs[r] for r in present], present)
                tag = f"{k}:{'+'.join(present)}"
            else:
                raw = fal_generate(wrap_style(it["prompt"], a.style), a.model, a.size)
                tag = "text"
            cover_fit(raw, W, H).save(out)
            ok += 1
            print(f"  ✅ [{i}/{len(todo)}] B{it['beat']:02d}.png  [{tag}]  ({time.time()-t0:.1f}s)")
        except Exception as e:
            fail += 1; fails.append(it["beat"])
            print(f"  ❌ [{i}/{len(todo)}] B{it['beat']:02d}: {str(e)[:140]}")
        time.sleep(0.3)
    print(f"\n🏁 성공 {ok} / 실패 {fail}  → {fdir}")
    if fails:
        print(f"⚠️ 실패 비트(재시도): --only {','.join(map(str, fails))}")
    if ok and not a.no_open:
        _reveal_finder(fdir)   # ★ 완료 시 Finder 로 띄워 사용자 직접 검수 (자동 비전QC 대신)


if __name__ == "__main__":
    main()
