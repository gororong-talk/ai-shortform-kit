# 🎭 인물 캐릭터 일관성 프로세스 (다중컷 사연)

> 2026-06-21 정립·실검증. 문제: elder_love(노부부)에서 두 주인공 **얼굴이 비트마다 바뀌고, 가디건 색이 핑크↔보라로 흔들리고, 손/반지가 기괴**했음. 원인 = produce-sayeon/fal 경로가 **text-only(레퍼런스 없음)** + FLUX는 매 컷 독립생성이라 얼굴을 못 잡음 + 손/반지는 FLUX 최악 약점.

## 핵심 원리 (왜 text-only가 실패하나)
- FLUX(schnell/dev)는 **이미지 레퍼런스를 못 받는다**(텍스트→이미지). 같은 외형 텍스트를 매 비트 복붙해도 얼굴은 매번 새로 굴러 **드리프트**.
- FLUX는 **guidance-distilled → negative 프롬프트를 무시**. "NOT photorealistic" 같은 건 오히려 그 단어를 그리라고 주입. **모든 제약은 positive로.**
- **손·손가락·반지·작은 텍스트 = FLUX 고질 약점.** 손 클로즈업·반지 디테일을 요청하면 거의 항상 기괴(공중부양 반지·6손가락).

## 해법 = 레퍼런스 잠금 (fal-ai/flux-pro/kontext)
레퍼런스 1장을 주고 매 비트를 "같은 인물, 새 장면"으로 **편집**(Kontext)하면 얼굴·헤어·의상이 유지된다. `generate_images_fal.py`에 `--ref` 모드로 구현됨(2026-06-21).

## 표준 절차 (인물이 여러 컷 등장하는 사연)

### 1) 캐릭터 스펙 = 구체적 (모호한 색 금지)
- ❌ "soft-lavender"(모델이 핑크/보라 제각각) → ✅ **"dusty rose pink"** 처럼 한 단어로 못박는다.
- 역할 토큰을 대문자로 고정: `GRANDPA` `GRANDMA` `NARRATOR` (08 시트·--ref 키와 일치).

### 2) 역할별 레퍼런스 1장 생성 (schnell, 깨끗할 때까지 재추첨)
```bash
.venv/bin/python scripts/generate_images_fal.py --production <slug> \
  --prompt "front-facing waist-up character reference portrait of ROLE, <구체 외형>, \
            calm expression, hands out of frame, plain soft background, single character, centered" \
  --out flow_images/_ref_<role>.png
```
⚠️ **레퍼런스가 전체를 좌우** — 손 프레임밖·정면·깨끗한 얼굴이 나올 때까지 다시 생성. 나쁜 레퍼런스 = 전 비트 오염.

### 3) 08_image_prompts.md = 짧은 레퍼런스-일치 식별자 + 장면 (★핵심 규칙)
각 비트 프롬프트 = **역할 토큰 + 짧은 식별자(핵심특징+위치) + 동작 + 배경.**
- ✅ `GRANDPA (white hair, BEIGE cardigan, on the LEFT) and GRANDMA (grey hair, glasses, DUSTY ROSE PINK cardigan, on the RIGHT) sitting side by side ...`
- ❌ **풀 외형블록 재기술** → 레퍼런스(핑크)와 텍스트(lavender)가 **충돌 → 색 드리프트**.
- ❌ **외형 0(장면만)** → 멀티 레퍼런스가 두 인물을 **병합**(할아버지가 할머니 핑크를 입음).
- 식별자는 **반드시 레퍼런스와 일치**(beige=beige, pink=pink). 위치(LEFT/RIGHT)로 2인 구분.

### 4) 생성 = --ref 로 Kontext 잠금
```bash
.venv/bin/python scripts/generate_images_fal.py --production <slug> \
  --ref grandpa=flow_images/_ref_grandpa.png \
  --ref grandma=flow_images/_ref_grandma.png \
  --ref narrator=flow_images/_ref_narrator.png
```
- 비트 프롬프트에 등장하는 ROLE → 그 레퍼런스로 Kontext 편집(2인↑=kontext multi). ROLE 없는 비트(사물·배경)=schnell.
- 비용: 인물 비트 ~₩54(single)/₩108(multi), 사물 비트 ~₩12. 10비트 인물 사연 ≈ ₩600~1000.

