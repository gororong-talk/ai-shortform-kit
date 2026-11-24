#!/usr/bin/env python3
"""키즈 프롬프트 다양성 검사 — 같은 '장면' 프롬프트 재사용 경고 (2026-06-17 박제).

배경: 키즈 채널 최대 위험 = 저품질 AI 양산물/유사콘텐츠 단속. 에피소드마다 MASCOT
캐릭터 블록은 일관성을 위해 고정(정상)이지만, 장면·배경·포즈·구도까지 복붙하면
"같은 영상 찍어낸다"로 분류될 수 있다. 이 검사는 MASCOT 캐릭터 블록을 제외한 '장면'
묘사를 다른 mascot 에피소드와 비교해 과도하게 유사하면 경고한다.

  python scripts/check_kids_prompt_variety.py <slug>
  (종료코드: 0=충분히 다양 / 1=0.5+ 유사 발견)
"""
import glob, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 스타일·보일러플레이트·캐릭터 공통어 — 장면 비교에서 제외(이건 원래 모든 편에 같음)
STOP = {
    "a", "an", "the", "of", "with", "and", "one", "its", "in", "on", "at", "to", "as",
    "big", "clear", "soft", "cute", "round", "pastel", "background", "mood", "warm",
    "gentle", "large", "mascot", "kitten", "cream", "butter", "colored", "caramel",
    "tipped", "ears", "tail", "amber", "eyes", "tiny", "pink", "nose", "fur", "paw",
    "paws", "chubby", "small", "expression", "happy", "bright", "smile", "vertical",
    "no", "text", "letters", "signage", "single",
}


def scenes(path):
    """08 파일 → {비트id: 장면토큰집합} (MASCOT 블록·보일러플레이트 제거)."""
    txt = open(path, encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"^##\s*(B\d+).*?$\n(.*?)(?=^##|\Z)", txt, re.M | re.S):
        body = re.sub(r"MASCOT\s*\([^)]*\)", " ", m.group(2))      # 캐릭터 블록 제거
        body = re.sub(r"Vertical 9:16.*", " ", body, flags=re.S)  # 스타일 보일러플레이트 제거
        toks = {t for t in re.findall(r"[a-z]+", body.lower()) if t not in STOP and len(t) > 2}
        if toks:
            out[m.group(1)] = toks
    return out


def jac(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0.0


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: check_kids_prompt_variety.py <slug>")
    slug = sys.argv[1]
    tgt = scenes(os.path.join(ROOT, "productions", slug, "08_image_prompts.md"))
    others = [p for p in glob.glob(os.path.join(ROOT, "productions", "*mascot*", "08_image_prompts.md"))
              if slug not in p]
    print(f"[{slug}] 장면 비트 {len(tgt)}개 · 비교대상 {len(others)} 에피소드")
    worst = 0.0
    for p in sorted(others):
        ep = os.path.basename(os.path.dirname(p))
        o = scenes(p)
        for bid, tk in tgt.items():
            best = max(((jac(tk, otk), obid) for obid, otk in o.items()), default=(0, "-"))
            if best[0] >= 0.5:
                print(f"  ⚠️ {bid} ↔ {ep}:{best[1]}  장면 유사도 {best[0]:.0%}  (장면을 더 다양화하세요)")
            worst = max(worst, best[0])
    ok = worst < 0.5
    print(f"\n최대 장면 유사도 {worst:.0%} — {'✅ 충분히 다양 (캐릭터만 일관, 장면은 변주)' if ok else '⚠️ 0.5+ : 같은 장면 재사용 의심 → 배경·포즈·구도 변경'}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
