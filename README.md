# AI 숏폼 제작 파이프라인 — 예제 저장소

누구나 무료로 볼 수 있는 공개 저장소입니다. 전자책 「AI 숏폼 제작 일지와 시행착오」에 나오는 파이프라인의 실제 코드입니다.
사연 한 편을 **대본 → 그림 → 나레이션 → 자막 영상 → 업로드 문구**까지 만듭니다.

> 이용 조건은 `LICENSE`를 보세요 — 개인·상업 목적의 사용·수정은 자유이고, 이 코드 자체를 판매하거나 유료 상품에 넣어 배포하는 것은 금지입니다.
> 게시(업로드)는 이 저장소에 없습니다 — 만든 영상은 직접 올리거나 별도 게시 프로그램을 쓰세요.

---

## 1. 준비물

| 항목 | 설명 |
|---|---|
| macOS 또는 Linux | 저자는 macOS(Apple Silicon)에서 사용. Windows는 WSL 권장(미검증) |
| Python 3.11 | `python3 --version`으로 확인 |
| ffmpeg | 영상 합성·자막. macOS: `brew install ffmpeg` |
| 한국어 폰트 | 자막용. 설치된 한국어 폰트 중에서 자동 선택(`fc-list :lang=ko`로 확인). 없으면 나눔 폰트 등을 설치 |
| fal.ai 키 | 그림 생성. 선불 충전 종량제 |
| Fish Audio 키 | 나레이션. 종량제 |
| (권장) Claude Code | 대본 작성·채점을 스킬로 진행. 없으면 대본은 직접 쓰면 됩니다 |

한 편 비용(6컷 기준, 2026년 하반기 — 전자책 7장 비용표와 같음): 그림 약 300~1,700원(모델에 따라, 손그림 `doodle_kit`이면 0원) + 나레이션 수십 원. 합성은 무료.

> 이 README의 ②·④~⑦은 깨끗한 환경(새 venv + `requirements.txt`)에서 그대로 실행해 확인했습니다(2026-11-17, macOS). ②·③ 그림 생성과 ⑤ 유료 TTS는 비용 때문에 시험하지 않았습니다.

## 2. 설치

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env          # FAL_KEY, FISH_API_KEY 채우기
# 선택: 손그림 스타일(doodle_kit)을 쓸 때만
.venv/bin/python -m playwright install chromium
```

## 3. 폴더 구조

```
scripts/               파이프라인 스크립트
.claude/skills/        Claude Code 스킬 (/produce-sayeon 등)
productions/<slug>/    한 편 = 한 폴더 (입력 파일 + 생성물)
data/                  TTS 보이스 목록, 명언 시드 데이터
docs/                  제작 매뉴얼, 실패 사례 모음, 캐릭터 일관성 가이드
story_engine/          롱폼 드라마 세계관 예시(창작)
```

한 편 폴더의 파일 (번호 = 만드는 순서):

| 파일 | 내용 | 누가 만드나 |
|---|---|---|
| `00_meta.json` | 핵심 설정·훅·인물·안전 점검 | 사람/Claude |
| `02_step3_narration.txt` | 나레이션 대본 (`S01  대사` 한 줄 = 자막 한 줄) | 사람/Claude |
| `08_image_prompts.md` | 장면별 그림 프롬프트 (`## B01 ...`) | 사람/Claude |
| `_beat_map.json` | 대본 줄 → 그림 번호 매핑. **키는 줄 번호 `"1"`, `"2"`…** | 사람/Claude |
| `_clips.json` | 움직이는 클립 목록 (보통 `{"clips": []}`) | 사람 |
| `flow_images/B##.png` | 장면 그림 | `generate_images_fal.py` |
| `03_audio_narration_only.mp3`, `04_timing.json` | 나레이션과 줄별 시간 | `generate_narration_fish.py` |
| `06_render_v1.mp4` | 완성 영상 | `compose_narration.py` |
| `07_upload_meta.md` → `_pubmeta.json` | 플랫폼별 제목·캡션 | 사람/Claude → `parse_upload_meta.py` |

## 4. 첫 편 만들기 — 예시로 따라 하기

`productions/<예시_production>/` 에 **입력 파일이 다 들어 있는 창작 예시**가 있습니다.
구성은 저자 채널에서 조회수가 가장 높았던 편의 구조를 그대로 따랐고, 내용은 새로 썼습니다.
(구조 설명 = `02_step3_narration.txt` 하단 "검증 메모")

