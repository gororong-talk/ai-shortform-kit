#!/usr/bin/env python3
"""
build_kids_episode.py — 키즈 채널 키즈 에피소드 자동 스캐폴더.

data/kids/curriculum.json 의 한 item(status:ready)을 소비해 한 편의 빌드 가능한
production 폴더를 생성한다.

결정적(deterministic) 파일은 커리큘럼에서 100% 자동 생성:
  00_meta.json · _edu_overlay.json · _beat_map.json · _clips.json · 02_step3_narration.txt
창작 부분(장면 변주 + 단어 나레이션 flavor)은 letter별 SCENE_PACK 에서 가져온다.
  → 왜 분리? AI-슬롭/유사콘텐츠 단속 회피 = 장면을 "진짜" 변주해야 하므로(커리큘럼
    _meta.anti_slop) letter마다 ~12줄 pack 을 큐레이션한다. 결정 구조는 자동, 장면은 큐레이션.

생성 후 다음 파이프라인(비용 발생·멱등)은 분리 실행한다(이 스크립트는 스캐폴드만):
  fal 이미지 → Fish 나레이션 → compose(큰글자 자동 번인) → check_kids_prompt_variety
스크립트 끝에 정확한 다음 명령을 출력한다.

지원 recipe: consonant (플래그십 한글 자모). vowel/number/word 는 추후 확장.

usage:
  python scripts/build_kids_episode.py hangul_consonants ㄹ
  python scripts/build_kids_episode.py hangul_consonants ㄹ --dry-run
"""
import argparse
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CURRICULUM = os.path.join(ROOT, "data", "kids", "curriculum.json")
PRODUCTIONS = os.path.join(ROOT, "productions")

# 자음 → slug 로마자 (production 디렉토리명 = 기존 mascot_ga/na/da 규약)
ROMANIZE = {
    "ㄱ": "ga", "ㄴ": "na", "ㄷ": "da", "ㄹ": "ra", "ㅁ": "ma", "ㅂ": "ba",
    "ㅅ": "sa", "ㅇ": "a", "ㅈ": "ja", "ㅊ": "cha", "ㅋ": "ka", "ㅌ": "ta",
    "ㅍ": "pa", "ㅎ": "ha",
}
ORDINAL_KO = {1: "첫", 2: "두", 3: "세", 4: "네", 5: "다섯", 6: "여섯", 7: "일곱",
              8: "여덟", 9: "아홉", 10: "열", 11: "열한", 12: "열두", 13: "열세", 14: "열네"}

# MASCOT 마스코트 영문 블록 (08 매 비트 그대로 복붙 = 캐릭터 일관성). curriculum _meta.mascot_block 과 동일.
MASCOT = ("a small round chubby kitten, soft cream butter-colored fur, "
         "caramel-tipped ears and tail, big round amber eyes, tiny pink nose")
SUFFIX = "Vertical 9:16 (1080x1920). No text, no letters, no signage."

# ── letter별 창작 pack ─────────────────────────────────────────────────────
#  friend_*  : B02 자음 소개 비트의 동반 친구(가능하면 그 자음으로 시작하는 동물).
#  w*_flavor : 단어 비트 나레이션 의성/의태어(단어 hint 에서 유도).
#  scenes[5] : (한글 라벨, MASCOT 표정, 영문 장면). 배경·포즈는 인접 편과 절대 겹치지 않게 큐레이션.
#  ▶ 다음 편 추가 = 여기에 letter 키 하나(약 12줄)만 더하면 됨. 나머지는 전부 자동.
# 키즈 _pubmeta YouTube 표준 태그(2026-06-22 사용자 지정) — 매 에피소드 _pubmeta YT description 에 포함.
#   에피소드별 니치태그(#키즈채널 #한글 #<자모> #한글공부)와 합쳐 사용. YT는 SEO라 ≤8 정책 제외.
KIDS_YT_TAGS = "#shorts #koreakids #고양이 #특별일러스트 #cat #유아교육 #cute"

