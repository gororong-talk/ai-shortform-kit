---
name: wisdom
description: 명언/지혜 텍스트 콘텐츠 種 (사연과 별개 트랙). 위인·책 현자·성경·불교 명언을 데이터화(wisdom_library.db) → "아주 간단한 텍스트인데 흡입력 있고 오래 보게 되는" 미니멀 타이포 결과물 양산. 정적 카드 PNG(9:16 Shorts·4:5 IG캐러셀) + 미니멀 텍스트 영상(검은화면→명언 페이드인→저자 reveal→느린 줌) + 명상형 컴필레이션. 비용 0원(로컬 Pillow+ffmpeg). 사용자가 "/wisdom", "명언", "지혜 카드", "명언 영상", "명언 카드 만들어", "위인 명언", "성경 구절 카드", "명상 영상" 같은 표현 사용 시 호출.
---

# /wisdom — 명언 텍스트 카드/영상

사연(스토리→웹툰영상)과 **다른 콘텐츠 種**. 인물·이미지 없이 **텍스트만**으로,
"아주 간단하지만 흡입력 있고 오래 보게 되는" 결과물을 비용 0원으로 양산한다.

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `scripts/wisdom_db.py` | 데이터 레이어 — 시드 JSONL → `wisdom_library.db`(quotes 테이블) 적재·쿼리 |
| `scripts/wisdom_render.py` | ⭐ 렌더러 — 주제 영상 + 카드 PNG + 컴필레이션 (Pillow+ffmpeg) |
| `data/wisdom/seed_quotes.jsonl` | 시드 명언집 (7갈래: 스토아·동양고전·서양철학·문학·성경·불교·위인) |
| `data/wisdom/themes.json` | 주제 인덱스(미리보기/실험용 — 게시 아님). 주제→글 매칭규칙(태그+키워드) |
| `scripts/wisdom_bgm.py` | mood별 앰비언트 BGM 생성 + 영상에 입히기 (procedural 기본 / ACE 옵션) |

## 데이터 포맷 (JSONL 한 줄 = 명언 한 건)

```json
{"id":"sto_001","text":"한국어 표시 텍스트","author":"세네카","source":"출처(작품/장:절)",
 "orig":"원문(한문/원어, 없으면 \"\")","tradition":"스토아|동양고전|서양철학|문학|성경|불교|위인",
 "theme":["시간","유한성"],"mood":"평온|각성|단호|위안|경건",
 "lang_orig":"la|grc|zh|pli|he|en|de|fr|ru|ko",
 "license":"public_domain|scripture_ref|fair_use_short","verified":1,"note":""}
```

- **mood** 가 렌더 팔레트를 결정 (평온=세이지/각성=골드/단호=레드/위안=앰버/경건=블루, 모두 다크).
- **license/verified** 는 저작권·출처 정직성 장치. 고대·공개(public_domain) 우선, 근현대 책은 **짧게·출처표기(fair_use_short)**, 성경은 **구절 출처(scripture_ref)**. 출처 미확인은 `verified:0`.
- 외부 크롤/수집 도구가 같은 포맷으로 떨어뜨리면 그대로 `ingest` (사연 /ingest-stories 와 동일 패턴).

## ⛔ 게시 표준 (불변·2026-06-25 사용자 정정) — 명언 채널 = **영상 1편 = 명언 1개 · ≤15초**