```bash
SLUG=202611170000_example_talk_hijack

# ① 그림 계획 확인 (API 호출 없음, 무료)
.venv/bin/python scripts/generate_images_fal.py --production $SLUG --dry-run

# ② 인물 레퍼런스 1장씩 — 얼굴을 컷마다 고정하는 기준. 깨끗할 때까지 다시 뽑는 게 제일 싸다
.venv/bin/python scripts/generate_images_fal.py --production $SLUG \
  --prompt "front-facing waist-up character reference portrait of NARRATOR, Korean woman in her early 30s, long straight black hair in a low ponytail, dusty-rose pink knit sweater, gentle face, hands out of frame, plain background, single character, centered" \
  --out flow_images/_ref_narrator.png
.venv/bin/python scripts/generate_images_fal.py --production $SLUG \
  --prompt "front-facing waist-up character reference portrait of HUSBAND, Korean man in his early 30s, short wavy brown hair, no glasses, navy blue hoodie, friendly face, hands out of frame, plain background, single character, centered" \
  --out flow_images/_ref_husband.png

# ③ 장면 그림 10장 (레퍼런스 고정)
.venv/bin/python scripts/generate_images_fal.py --production $SLUG --flux2 \
  --ref narrator=flow_images/_ref_narrator.png --ref husband=flow_images/_ref_husband.png

# ④ 검수 — 검은 화면 자동 검사 + 사람이 눈으로 (명찰·소품의 가짜 글자, 손, 얼굴)
.venv/bin/python scripts/check_black_frames.py $SLUG
#    이상한 컷만 다시: --only 4,7

# ⑤ 나레이션 + 줄별 타이밍
.venv/bin/python scripts/generate_narration_fish.py $SLUG
#    키 없이 먼저 돌려보려면 무료 TTS: scripts/generate_narration_edge.py $SLUG
#    (단, 무료 음성은 느리게 읽어 이 예시가 약 124초 — 유료는 약 90초 목표)

# ⑥ 영상 합성 (천천히 확대되는 효과 포함)
.venv/bin/python scripts/compose_narration.py $SLUG --kenburns

# ⑦ 업로드 문구 → 구조화 + 게시 전 점검 (그림을 고친 뒤 재합성을 안 했으면 여기서 멈춘다)
.venv/bin/python scripts/parse_upload_meta.py $SLUG
.venv/bin/python scripts/prep_upload.py $SLUG --no-open
```

Claude Code가 있다면 위 과정을 한 번에: 저장소 폴더에서 `claude` 실행 → `/produce-sayeon`.

## 5. 내 사연으로 만들기

1. `productions/<날짜시각>_<영문이름>/` 폴더를 새로 만든다 (예: `202612011200_my_story`).
2. 예시 폴더의 `00_meta.json`·`02_step3_narration.txt`·`08_image_prompts.md`·`_beat_map.json`·`_clips.json`·`07_upload_meta.md`를 복사해 내용만 바꾼다.
3. 4장의 ①~⑦을 `SLUG`만 바꿔 실행한다.

**소재 주의**: 다른 사람이 쓴 글을 소재로 쓰려면 저작권과 해당 사이트 이용약관을 먼저 확인하세요. 실명·지명·브랜드는 일반명사로 바꿉니다.

## 6. 막혔을 때

- `docs/FAILURE_CASES.md` — 겪은 실패와 해법 모음 (전자책 3장의 원자료)
- `docs/CHARACTER_CONSISTENCY.md` — 얼굴이 컷마다 바뀔 때
- `docs/PRODUCTION_PLAYBOOK.md` — 전체 제작 절차
- 자주 나는 것:
  - `⛔ _beat_map.json 에 라인번호 키 없음` → 키를 `"S01"`이 아니라 `"1"`로
  - `⛔ stale 렌더` → 그림·음성을 고친 뒤 ⑥을 다시 실행
  - 그림 생성이 콘텐츠 필터에 걸림 → 같은 프롬프트 재시도 → 단어 완화 → `--flux2` 없이 생성
  - 그림에 안경·글자가 자꾸 생김 → "~하지 마" 대신 원하는 상태만 적기

## 7. 전자책 장별 대응

| 전자책 | 이 저장소 |
|---|---|
| 2장 파이프라인 | 4장의 ①~⑦ |
| 3장 시행착오 (재현·테스트) | 각 사례의 "가드의 실체"에 나온 스크립트 |
| 6장 체크리스트 | `docs/PRODUCTION_PLAYBOOK.md`, `prep_upload.py`의 점검 |

## 8. 채널 설정

`scripts/parse_upload_meta.py` 상단의 채널 표에서 `@your_story_channel` 등을 내 채널 핸들과 ID로 바꾸세요.
명언·키즈 트랙도 같은 방식입니다(`wisdom_render.py`, `wisdom_publish_guard.py`).
