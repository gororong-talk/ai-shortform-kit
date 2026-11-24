---
name: generate-hybrid-sheet
description: 나레이션 production 의 하이브리드 08 프롬프트 시트 2개 생성 — 08_image_prompts.md(정지 스틸 N개) + 08_clip_prompts.md(모션 클립, 스틸 참조 image-to-video). 02_step3_narration 라인을 비트로 매핑(1라인=1비트 또는 split) + 핵심 비트 클립 지정 + Webtoon 스타일·안전(얼굴X·로고X·Storybook 금지·no text). uncle_car/ex_90million 검증. 대량 작성은 서브에이전트 위임. 사용자가 "/generate-hybrid-sheet <slug>", "08 시트 만들어", "이미지+영상 프롬프트", "하이브리드 시트" 같은 표현 사용 시 호출.
---

# /generate-hybrid-sheet — 하이브리드 08 시트 생성

## 트리거
- `/generate-hybrid-sheet <slug>` 또는 "08 시트", "이미지+영상 프롬프트", "하이브리드 시트"
- 전제: `02_step3_narration.txt` + 가사 게이트 OK

## 핵심 설계
1. **비트 매핑**: 1 라인 = 1 비트(B01..BNN) 기본. 페이싱 위해 일부 핵심 라인은 2비트로 split 가능(그땐 `_beat_map.json` 작성: `{"1":[1,2],...}`).
2. **클립 지정 (~30-40%)**: 훅·폭로 캐스케이드·감정·결단·CTA 비트를 🎬 모션 클립으로. 나머지는 정지. (예 uncle_car 11/35, ex_90million 9/24)
3. **image-to-video**: 모든 비트에 스틸 생성 → 🎬 비트는 *자기 번호 스틸을 첫 프레임*으로 애니메이션(1:1 참조). 클립 프롬프트 머리에 **"참조 이미지: B##.png"** 명시.

## ⚠️ 스타일·안전 규칙 (엄수 — dogfood 학습)
- 스타일 문구: **"Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, 9:16 vertical 1080x1920"**.
- ❌ **"Storybook" 단어 금지** — Flow가 하단에 한글 제목 캡션을 자동 삽입함(uncle_car 사고). 대신 각 프롬프트에 **"no text, no caption, no title, no letters anywhere, wordless illustration"** 명시.
- ❌ **"no speech bubble, no dialogue balloon, no comic panel border" 명시 필수** — "no text"만으론 안 막힘. 글자 없는 빈 말풍선/만화 컷 테두리가 그대로 그려지는 사례 발생(reflexive_denial B02 실측, 2026-07-25). 08 시트 공통 문구에 이 세 가지를 항상 포함.
- **얼굴 X**: 전원 뒷모습/손/실루엣/소품. AVOID face.
- **브랜드·로고·읽히는 텍스트·숫자 X**: 돈·명품은 generic 메타포(돈 리본·합류 다이어그램 등).
- mood: 사연 톤 반영 (분노·각성 = restrained→indignant→resolute).

## 산출물
1. `productions/<slug>/08_image_prompts.md` — 스틸 N개(B01..BNN). 헤더에 **COMMON_BASE / CHARACTER_GUIDE / NEGATIVE** 블록. 🎬 비트엔 "🎬→클립" 태그 + 모션 첫 프레임 여백 구도.
2. `productions/<slug>/08_clip_prompts.md` — 클립 M개. 각자 "참조 이미지: B##.png" + Motion 지시(절제, ~2.5s) + image-to-video.
3. **`_clips.json`** — 클립 지정 `{"clips":[1,2,8,...]}` (🎬 비트 번호). ⭐필수 — generate-narration이 이걸로 timing의 png/mp4를 *파일존재와 무관하게* 판정(순서 의존 제거).
4. (split 했으면) `_beat_map.json`.

### ⭐ 두 시트(08_image_prompts.md·08_clip_prompts.md) **맨 위(제목 위 첫 줄)에 'Flow 작업 지시' 블록 고정 삽입** (Flow가 항상 참고):
```
> 🔔 Flow 작업 지시 (먼저 읽기): 프롬프트를 참고해서 이미지와 영상을 만들어줘. 이미지 생성은 한꺼번에 만들지 말고 하나씩 순차적으로 만들어.
> 영상 생성은 프롬프트가 가리키는 이미지를 참고해서 영상을 만들어야 해.
> 생성된 이미지와 영상은 각 씬 이름(B01, B02 …)과 동일하게 저장/변경해줘.
```
→ 서브에이전트 위임 시에도 이 블록을 두 파일 최상단에 넣도록 지시에 포함.

## 대량 작성 = 서브에이전트 위임 권장
N≥20이면 Agent(general-purpose)에 위임해 컨텍스트 절약. 위임 프롬프트 필수 포함:
- 라인별 장면 plan + 🎬 클립 비트 목록
- 위 스타일·안전 규칙 (특히 **Storybook 금지 + no text**)
- 참고 템플릿: `productions/<예시_production>/08_image_prompts.md`·`08_clip_prompts.md` 를 Read 해 포맷 일치
- 산출 경로 2개 + "완료 후 경로·비트수만 보고"
→ 위임 후 **독립 검증**: `grep -c Storybook`(프롬프트 0건), 비트 수, "no text" 포함, 🎬 매핑.

## 다음
- [사용자] Flow 로 스틸 N + 클립 M 생성 → `flow/` → `/normalize-flow-assets`

## 절대 하지 말 것
- 프롬프트에 "Storybook" 쓰기 (캡션 유발)
- 얼굴·브랜드·로고·읽히는 텍스트 넣기
- 클립을 텍스트→비디오로(스타일 튐) — 반드시 *스틸 참조* image-to-video
- 서브에이전트 산출 무검증 통과 (Storybook·안전 grep 필수)

## 참조
- `productions/<예시_production>/08_{image,clip}_prompts.md` — 검증 템플릿
- 선행: `/draft-narration` · 후행: `/normalize-flow-assets` → `/generate-narration` → `/compose-narration`