SCENE_PACKS = {
    "ㄹ": {
        "friend_ko": "라마", "friend_en": "a cute little round baby llama",
        "w1_flavor": "삐빅삐빅 움직이는", "w2_flavor": "노랗고 새콤한",
        "scenes": [
            ("인사 (인트로) · 알록달록 장난감 방에서 빼꼼", "cheerful friendly expression",
             "popping up cheerfully from behind a soft toy box in a bright cozy pastel playroom full of "
             "round colorful building blocks and plush toys, one paw raised in a happy hello, warm sunny indoor mood"),
            ("리을(ㄹ) 소개 · 라마 친구와 무지개 언덕", "delighted teaching expression",
             "sitting cozily side by side with ONE cute little round baby llama friend on a soft pastel rainbow "
             "hill with fluffy clouds, MASCOT opening its mouth as if happily making a sound, gentle bright daytime mood"),
            ("로봇 · 반짝이는 작업실에서", "joyful excited expression",
             "standing beside ONE cute round friendly toy robot with a smooth round body, a little antenna and "
             "glowing happy button-eyes, in a bright colorful pastel workshop with soft gears and shapes, "
             "the single chubby robot large and clear beside MASCOT, playful cheerful mood"),
            ("레몬 · 햇살 가득한 레몬 과수원에서", "delighted happy expression",
             "holding up ONE big bright yellow round lemon with both paws in a sunny pastel lemon orchard with "
             "soft green leaves, the single plump lemon large and clear and centered, fresh cheerful sunny mood"),
            ("리캡 (ㄹ + 로봇 + 레몬) · 색종이 파티", "proud happy clapping expression",
             "clapping its paws happily in a bright cheerful pastel party scene, with a cute round friendly toy "
             "robot and a big bright yellow lemon together nearby, balloons and soft confetti in the background, "
             "celebratory warm mood"),
        ],
    },
    "ㅁ": {
        "friend_ko": "미어캣", "friend_en": "a cute little round meerkat",
        "w1_flavor": "알록달록 떠오르는", "w2_flavor": "머리에 쏙 쓰는",
        "scenes": [
            ("인사 (인트로) · 햇살 소풍 돗자리에서 빼꼼", "cheerful friendly expression",
             "popping up cheerfully from behind a small picnic basket on a soft checkered picnic blanket spread on "
             "sunny green grass, one paw raised in a happy hello, a few simple round fruits on the blanket, bright warm sunny mood"),
            ("미음(ㅁ) 소개 · 미어캣 친구와 모래 언덕", "delighted teaching expression",
             "sitting cozily side by side with ONE cute little round meerkat friend standing upright on a warm "
             "sandy pastel dune under a clear soft sky, MASCOT opening its mouth as if happily making a sound, gentle warm daylight mood"),
            ("무지개 · 비 갠 뒤 하늘 가리키기", "joyful excited expression",
             "standing on a small grassy hill and pointing one paw up at ONE big beautiful colorful rainbow arc "
             "across a soft pastel sky after the rain, a few tiny puddles reflecting below, fresh bright happy mood, the single rainbow large and clear"),
            ("모자 · 거울 앞에서 모자 쓰기", "delighted happy expression",
             "happily wearing ONE big cute round soft hat on its head in front of a small round mirror in a cozy "
             "pastel dressing nook, both paws holding the brim, the single chubby hat large and clear, warm cheerful mood"),
            ("리캡 (ㅁ + 무지개 + 모자) · 무지개 아래 깡총", "proud happy joyful expression",
             "doing a happy little jump with both paws up under ONE big colorful rainbow arc while wearing a cute "
             "round hat, ONE cute round meerkat friend waving nearby, soft pastel sunny sky with a few floating soft clouds, joyful celebratory mood"),
        ],
    },
    "ㅂ": {
        "friend_ko": "비버", "friend_en": "a cute little round baby beaver",
        "w1_flavor": "길쭉하고 노란", "w2_flavor": "하늘을 슝 나는",
        "scenes": [
            ("인사 (인트로) · 햇살 드는 그림책 읽기 코너에서 빼꼼", "cheerful friendly expression",
             "popping up cheerfully from behind a neat stack of colorful picture books in a bright cozy reading nook "
             "by a sunny window with soft potted plants, one paw raised in a happy hello, warm gentle indoor mood"),
            ("비읍(ㅂ) 소개 · 비버 친구와 잔잔한 연못가", "delighted teaching expression",
             "sitting cozily side by side with ONE cute little round baby beaver friend on a soft mossy bank beside a "
             "calm pastel pond with round lily pads and gentle cattails, MASCOT opening its mouth as if happily making a sound, soft fresh daylight mood"),
            ("바나나 · 햇살 가득한 파스텔 부엌에서", "delighted happy expression",
             "holding up ONE big bright yellow curved banana with both paws in a sunny pastel kitchen with a small "
             "round wooden table and a bowl of round fruits, the single plump banana large and clear and centered, cheerful warm mood"),
            ("비행기 · 구름 둥둥 활짝 열린 하늘에서", "joyful excited expression",
             "flying ONE big cute round friendly toy airplane held high with one paw across a wide open bright blue-pastel "
             "sky full of soft fluffy clouds and a tiny sun in the corner, breezy soaring feeling, the single chubby airplane large and clear, joyful mood"),
            ("리캡 (ㅂ + 바나나 + 비행기) · 노을 언덕 풍선잔치", "proud happy clapping expression",
             "cheering happily while holding a big yellow banana in one paw and a cute round toy airplane in the other "
             "on a soft pastel hilltop at warm golden sunset, a few floating balloons and ONE cute round beaver friend waving nearby, cozy celebratory mood"),
        ],
    },
}