채널명 그대로 **명언 채널(=명언 1개)**. 게시 8건 전부 단건이고 코드도 `MAX_VIDEO_SEC=15`("1편=1명언")로
박혀 있다. **게시는 단건 렌더(`--id`/`--fresh`/`--random`)만.** 아래 '주제 컴필레이션'(여러 글·1~3분)은
**미리보기/실험용일 뿐 이 채널 게시 대상이 아니다.** 생성 후 `scripts/wisdom_publish_guard.py`(prep_upload·
> ⚠️ 2026-06-25 실수: 이 스킬이 "제작 단위=주제"라고 적혀 있어 9편·1:30 컴필레이션을 만들어 게시 단계까지 갔다.
> 그건 틀렸다 — 표준은 단건 ≤15s. (재고확충으로 라이브러리를 늘리는 건 여전히 유효: 단건 후보가 풍부해진다.)

## 주제 컴필레이션 (미리보기/실험 — 게시 대상 아님)

영상 한 편 = **주제 하나** + 그 주제에 맞는 **글 전부**. 데이터가 늘면 더 풍부해지지만 **길어서 채널 표준(≤15s)
위반** → 게시 안 함. 톤/구성 미리보기나 다른 포맷 실험용으로만 사용.

### 주제 레지스트리 포맷 (`data/wisdom/themes.json` 한 줄 = 주제 하나)
```json
{"id":"time","title":"시간","subtitle":"흘러가는 모든 것에 대하여","mood":"각성",
 "match":{"themes":["시간","유한성"],"keywords":["시간","세월","순간"]}}
```
- 한 글이 `match.themes`(태그) **또는** `match.keywords`(본문/출처/원문 포함) 중 하나라도 걸리면 그 주제에 편입.
- ⚠️ **키워드 오탐 주의**: 너무 짧은 글자("공"이 "위령공", "변"이 "변명"에 걸림)는 빼고 **태그 우선**. 새 주제 추가 후 반드시 `--list-themes` 로 매칭 글을 눈으로 검수.
- 한 글이 여러 주제에 동시 편입 가능(시간↔죽음↔현재 겹침) — 자연스럽다.

### 주제 영상 만들기
```bash
.venv/bin/python scripts/wisdom_render.py --list-themes          # 주제별 매칭 글 수 미리보기·검수
.venv/bin/python scripts/wisdom_render.py --theme-id adversity   # '고난' 1편 (매칭 글 전부)
.venv/bin/python scripts/wisdom_render.py --all-themes           # 모든 주제 일괄 (팩토리)
```
구조: **오프닝 타이틀 카드**(주제명+부제+편수) → 매칭된 글 전부(흐름순: 위인→스토아→서양→동양→불교→성경→문학) → **클로징**. 출력 `wisdom_out/themes/<id>.mp4`.

## 워크플로우 (단건/배치)

### 1) 데이터 적재 (최초 1회 / 신규 명언 추가 시)
```bash
.venv/bin/python scripts/wisdom_db.py init
.venv/bin/python scripts/wisdom_db.py ingest data/wisdom/seed_quotes.jsonl
.venv/bin/python scripts/wisdom_db.py stats        # 갈래·mood 분포 + verified 비율
```
> `wisdom_library.db` 는 JSONL 에서 **언제든 재생성** → git 제외(.gitignore). 진실의 원천 = JSONL.

### 2) 단일 명언 → 카드 + 영상
```bash
.venv/bin/python scripts/wisdom_render.py --id sto_002              # 카드(9:16,4:5) + 영상
.venv/bin/python scripts/wisdom_render.py --id bud_001 --no-video   # 카드만 (영상이 아닌 텍스트)
```
산출: `wisdom_out/<id>/card_9x16.png` · `card_4x5.png` · `video.mp4`

### 3) 컴필레이션 (가장 "오래 보게 되는" 포맷 — 명상형 1~3분)
```bash
.venv/bin/python scripts/wisdom_render.py --compile 5 --mood 평온 --out wisdom_out/_calm5.mp4
.venv/bin/python scripts/wisdom_render.py --compile 8 --tradition 불교 --out wisdom_out/_zen8.mp4
```

### 4) 무작위 배치
```bash
.venv/bin/python scripts/wisdom_render.py --random 5 --theme 시간
```

### 5) BGM (주제 mood별 배경음)
mood별 앰비언트 패드를 만들어 영상에 입힌다. `scripts/wisdom_bgm.py`.
```bash
.venv/bin/python scripts/wisdom_bgm.py --gen                # 5 mood 패드 생성 (procedural, 즉시·₩0)
.venv/bin/python scripts/wisdom_bgm.py --mux-themes         # wisdom_out/themes/*.mp4 에 mood BGM 입힘
# 또는 렌더 시 한 번에:
.venv/bin/python scripts/wisdom_render.py --all-themes --auto-bgm
```
- **procedural(기본)** = ffmpeg 사인톤 화음 패드. 즉시·₩0·**보컬 0 보장**(instrumental 확실). mood별 화음: 평온=C major / 각성=Dsus / 단호=A minor / 위안=F major / 경건=완전5도. 레벨 ~−24dB(배경).
- **ace(옵션)** `--backend ace` = ACE Step v1.5 로 더 리치한 음악. ⚠️ 노래 모델이라 **보컬 누수 가능 + 느림(~6분/30초)** → 생성 후 귀로 확인 필수.
- 단건: `--bgm <mp3>` 로 직접 지정도 가능. BGM 파일은 `*.mp3` 라 git 제외(JSONL/코드처럼 재생성).

## 영상 연출 (흡입력 + 오래 보게 되는 장치)

1. 검은 화면 → 명언 **페이드인** (1단계: 저자 없음)
2. 읽고 음미하도록 **머무름** (읽기 속도 기반 자동 hold)
3. **저자 reveal** (xfade) — "누가 한 말일까?" 호기심 페이로프, 명언 위치는 고정(점프 없음)
4. 전체에 **아주 느린 줌**(zoompan 1.0→1.085) + 비네트 → 정적이지만 살아 있음
5. 끝 프레임 ≈ 깨끗한 카드 → **루프** 자연스러움 (TikTok 루프 보상)

## 게시 (채널 명언 채널 @your_wisdom_channel — YT Shorts + IG Reels)

- **⛔ 게시 표준 = 단건 ≤15초** (위 섹션). 게시 전 `wisdom_publish_guard` 가 자동 검증 — 컴필레이션·15s초과는 차단.
- **채널**: 명언 채널 (@your_wisdom_channel, channel_id `UC_YOUR_CHANNEL_ID`). **개인 Chrome**에 IG/YT 로그인(사연=brave와 구분 — 게시 전 활성계정 검증 필수).
- **★ `_pubmeta.json` 자동 생성**: `wisdom_render`가 렌더 시 `wisdom_out/<id>/_pubmeta.json`을 **자동 작성**(채널·AI OFF·FB OFF·플랫폼별 캡션, 해시태그 5). → **게시(수동)가 이걸 그대로 읽어 데이터 구동** (캡션 수동작성 불요).
- **AI 라벨 = OFF**(명언=타이포, 생성이미지 아님 — 사연/키즈 fal과 다름). **IG FB토글 OFF**. TikTok 신규계정은 게시 후 '나만' 자동잠금→'모두' 전환.
- 카드 PNG → IG 피드/캐러셀(4:5)·스토리. 영상 MP4 → YT Shorts/TikTok/IG Reels(9:16). 파일드롭=사용자.
- 데뷔: 세네카 sto_002(2026-06-16, TikTok+IG). 자세히 → 메모리 [[upload-automation]].

## 저작권 가드 (지킬 것)

- 고대/공개 출처(논어·도덕경·명상록·법구경·성경 구절 등) 우선 — public_domain.
- 근현대 책 인용은 **한 문장 이내·저자/작품 표기** (fair_use_short). 장문 복원 금지.
- **오귀속 주의**: "내일 죽을 것처럼 살라"(간디) 등 출처 불명 인기 명언은 넣지 말 것. 시드 제작 시 실제 출처 추적, 불명은 `verified:0`.
- 가사(노래)는 어떤 형태로도 넣지 않는다.

## 확장 (펜딩)

- 데이터 더 모으기(목표=갈래별 50+). 외부 LLM 으로 후보 생성 시 **출처 교차검증 필수**(오귀속 차단).
- 폰트 변주(경건=더 클래식한 명조), 컬러 테마 추가, 오프닝 인용부호 옵션(`--ornament`은 현재 미구현, 필요 시 추가).
- 시리즈화: "스토아 7일", "잠언 한 절" 등 테마 컴필레이션 정기 발행.
