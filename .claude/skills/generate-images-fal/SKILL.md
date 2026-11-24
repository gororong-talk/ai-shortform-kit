---
name: generate-images-fal
description: production 의 08_image_prompts.md 를 읽어 fal.ai FLUX 로 flow_images/B##.png(1080×1920) 양산. 막힌 Gemini-image(2.5-flash-image 429)·Flow 월구독을 대체하는 종량제 이미지 백엔드(schnell ~₩12/장 — 단 실사용 레퍼런스잠금 kontext는 ₩54~108/장). 키·SDK 보유(FAL_KEY + fal_client). compose_narration 이 바로 읽는 위치로 저장(normalize 불필요). 사용자가 "/generate-images-fal", "이미지 생성", "fal 이미지", "flow 이미지 만들어", "스틸 생성" 같은 표현 사용 시 호출.
---

# /generate-images-fal — fal.ai FLUX 이미지 양산

## 트리거
- `/generate-images-fal <slug>` 또는 "이미지 생성", "fal로 스틸 뽑아", "flow_images 만들어"
- 전제: `productions/<slug>/08_image_prompts.md` (generate-hybrid-sheet 산출, `## B## ... \n 영문프롬프트`)

## ★인물 여러 컷 = 레퍼런스 잠금(`--ref`, 2026-06-21)
text-only는 얼굴 드리프트(매 컷 독립생성). 인물 사연은 **레퍼런스 잠금** 필수 — 역할별 레퍼런스 1장(`--prompt … --out flow_images/_ref_<role>.png`, 정면·손 프레임밖·구체 색) → `--ref grandpa=… --ref grandma=…` 로 비트의 ROLE 토큰을 fal kontext(2인=multi)로 잠금. 비트엔 **짧은 레퍼런스-일치 식별자만**. 전 표준=`docs/CHARACTER_CONSISTENCY.md`. 손/반지 클로즈업 금지(FLUX 약점). FLUX는 negative 무시→positive.

## 왜 (배경)
- 기존 이미지 경로 = Gemini-image(**429 막힘**) / Imagen4(유료) / Flow(월구독·브라우저 수동). 전부 누수·불안정.
- **fal.ai FLUX schnell = 장당 ~$0.009(₩12)·3.9초·웹툰 품질 OK** (2026-06 스모크 검증). 키(FAL_KEY)·SDK(.venv fal_client 0.13.1) 이미 보유.
- 전략·단가 전체 → `docs/MINIMAL_CAPITAL_STACK.md`.

## 사용
```bash
# 전체 생성 (08 시트 → flow_images/B##.png, 멱등: 이미 있으면 스킵)
.venv/bin/python scripts/generate_images_fal.py --production <slug>
# 핵심 컷만 고품질 dev / 특정 비트 / 비용 미리보기
.venv/bin/python scripts/generate_images_fal.py --production <slug> --only 1,31 --model dev
.venv/bin/python scripts/generate_images_fal.py --production <slug> --dry-run   # 호출 0, 비용·플랜만
.venv/bin/python scripts/generate_images_fal.py --production <slug> --style none # 08 원문 그대로(웹툰 강제 끔)
# 1장 스모크(키·품질 확인)
.venv/bin/python scripts/generate_images_fal.py --prompt "Korean webtoon ..., no text" --out /tmp/smoke.png
```
처리: 08 파싱 → `fal-ai/flux/{schnell|dev}` 호출 → URL 다운로드 → PIL cover-fit **1080×1920** → `flow_images/B##.png`.
→ fal 산출물은 캡션밴드 없음 → **normalize-flow-assets 불필요**, 바로 `/compose-narration` 으로.

## 단가 / 모델
- ⚠️ 실사용 비용(2026-11-16 정정): 인물 사연은 레퍼런스 잠금(`--ref`→kontext) 이라 **₩54~108/장**. `--flux2`(fal-ai/flux-2-pro/edit) = 출력 첫 1MP $0.03 + 입력·출력 추가 MP당 $0.015(올림) → 1080×1920 출력+레퍼런스 1~3장(각 1080×1920) ≈ **$0.09~0.20(₩130~280)/장** (2026-11-17 fal 모델 페이지 규칙으로 계산 — 입력 합산/개별 올림이 페이지상 모호해 범위로, 청구액 대조 안 함). 레퍼런스를 작게 줄이면 싸진다. 아래 ₩12 는 schnell(레퍼런스 없음) 기준.
- `schnell`(기본): ~₩12/장. 양산 워크호스. 숏폼 12컷 ~₩100, 롱폼 100컷 ~₩700~1000.
- `dev`: ~₩33/장(추정). 훅·엔딩 등 핵심 컷만 선택.
- 캐릭터 일관성 필요(같은 인물 여러 씬) → 현재 schnell 단독은 랜덤. character_pool 병행 또는 FLUX.2 dev 멀티레퍼런스(추후 어댑터).