# ── 한글 조사 헬퍼 ─────────────────────────────────────────────────────────
def _has_batchim(word):
    last = word[-1]
    code = ord(last) - 0xAC00
    if 0 <= code <= 11171:
        return (code % 28) != 0
    return True  # 한글 음절이 아니면 받침 있다고 간주(안전측)


def iyeyo(word):
    return "이에요" if _has_batchim(word) else "예요"


def eul(word):
    return "을" if _has_batchim(word) else "를"


# ── 빌더 ───────────────────────────────────────────────────────────────────
def load_curriculum():
    with open(CURRICULUM, encoding="utf-8") as f:
        return json.load(f)


def find_item(cur, series_key, selector):
    series = cur.get("series", {}).get(series_key)
    if not series:
        sys.exit(f"❌ series '{series_key}' 없음. 가능: {', '.join(cur.get('series', {}))}")
    items = series["items"]
    # selector = letter(자음/모음) 또는 index(1-based)
    idx = None
    if selector.isdigit():
        idx = int(selector) - 1
    else:
        for i, it in enumerate(items):
            if it.get("letter") == selector:
                idx = i
                break
    if idx is None or not (0 <= idx < len(items)):
        sys.exit(f"❌ '{selector}' 를 {series_key} 에서 못 찾음.")
    return series, items[idx], idx


def render_overlay(recipe, subs):
    """recipe.overlay_recipe 의 {placeholder} 를 치환해 _edu_overlay.json dict 생성."""
    out = {}
    for beat, items in recipe["overlay_recipe"].items():
        new_items = []
        for it in items:
            it2 = dict(it)
            text = it2["text"]
            for k, v in subs.items():
                text = text.replace("{" + k + "}", str(v))
            it2["text"] = text
            new_items.append(it2)
        out[beat] = new_items
    return out