### 5) 손/반지/소품 = FLUX 약점 회피 (프롬프트 관리)
- **손은 프레임 밖 / 테이블 위에 단순히 / 주머니에.** "hands resting simply and out of focus", "hands out of frame".
- **반지·보석·시계 클로즈업 절대 금지.** 결혼반지 서사가 필요하면 클로즈업 대신 투샷·소품(액자)으로 암시.
- 가방·소품 일관: 레퍼런스에 들리면 식별자에 포함("holding a brown handbag"), 아니면 빼서 매번 안 바뀌게.
- 이 가드는 `generate_images_fal.py` WEBTOON_PREFIX 에 내장됨(positive). 추가로 08에 PLAYBOOK §7.5(`EXACTLY TWO HANDS belonging to the SAME person`) 적용.

### 6) 검증 (필수 — 자율생성 시 사람이 못 보므로 더 중요)
- 인물 핵심 비트(투샷·클로즈업) 프레임을 **눈으로 비교**: 얼굴·헤어·의상 색이 비트 간/레퍼런스와 일치하나.
- `scripts/check_black_frames.py`로 검은 이미지 가드도 같이.

## elder_love 실검증 결과 (before→after)
- before(text-only): 할아버지 얼굴 비트마다 다름, 할머니 핑크↔보라, B08 손/반지 공중부양.
- after(레퍼런스 잠금): 할아버지 흰머리+베이지 일관 / 할머니 회색머리+핑크+안경 일관 / B08은 손 클로즈업을 투샷으로 교체해 손 정상. 레퍼런스=`flow_images/_ref_*.png`, 백업=`flow_images/_inconsistent_v1/`.

## 자체검증(QC) 자동화 — `scripts/verify_images.py` (2026-06-21 빌드·검증)

**"자율생성 시 자체검증 에이전트가 필요한가?" → YES(검증됨).** 레퍼런스 잠금으로 실패를 줄여도 FLUX는 확률적이라 가끔 실패한다(색 드리프트·떠있는 반지·식별자 누출). 자율진행은 사람이 매 컷을 못 보므로 **자동 QC가 안전망**. "검증을 회피?" → **완전 회피 불가**(예방은 빈도만 낮춤). 정답 = **검증을 자동화**.

3중 레이어(싼 것부터): ① black-frame(ffmpeg, 무료) ② OCR(tesseract, `--no-vision` 시 텍스트 1차) ③ **비전 LLM 판정**(Anthropic vision, 레퍼런스 대비 얼굴/색/손/떠있는물체/정체성). 출력=불량 비트 + `--only` 재생성 권장.

**실검증(elder_love before/after 혼동행렬)**: 불량 3/3 검출(B04 색·B07 색/안경·B08 떠있는반지+기형손), 정상 통과, **사람이 놓친 잔존결함(할아버지 안경)까지 검출**. 루브릭 보정 = 명확한 결함만 high(사소한 안경 프레임 모양·포즈 변이는 통과). 파싱 실패는 무음통과 금지(low로 표면화).

**자율 루프(생성→검증→재생성)**: 자율 파이프라인은 생성 직후 반드시
```bash
.venv/bin/python scripts/verify_images.py --production <slug>          # 레퍼런스/역할 자동 인식, 비전 QC
# high 나오면 → generate_images_fal --only <비트> --ref ... 재생성 → verify_images 재실행(1~2회)
```
비용 ~$0.01-0.02/컷(sonnet). 키즈 마스코트처럼 단순하면 `--no-vision`(무료 ①②)만으로도 충분. 검은이미지는 `check_black_frames.py`(동일 ① 레이어 단독).

