#!/usr/bin/env python3
"""doodle_kit.py — 코드로 그리는 파스텔 손그림(₩0·무제한·인물 100% 일관) 이미지 백엔드.

fal 잔액 소진 + 친근 톤 실험(2026-11-16)으로 신설. 장면은 production 폴더의 `doodle_scenes.py`가
`SCENES = {"B01": page(bg, body_svg), ...}` 로 정의하고, 여기의 person()/page()/render() 를 쓴다.
    .venv/bin/python scripts/doodle_kit.py <slug>      → productions/<slug>/flow_images/B##.png (1080x1920)
shortcut: 인물은 상반신 한 종류(person)뿐이고 소품은 장면 파일에서 SVG 로 직접 그린다 — 3편 이상 쓰게 되면 소품 함수를 이쪽으로 승격.
⚠ 자막이 하단에 깔리므로 인물·소품은 화면 위 2/3 안에 둔다.
"""
import importlib.util, os, sys

INK = "#5b4a42"
ST = f'stroke="{INK}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"'
DEFS = """
<defs>
  <filter id="wob" x="-5%" y="-5%" width="110%" height="110%">
    <feTurbulence type="fractalNoise" baseFrequency="0.018" numOctaves="2" seed="7" result="n"/>
    <feDisplacementMap in="SourceGraphic" in2="n" scale="9"/>
  </filter>
  <filter id="paper"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3"/>
    <feColorMatrix values="0 0 0 0 0.45  0 0 0 0 0.38  0 0 0 0 0.33  0 0 0 0.07 0"/></filter>
</defs>"""

_BROW = {"flat": "M-58 -38 L-26 -38 M26 -38 L58 -38",
         "annoyed": "M-60 -44 L-26 -34 M26 -40 L60 -40",
         "angry": "M-62 -52 L-24 -32 M24 -32 L62 -52",
         "sorry": "M-60 -34 L-26 -46 M26 -46 L60 -34",
         "happy": "M-58 -42 Q-42 -50 -26 -42 M26 -42 Q42 -50 58 -42",
         "firm": "M-60 -46 L-26 -36 M26 -36 L60 -46"}
_MOUTH = {"flat": "M-22 52 L22 52", "annoyed": "M-24 56 Q0 44 24 56",
          "angry": "M-30 50 Q0 78 30 50 Q0 40 -30 50 Z", "sorry": "M-20 58 Q0 48 20 58",
          "happy": "M-26 46 Q0 72 26 46", "firm": "M-20 54 L20 54",
          "talk": "M-20 48 Q0 70 20 48 Q0 42 -20 48 Z"}


def person(x, y, s=1.0, hair="#b98a6b", shirt="#dfe3ea", mood="flat", kind="woman", flip=False, mouth=None):
    """상반신 인물. x,y=머리 중심. kind: woman(묶은 머리)|man(짧은 머리+희끗)|bob(단발). mood: _BROW 키."""
    m = _MOUTH[mouth or mood]
    mfill = "#8d5a55" if (mouth or mood) in ("angry", "talk") else "none"
    if kind == "woman":
        hair_svg = (f'<path d="M-112 -10 Q-120 -128 0 -132 Q120 -128 112 -10 Q96 -74 30 -84 Q-40 -80 -112 -10 Z" fill="{hair}" {ST}/>'
                    f'<path d="M100 -40 Q178 -20 150 80 Q138 120 118 96 Q140 30 96 10 Z" fill="{hair}" {ST}/>')
    elif kind == "bob":
        hair_svg = f'<path d="M-118 70 Q-136 -134 0 -134 Q136 -134 118 70 Q112 -60 30 -80 Q-60 -78 -100 -20 Q-104 30 -118 70 Z" fill="{hair}" {ST}/>'
    else:
        hair_svg = (f'<path d="M-108 -30 Q-112 -128 0 -128 Q112 -128 108 -30 Q70 -86 0 -84 Q-70 -86 -108 -30 Z" fill="{hair}" {ST}/>'
                    f'<path d="M-110 -34 Q-104 -70 -84 -74 M110 -34 Q104 -70 84 -74" fill="none" stroke="#cfcfd4" stroke-width="16" stroke-linecap="round"/>')
    eyes = (f'<path d="M-54 -2 Q-42 -16 -30 -2 M30 -2 Q42 -16 54 -2" fill="none" {ST}/>' if mood == "happy"
            else f'<circle cx="-42" cy="-4" r="9" fill="{INK}"/><circle cx="42" cy="-4" r="9" fill="{INK}"/>')
    g = f'<g transform="translate({x},{y}) scale({-s if flip else s},{s})">'
    g += f'<path d="M-150 420 Q-160 150 -70 118 L70 118 Q160 150 150 420 Z" fill="{shirt}" {ST}/>'
    g += f'<path d="M-34 118 L0 160 L34 118" fill="none" {ST}/>'
    g += f'<ellipse cx="0" cy="0" rx="108" ry="112" fill="#ffe9d6" {ST}/>' + hair_svg + eyes
    g += f'<path d="{_BROW[mood]}" fill="none" {ST}/><path d="{m}" fill="{mfill}" {ST}/>'
    g += '<ellipse cx="-70" cy="30" rx="20" ry="12" fill="#ffb9b0" opacity=".7"/><ellipse cx="70" cy="30" rx="20" ry="12" fill="#ffb9b0" opacity=".7"/>'
    return g + "</g>"


def arm(d, color):
    """굵은 팔 한 획(path d)."""
    return (f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="46" stroke-linecap="round"/>'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="30" stroke-linecap="round"/>')


def glyph(ch, x, y, size=120, fill=INK):
    """? ! Z 같은 진짜 글자 1개(가짜 글자 아님)."""
    return (f'<text x="{x}" y="{y}" font-family="Arial Rounded MT Bold, Helvetica, sans-serif" font-weight="700" '
            f'font-size="{size}" fill="{fill}" text-anchor="middle">{ch}</text>')


def page(bg, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">{DEFS}'
            f'<rect width="1080" height="1920" fill="{bg}"/>'
            f'<g filter="url(#wob)">{body}</g><rect width="1080" height="1920" filter="url(#paper)"/></svg>')


def render(scenes: dict, outdir: str):
    from playwright.sync_api import sync_playwright
    os.makedirs(outdir, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        for name, svg in scenes.items():
            pg.set_content(f'<html><body style="margin:0">{svg}</body></html>')
            pg.screenshot(path=os.path.join(outdir, f"{name}.png"))
            print("✅", name)
        b.close()


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prod = os.path.join(root, "productions", sys.argv[1])
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("doodle_scenes", os.path.join(prod, "doodle_scenes.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    assert mod.SCENES, "SCENES 비어 있음"
    render(mod.SCENES, os.path.join(prod, "flow_images"))