def build_consonant(cur, series, item, idx):
    L = item["letter"]
    name = item["name"]
    snd = item["sound"]
    w1, w2 = item["word1"], item["word2"]
    pack = SCENE_PACKS.get(L)
    if not pack:
        sys.exit(
            f"❌ '{L}' 의 SCENE_PACK 이 없습니다.\n"
            f"   결정적 파일은 자동이지만 장면·나레이션 flavor 는 letter별 큐레이션이 필요합니다(anti-slop).\n"
            f"   scripts/build_kids_episode.py 의 SCENE_PACKS 에 '{L}' 키를 추가하세요\n"
            f"   (friend_ko/friend_en, w1_flavor/w2_flavor, scenes[5] — 인접 편과 배경 겹치지 않게)."
        )
    ordinal = ORDINAL_KO.get(idx + 1, f"{idx + 1}")
    meta_root = cur["_meta"]
    fr_ko, fr_en = pack["friend_ko"], pack["friend_en"]

    # 00_meta.json
    slug_ts = datetime.datetime.now().strftime("%Y%m%d%H%M")
    rom = ROMANIZE.get(L, "x")
    slug = f"{slug_ts}_mascot_{rom}"
    meta = {
        "slug": slug,
        "format": "narration_short",
        "track": "kids_edu",
        "channel": meta_root["channel"],
        "mascot": "토리 — 둥근 크림빛 아기 고양이 (캐러멜 귀·꼬리, 큰 호박색 눈)",
        "learning_objective": (
            f"한글 자음 {L}({name}) — 소리 '{snd}' 인식 + {L}로 시작하는 일상단어 "
            f"2개({w1}·{w2}) 명명+반복+리캡"
        ),
        "target_duration_sec": 34,
        "narration_tone": (
            f"패런티즈(과장 노래조) · 따뜻하고 또렷하게 · 유아 대상 · 자음 소리 '{snd}' 강조"
        ),
        "image_backend": "fal.ai FLUX schnell (--style cute)",
        "core_identity": (
            f"토리가 인트로 인사 → 한글 {ordinal} 번째 자음 {L}({name}) 소개"
            f"(소리 '{snd}', {fr_ko} 친구와 함께) → {L}로 시작하는 단어 {w1}·{w2}{eul(w2)} "
            f"하나씩 명명·반복(반복-멈춤 루프) → 리캡 → 아웃트로. "
            f"플래그십 자모 의인화 시리즈 {idx + 1}편({L})."
        ),
        "made_for_kids": True,
        "characters": ["토리(마스코트 고양이)"],
        "bgm_mood": "위안",
        "series": f"한글 자모 (플래그십) — {idx + 1}편 {L}",
        "subtitle_note": (
            f"큰 글자({L}·{name}·{w1}·{w2})는 compose 후 overlay_kids_letters로 상단 번인"
            f"(_edu_overlay.json). fal 이미지엔 글자 그리지 않음(no text)."
        ),
        "safety": (
            "아동용. 실명·로고·브랜드 없음. 차분한 페이스(과자극 금지). "
            "학습목표 명시·토리 일관·앞 편들과 진짜 변주(다른 자음 소리·다른 단어·다른 장면·배경)."
        ),
    }

    # 02_step3_narration.txt (ㄴ/ㄷ편 자연스러운 패턴)
    lines = [
        f"안녕! 토리예요. 오늘은 {ordinal} 번째 한글, {name}{eul(name)} 배워 볼까요?",
        f"이건 {name}, {L}이에요. 소리는 {snd}, {snd}, {snd}! {fr_ko}도 {snd}, {snd}, {fr_ko}! {L}!",
        f"{w1}! {w1}{iyeyo(w1)}. {pack['w1_flavor']} {name} {w1}. {w1}!",
        f"{w2}! {w2}{iyeyo(w2)}. {pack['w2_flavor']} {name} {w2}. {w2}!",
        f"{name} {snd}, {w1}, {w2}! 참 잘했어요. 토리랑 또 만나요!",
    ]
    narration = "".join(f"S{i:02d} {ln}\n" for i, ln in enumerate(lines, 1))

    # 08_image_prompts.md
    bgs = " / ".join(s[0].split("·")[-1].strip() for s in pack["scenes"])
    head = (
        f"# 08 IMAGE PROMPTS — 토리랑 한글: {name} {L} ({slug.split('_', 1)[1]})\n\n"
        f"- **slug**: {slug} · 5 stills · fal.ai FLUX schnell (`--style cute`) · 파스텔 동화풍 · no-text\n"
        f"- 마스코트 **토리**(MASCOT 블록)은 매 비트 그대로 복붙(일관성=필수). "
        f"**단, 장면·배경·포즈·구도는 앞 편(ㄱ/ㄴ/ㄷ…)과 절대 동일하게 쓰지 말 것** — "
        f"같은 장면 재사용=AI슬롭/유사콘텐츠 단속 위험. 본 편 배경={bgs}로 차별화.\n"
        f"- ★ 한글 글자({L}·{name}·{w1}·{w2})는 **영상 오버레이·자막으로만** → "
        f"fal 이미지엔 글자 절대 그리지 않음(no text). 토리 + 해당 사물만.\n\n"
        f"> MASCOT = {MASCOT}, cheerful friendly expression.\n\n---\n\n"
    )
    blocks = []
    for i, (label, expr, action) in enumerate(pack["scenes"], 1):
        blocks.append(
            f"## B{i:02d}  (S{i:02d})  — {label}\n"
            f"MASCOT ({MASCOT}, {expr}) {action}. {SUFFIX}\n"
        )
    image_prompts = head + "\n".join(blocks) + "\n"

    # _edu_overlay.json (consonant recipe overlay_recipe 치환)
    recipe = cur["recipes"]["consonant"]
    overlay = render_overlay(recipe, {"letter": L, "name": name, "word1": w1, "word2": w2})

    beats = recipe["beats"]
    beat_map = {str(i): [i] for i in range(1, beats + 1)}
    clips = {"clips": []}

    return slug, {
        "00_meta.json": meta,
        "02_step3_narration.txt": narration,
        "08_image_prompts.md": image_prompts,
        "_edu_overlay.json": overlay,
        "_beat_map.json": beat_map,
        "_clips.json": clips,
    }