## ⚠️ 스타일 일치 (Meta/Flow 결 맞추기) — 검증됨 2026-06-13
- FLUX는 **기본이 사실주의**라 08시트의 약한 "webtoon, cel shading" 한 줄만으론 **반실사·페인터리**가 나옴(기존 Meta 클린웹툰과 따로 놂).
- 그래서 `--style webtoon`(**기본값**)이 "flat 2D, NOT 3d/realistic"을 강하게 prepend → **Meta 웹툰 결로 복귀**(B01/B03/B14 비교 검증). 끄려면 `--style none`.
- **schnell-webtoon = Meta에 제일 근접**(차분한 웹툰). `dev`는 웹툰이나 더 애니풍(큰 눈).
- 잔차: fal 얼굴이 Meta보다 약간 선 굵고 만화적 → **한 production은 한 백엔드로 통일**(fal끼리는 내부 일관 OK, fal+Meta 혼합은 미세차 보임).

### 모델·일관성·텍스트 (랜덤사연 3비트 schnell↔dev 비교 검증, 2026-06-13)
- **schnell = 이 프로젝트 표준** — 만화/만화선 클린, **공유 캐릭터블록 복붙 시 인물 디자인(헤어·의상·얼굴패밀리) 잘 유지**, ₩12. `dev`(₩33)는 더 **부드러운 애니 일러스트**(지브리/포스터풍)·일관성 살짝 낮고·프롬프트 과해석(없는 인물 추가)·텍스트 누수 더 많음 → 애니풍을 원할 때만.
- ⚠️ **가짜 텍스트 누수**: `no text` + webtoon에도 **간판·벽 포스터·메모 있는 씬은 글자 비슷한 흔적**이 남음(특히 거리/게시물 장면). 대응: ① 프롬프트에서 **보이는 간판·포스터·메모 묘사 피하기** ② 위험 키컷은 재생성 or 크롭 ③ 하단은 normalize 밴드로 가려짐(화면 중앙 간판은 아님).
- **세트 일관성**: 캐릭터블록 verbatim 복붙 = "같은 디자인"까지(픽셀동일 얼굴 X). 정지컷 웹툰엔 충분. 더 빡센 동일성 필요 시 FLUX.2 dev 멀티레퍼런스 or character_pool.

## 함정 / 주의
- ⚠️ **안전 프롬프트는 08 시트가 책임** — 이 스크립트는 프롬프트를 **그대로 전달**(수정 안 함). 08에 `no text / NOT photorealistic / no real-celebrity / no logo`(CLAUDE.md 규칙)가 박혀 있어야 함.
- **멱등**: 이미 있는 B##.png 는 스킵 → 재시도는 실패 비트만 `--only` 로.
- **단가 추정**: dev/video 단가는 공시가 기반 — 본격 전 1건 실측 권장.
- **결제 발생**: fal 종량제(소액이지만 실비). FAL_KEY funding 끊기면 실패 → 에러 그대로 보고(무음 통과 안 함).
- 캐릭터 일관성 깨지면 `/match-characters` 또는 핵심 인물 컷만 dev.

## 절대 하지 말 것
- 08 시트의 안전 negative 빼고 호출 (얼굴 실사화·로고·텍스트 위험)
- 막힌 Gemini-image 스크립트(gemini_image_gen.py Playwright)로 회귀 — 이 경로가 대체
- 캐릭터 description 요약 (08 시트는 매 비트 전체 복붙이 원칙)

## 참조
- `scripts/generate_images_fal.py` — 구현
- `docs/MINIMAL_CAPITAL_STACK.md` — 전체 스택·단가·로드맵
- 선행: `/generate-hybrid-sheet`(08 시트) · 후행: `/compose-narration`
- 비교: `generate_bgm.py`(같은 REST 종량제 연동 패턴)
