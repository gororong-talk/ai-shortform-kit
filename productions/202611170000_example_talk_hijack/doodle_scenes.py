"""예시 장면 파일 — doodle_kit(코드로 그리는 손그림, 0원) 사용법.

실행: python scripts/doodle_kit.py 202611170000_example_talk_hijack
  → flow_images/B01.png … (1080×1920)

이 파일은 형식을 보여 주려고 4컷(B01·B04·B07·B09)만 그렸다. 실제 렌더에는 08_image_prompts.md 의
비트(B01~B10) 전부가 필요하니, 나머지는 같은 모양으로 추가하거나 Claude에게 이렇게 요청한다:
  "doodle_scenes.py 의 형식을 따라, 02_step3_narration.txt 의 S07 장면을 B06 으로 그려 줘.
   doodle_kit 의 person()·arm()·glyph()·page() 만 쓰고, 인물·소품은 화면 위 2/3 안에."

규칙
- SCENES = {"B##": page(배경색, SVG 본문)} 딕셔너리 하나.
- 인물은 person(x, y, 크기, …) — x,y는 머리 중심. 같은 dict(N, H)를 매 컷 재사용하면 외모가 절대 안 바뀐다.
- mood: flat·annoyed·angry·sorry·happy·firm / mouth="talk" 로 말하는 입.
- 글자는 glyph()로 ? ! 같은 기호 1개만. 진짜 문장은 자막이 맡는다.
- 하단 1/3은 자막 자리 — 비워 둔다.
"""
from doodle_kit import INK, ST, person, arm, glyph, page

N = dict(hair="#b98a6b", shirt="#f3d9e4", kind="woman")   # 화자(아내)
H = dict(hair="#4a4442", shirt="#bcd3c2", kind="man")     # 남편


def bubble(x, y, s=1.0, flip=False, fill="#fffdf2"):
    """말풍선 모양(글자 없음)."""
    return (f'<g transform="translate({x},{y}) scale({-s if flip else s},{s})">'
            f'<path d="M-170 60 q-30 -150 130 -170 q200 -20 220 110 q10 120 -150 130 q-60 0 -100 -10 '
            f'q-40 50 -110 40 q40 -40 10 -100z" fill="{fill}" {ST}/></g>')


def paper(x, y, rot=-8):
    """검진 결과지(줄만 — 가짜 글자 없음)."""
    lines = "".join(f'<path d="M-60 {y0} L60 {y0}" {ST}/>' for y0 in (-50, -10, 30))
    return (f'<g transform="translate({x},{y}) rotate({rot})"><rect x="-95" y="-120" width="190" height="240" rx="14" '
            f'fill="#fffdf2" {ST}/>{lines}<circle cx="50" cy="80" r="22" fill="#ff8f8f" {ST}/></g>')


SCENES = {
    # 훅: 화자가 말하는데 남편 말풍선이 더 크게 덮는다
    "B01": page("#fdf1e6",
                bubble(330, 300, 0.8) + bubble(700, 330, 1.25, flip=True, fill="#e3efe6")
                + person(300, 720, 1.0, mood="sorry", mouth="talk", **N)
                + person(780, 720, 1.0, mood="happy", mouth="talk", flip=True, **H)),

    # 재검 통보: 화자는 결과지를 쥐고 불안, 남편은 딴 데 보며 자기 얘기
    "B04": page("#eef1f7",
                person(320, 760, 1.0, mood="sorry", **N)
                + arm("M380 1000 Q470 1010 500 930", N["shirt"]) + paper(520, 880)
                + person(800, 700, 0.95, mood="happy", mouth="talk", **H)
                + bubble(820, 330, 0.9, flip=True, fill="#e3efe6")),

    # 항변: 남편 팔짱(답답), 화자 쪽에 물음표
    "B07": page("#f6efe2",
                person(300, 760, 1.0, mood="annoyed", **N) + glyph("?", 300, 470, 150)
                + person(790, 720, 1.05, mood="firm", mouth="talk", flip=True, **H)
                + arm("M700 1010 Q790 960 880 1010", H["shirt"])),

    # 사이다: 이번엔 화자 말풍선이 크고, 남편이 머쓱
    "B09": page("#fdeef0",
                bubble(360, 320, 1.25, fill="#f8dce6") + bubble(760, 360, 0.7, flip=True)
                + person(300, 720, 1.0, mood="firm", mouth="talk", **N)
                + person(790, 740, 0.95, mood="sorry", flip=True, **H) + glyph("!", 900, 470, 130)),
}