# ── 숫자(number) recipe ────────────────────────────────────────────────────
#  ⚠️ FLUX schnell 은 '정확한 개수'를 그리지 못한다 → 수 학습은 큰 숫자 오버레이가 담당하고
#     이미지는 '여러 개 {obj}'로 충분(이미지에 개수를 의존하지 말 것). narration 은 1:1 탭 카운트.
NUMBER_SCENE_PACKS = {
    "6부터 10까지": {
        "lines": [
            "안녕! 토리랑 숫자를 세어 봐요. 오늘은 여섯부터 열까지!",
            "여섯! 사과가 여섯 개예요. 토리랑 같이, 여섯!",
            "일곱! 사과가 일곱 개. 하나 더, 일곱!",
            "여덟! 사과가 여덟 개. 또 하나, 여덟!",
            "아홉! 사과가 아홉 개. 거의 다 왔어요, 아홉!",
            "열! 사과가 열 개. 우와, 열 개나!",
            "여섯, 일곱, 여덟, 아홉, 열! 다 셌어요. 참 잘했어요. 토리랑 또 만나요!",
        ],
        "scenes": [
            ("인사 (인트로) · 햇살 사과 과수원에서 빼꼼", "cheerful friendly expression",
             "popping up cheerfully and waving one paw hello in a sunny pastel apple orchard, a round tree with red apples behind, bright warm sunny mood"),
            ("여섯 · 바구니의 사과 가리키기", "delighted counting expression",
             "happily pointing one paw at a small woven basket filled with round red apples on soft green grass, cheerful counting mood"),
            ("일곱 · 나무 탁자에 사과 한 줄", "joyful counting expression",
             "carefully placing round red apples in a neat row on a warm wooden table, looking focused and happy, cozy bright mood"),
            ("여덟 · 나무 상자에 사과 가득", "delighted happy expression",
             "holding up a round red apple beside a wooden crate brimming with more round red apples, cheerful proud mood"),
            ("아홉 · 사과나무 가지에 손 뻗기", "excited cheerful expression",
             "reaching one paw up toward a low pastel apple-tree branch heavy with round red apples, sunny garden mood"),
            ("열 · 큰 바구니 한가득 사과 안기", "joyful delighted expression",
             "hugging a big basket overflowing with lots of round red apples, beaming with delight, warm sunny mood"),
            ("리캡 (6~10) · 사과에 둘러싸여 박수", "proud happy clapping expression",
             "clapping its paws happily while sitting surrounded by many round red apples in a cheerful sunny pastel orchard, celebratory warm mood"),
        ],
    },
}