> ⚠️ **함정·수정 (2026-06-23, cafe_farewell)**: 비전 QC 루브릭이 *읽을 수 있는* 텍스트만 high로 잡아서 **배경 간판/건물 외벽의 '가짜 글자(garbled glyph)'를 통과**시켰다(B13 빈소 건물·B06 창문 간판). FLUX는 평면(간판·외벽·창문)이 있으면 'no text'를 무시하고 깨진 글자를 박는다. **수정**: `verify_images.py` RUBRIC에 "읽히지 않는 가짜/깨진 글자도 HIGH, 배경까지 스캔"을 명시(반영됨 → 즉시 B06 추가 검출). **예방(프롬프트·최우선)**: 인물 비트 배경은 평면을 주지 말 것 — 빈소/길거리/창문 같은 비트는 **흐린 보케 배경·평면 단색 벽·인물 클로즈업**으로(글자 박을 표면 제거). 빈소는 흰 국화·은은한 빛만, 건물 외벽 금지.
>
> **살리기(이미 박힌 경우) = `scripts/scrub_text.py` (재생성 없이)**:
> - **A. ₩0 국소 처리**(`--method blur|clone`): vision으로 글자 bbox 검출 → 블러/클론. 단 **vision 좌표가 부정확**해 자동 박스가 글자를 빗나가기 쉽다(실측 y 15~20% 오차). 보케/가장자리·**수동 `--box`로 정확히 잡을 때만 신뢰**. clone은 박스 부정확 시 글자를 복제하므로 auto=blur(opt-in clone).
> - **B. fal 인페인트**(`--inpaint`, 소액 유료): 마스크 영역 재생성. ⚠️ **"배경 그대로 채워라"는 실패**(FLUX Fill도 건물 평면에 가짜글자 재생성). ✅ **"보케/하늘/단색으로 REPLACE하라" + 넉넉한 마스크**면 깔끔히 사라짐(실증). 기본 프롬프트가 이 recipe로 박혀 있음.
> - 결론: **예방 >> 살리기.** 살릴 땐 B(표면 교체) > A. 구조적 간판/외벽은 A의 블러는 띠가 남고 clone은 위험.

## 모델 선택 (사연 인물) — ★기본 = all-FLUX.2 (2026-06-21 A/B 결정)

**사연(인물 사연)은 `generate_images_fal.py --flux2`(all-FLUX.2) 가 기본.** parents_day(all-Kontext) vs late_bloom(all-FLUX.2) 실측 A/B 결과:

| | Kontext (`--ref`) | **FLUX.2 (`--flux2`, 기본)** |
|---|---|---|
| 멀티인물 일관성 | ⚠️ 가는 안경 반복 드롭·**4인 병합/복제** | ✅ **2인 비트 5/5 두 인물 유지** |
| 단일인물 | ✅ 안정 | ⚠️ 표정/색 일부 드리프트 |
| 화풍 | 플랫 셀셰이딩·굵은 선(만화풍) | 부드럽고 렌더링·폴리시(일러스트풍) |
| 가격/멀티컷 | ₩108 | **~₩60** |
| 4인+ | ❌ 병합 | △ 1명 누락 → ≤3 reframe |

**불변 원칙(반드시):**
- ★**한 에피소드 = 한 경로**(혼용 금지). Kontext+FLUX.2 섞으면 **화풍이 컷마다 점프**(사용자 검출). → all-FLUX.2 OR all-Kontext, 절대 섞지 말 것.
- **4인+ 한 프레임은 둘 다 무리** → 콘텐츠로 **≤3인 프레이밍**(군집을 줄여라).
- **레퍼런스 먼저 생성 후, 08 식별자를 레퍼런스에 맞춰라**(FLUX는 한국 성인에 안경을 자주 추가 — 싸우지 말고 ref 따라 식별자에 "glasses" 기입).
- FLUX.2 프롬프트: `fal_generate_flux2`가 `ROLE(외형블록)`→`@imageN`으로 **외형 텍스트 제거**(레퍼런스가 외형 담당, 색이름이 글자로 구워지는 것 방지) + 강한 no-text.
- 손 접촉·전신 컷 회피(손 융합·하반신 미앵커): 손은 단순/프레임밖, 전신 대신 상반신.

**Kontext(`--ref`)는 폴백** — 플랫 만화풍이 꼭 필요하거나 FLUX.2 톤이 안 맞을 때. (키즈 마스코트는 둘 다 불요 — schnell `--style cute`로 충분.)

## 관련
- `scripts/generate_images_fal.py`(--flux2 / --ref 모드) · **`scripts/verify_images.py`(자체검증 QC)** · `.claude/skills/produce-sayeon/SKILL.md` · `docs/PRODUCTION_PLAYBOOK.md` §7.5(손 가드) · `docs/FAILURE_CASES.md` FC-022. Gemini 경로 일관성(nano-banana master+image-input)=`generate-references`/`regenerate-reference` 스킬(별도 파이프라인).