def build_number(cur, series, item, idx):
    rng = item["range"]
    obj = item.get("obj", cur["recipes"]["number"].get("count_object", "별"))
    pack = NUMBER_SCENE_PACKS.get(rng)
    if not pack:
        sys.exit(f"❌ 숫자 '{rng}' SCENE_PACK 없음 — NUMBER_SCENE_PACKS 에 추가(narration 7줄 + scenes 7).")
    meta_root = cur["_meta"]
    n1, n5 = item["n1"], item["n5"]
    words = [item["n1_word"], item["n2_word"], item["n3_word"], item["n4_word"], item["n5_word"]]
    slug = f"{datetime.datetime.now().strftime('%Y%m%d%H%M')}_mascot_num{n1}{n5}"

    meta = {
        "slug": slug, "format": "narration_short", "track": "kids_edu",
        "channel": meta_root["channel"],
        "mascot": "토리 — 둥근 크림빛 아기 고양이 (캐러멜 귀·꼬리, 큰 호박색 눈)",
        "learning_objective": f"숫자 세기 {rng} — {obj}{eul(obj)} {n1}~{n5}개 세며 수 개념·수사({words[0]}~{words[4]}) 익히기",
        "target_duration_sec": 40,
        "narration_tone": "패런티즈(과장 노래조) · 또렷하고 즐겁게 · 유아 대상 · 1:1 탭 카운트",
        "image_backend": "fal.ai FLUX schnell (--style cute)",
        "core_identity": f"토리가 {obj}{eul(obj)} 하나씩 세며 {rng} 숫자와 수사를 익힌다. 큰 숫자 오버레이로 수를 명확히. 숫자 세기 시리즈.",
        "made_for_kids": True, "characters": ["토리(마스코트 고양이)"], "bgm_mood": "위안",
        "series": f"숫자 세기 — {rng}",
        "subtitle_note": f"큰 숫자({n1}~{n5})·수사는 compose 후 overlay_kids_letters로 상단 번인(_edu_overlay.json). fal 이미지엔 글자 그리지 않음(no text).",
        "safety": "아동용. 실명·로고·브랜드 없음. 차분한 페이스. 학습목표 명시·토리 일관·앞 편과 장면 변주. FLUX 개수 부정확 → 수 학습은 오버레이 담당.",
    }
    narration = "".join(f"S{i:02d} {ln}\n" for i, ln in enumerate(pack["lines"], 1))

    bgs = " / ".join(s[0].split("·")[-1].strip() for s in pack["scenes"])
    head = (
        f"# 08 IMAGE PROMPTS — 토리랑 숫자: {rng} ({slug.split('_', 1)[1]})\n\n"
        f"- **slug**: {slug} · 7 stills · fal.ai FLUX schnell (`--style cute`) · 파스텔 동화풍 · no-text\n"
        f"- 마스코트 **토리**(MASCOT 블록)은 매 비트 그대로 복붙(일관성=필수). 장면·배경은 앞 편과 겹치지 않게. 본 편 배경={bgs}.\n"
        f"- ★ 숫자·{obj} 개수는 **큰 글자 오버레이가 담당** → fal 이미지엔 글자 절대 그리지 않음(no text). "
        f"⚠️ 모델이 개수를 정확히 못 그릴 수 있어 '여러 개 {obj}'로 충분.\n\n"
        f"> MASCOT = {MASCOT}, cheerful friendly expression.\n\n---\n\n"
    )
    blocks = []
    for i, (label, expr, action) in enumerate(pack["scenes"], 1):
        blocks.append(f"## B{i:02d}  (S{i:02d})  — {label}\nMASCOT ({MASCOT}, {expr}) {action}. {SUFFIX}\n")
    image_prompts = head + "\n".join(blocks) + "\n"

    recipe = cur["recipes"]["number"]
    subs = {"range": rng}
    for k in ("n1", "n1_word", "n2", "n2_word", "n3", "n3_word", "n4", "n4_word", "n5", "n5_word"):
        subs[k] = item[k]
    overlay = render_overlay(recipe, subs)
    beat_map = {str(i): [i] for i in range(1, recipe["beats"] + 1)}

    return slug, {
        "00_meta.json": meta,
        "02_step3_narration.txt": narration,
        "08_image_prompts.md": image_prompts,
        "_edu_overlay.json": overlay,
        "_beat_map.json": beat_map,
        "_clips.json": {"clips": []},
    }


def save_curriculum_produced(cur, item, slug):
    """스캐폴드 직후 커리큘럼 item을 produced로 자동 마킹 → 같은 자모 재스캐폴드 방지.
    이전엔 사람이 curriculum.json을 손으로 편집해야 했다(2026-06-24 박제)."""
    item["status"] = "produced"
    item["production_dir"] = slug
    with open(CURRICULUM, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_files(slug, files, dry_run):
    prod = os.path.join(PRODUCTIONS, slug)
    if not dry_run:
        os.makedirs(os.path.join(prod, "flow_images"), exist_ok=True)
    for fname, content in files.items():
        path = os.path.join(prod, fname)
        if isinstance(content, str):
            blob = content
        else:
            blob = json.dumps(content, ensure_ascii=False, indent=2) + "\n"
        if dry_run:
            print(f"\n----- {fname} -----\n{blob}")
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(blob)
    return prod


def main():
    ap = argparse.ArgumentParser(description="키즈 채널 키즈 에피소드 자동 스캐폴더")
    ap.add_argument("series", help="curriculum series key (예: hangul_consonants)")
    ap.add_argument("selector", help="letter(예: ㄹ) 또는 1-based index")
    ap.add_argument("--dry-run", action="store_true", help="파일 쓰지 않고 출력만")
    a = ap.parse_args()

    cur = load_curriculum()
    series, item, idx = find_item(cur, a.series, a.selector)

    if item.get("status") == "produced":
        sys.exit(f"❌ '{a.selector}' 는 이미 제작됨(production_dir={item.get('production_dir')}). 재생성 금지.")

    recipe_key = series.get("recipe")
    if recipe_key == "consonant":
        slug, files = build_consonant(cur, series, item, idx)
    elif recipe_key == "number":
        slug, files = build_number(cur, series, item, idx)
    else:
        sys.exit(f"❌ consonant·number recipe만 지원합니다(요청: {recipe_key}). vowel/word 는 추후 확장.")
    prod = write_files(slug, files, a.dry_run)

    if a.dry_run:
        print(f"\n[dry-run] 슬러그={slug} — 파일 미생성.")
        return

    save_curriculum_produced(cur, item, slug)   # ★재스캐폴드 방지: 커리큘럼 자동 produced (2026-06-24)
    print(f"✅ 스캐폴드 생성: productions/{slug}/")
    for fn in files:
        print(f"   · {fn}")
    print(f"   · curriculum.json → '{a.selector}' status=produced (production_dir={slug})")
    print("\n다음 파이프라인 (순서대로, 비용 발생):")
    print(f"  1) .venv/bin/python scripts/generate_images_fal.py --production {slug} --style cute")
    print(f"  2) .venv/bin/python scripts/generate_narration_fish.py {slug}")
    print(f"  3) .venv/bin/python scripts/compose_narration.py {slug}        # track=kids_edu → 큰글자 자동 번인")
    print(f"  4) python scripts/check_kids_prompt_variety.py {slug}          # 장면 Jaccard<0.5 검증")
    print(f"  5) python scripts/check_black_frames.py {slug}                 # fal 검은이미지 가드(compose 전)")
    print(f"  5b) python scripts/verify_images.py --production {slug} --no-vision   # (옵션)무료 QC. 마스코트 일관 더 보려면 --no-vision 빼고 비전")
    print(f"  6) (게시 준비 끝나면) .venv/bin/python scripts/prep_upload.py {slug}   # Finder reveal + 캡션 복사 .command")
    print(f"\n⚠️ fal 실행 전 08_image_prompts.md 의 장면이 앞 편과 진짜 다른지 눈으로 한 번 확인(텍스트 수정은 무료).")


if __name__ == "__main__":
    main()
