---
name: produce-kids
description: 키즈 채널 키즈 에피소드 1편 풀 제작 — curriculum.json의 다음 자모/숫자를 소비해 스캐폴드→fal cute 이미지→장면다양성 게이트→Fish 나레이션→큰글자 번인 렌더→업로드 준비까지. 결정 구조는 자동, 장면(SCENE_PACK)은 anti-slop 큐레이션 게이트. 사용자가 "/produce-kids", "키즈 제작", "토리 영상 만들어", "한글 영상 만들어", "키즈 한 편" 같은 표현 사용 시 호출. 후행=**게시(별도 게시 프로그램 또는 수동)**(3플랫폼 완전자동 게시; 실패 시에만 게시(수동) 폴백).
---

# /produce-kids — 키즈 에피소드 1편 풀 제작

## 트리거
- `/produce-kids [series] [letter|숫자범위]` · "키즈 제작" · "토리 영상 만들어"
- 인자 생략 시 `hangul_consonants` 의 다음 ready 자모를 제안.
- 산출: `productions/<ts>_mascot_<rom>/` 에 렌더 + `_pubmeta.json` = 업로드 준비. (게시 **게시(별도 게시 프로그램 또는 수동)**, 채널 @your_kids_channel — 키즈는 YouTube 단독)

## ⚠️ 우선순위·현실 (정직 고지)
키즈는 **콜드스타트·저ROI**([[retention_insights]] 5뷰). 사연/명언이 우선. "6개월 최고채널"=비현실([[kids_channel]]).

## 0. 대상 선택 (curriculum.json)
```bash
python3 -c "import json;c=json.load(open('data/kids/curriculum.json'));[print(k,'→',[ (i.get('letter') or i.get('range')) for i in v['items'] if i.get('status')!='produced'][:6]) for k,v in c['series'].items()]"
```
- 다음 ready 한 칸 선택(예 자음 `ㅅ`). 지원 recipe = **consonant·number**(vowel/word는 build 미지원 → 추후).

## 1. ★ SCENE_PACK 게이트 (anti-slop — 반자동, 사람/Claude 큐레이션)
스캐폴드는 결정적 파일(00_meta·02_narration·08·overlay)을 자동 생성하지만 **장면 5컷은 letter별 SCENE_PACK**에서 온다. 없으면 build가 **중단**한다(유사콘텐츠 단속 회피 = 장면을 진짜 변주해야 함).
```bash
.venv/bin/python scripts/build_kids_episode.py <series> <letter> --dry-run   # SCENE_PACK 있으면 미리보기, 없으면 중단+안내
```
- **중단 시**: `scripts/build_kids_episode.py` 의 `SCENE_PACKS`(자음) 또는 `NUMBER_SCENE_PACKS`(숫자)에 그 키를 추가 — `friend_ko/friend_en`, `w1_flavor/w2_flavor`, `scenes[5]`(한글라벨, 표정, 영문장면). **★앞 편(ㄱ~ㅂ 등)과 배경·포즈·구도 절대 안 겹치게.** 이게 키즈의 유일한 창작 큐레이션 지점.

## 2. 스캐폴드 → 파이프라인 (build가 끝에 정확한 명령 출력)
```bash
.venv/bin/python scripts/build_kids_episode.py <series> <letter>            # 폴더+6파일 생성 + curriculum 자동 produced 마킹
.venv/bin/python scripts/generate_images_fal.py --production <slug> --style cute   # 마스코트 토리(글자 없음)
python scripts/check_kids_prompt_variety.py <slug>                          # ★장면 다양성 게이트(exit 1=Jaccard≥0.5 유사 → SCENE_PACK 보강)
python scripts/check_black_frames.py <slug>                                 # fal 검은이미지 가드
.venv/bin/python scripts/qc_autofix.py --production <slug>                  # (옵션)자율 QC — 마스코트/가짜글자. exit1=잔존 보고. /qc-autofix
.venv/bin/python scripts/generate_narration_fish.py <slug>                  # Fish S2-Pro(없으면 SunHi: /tmp/edgetts_venv/bin/python scripts/generate_narration_edge.py <slug>)
PATH=/opt/homebrew/bin:$PATH .venv/bin/python scripts/compose_narration.py <slug>   # track=kids_edu → 큰글자(자모/숫자) 자동 번인 (overlay_kids_letters)
```
- ★이미지를 QC가 고쳤으면 compose가 그 **뒤**에 와야 함(stale 렌더 방지 [[stale-render-and-foreground-text-qc]]).

## 3. 업로드 메타 + 준비
`_pubmeta.json` 작성: 채널 **@your_kids_channel**(`UC_YOUR_CHANNEL_ID`) · `made_for_kids=true` · `ai_label=true` · TikTok/IG 계정 없음 → `--na tiktok --na ig`. YT 태그=빌드의 `KIDS_YT_TAGS` + 니치(#키즈채널 #한글 #<자모>).
```bash
.venv/bin/python scripts/prep_upload.py <slug> --no-open   # freshness 가드 + 정책 게이트
```

## 4. 보고 + (요청 시) 게시(수동)

## 참조
- 후행 게시 **게시(별도 게시 프로그램 또는 수동)**(실패 시 게시(수동) 폴백) · QC `/qc-autofix` · 자매 스킬 `/produce-sayeon`
- COPPA·아동용·AI슬롭 단속 회피 = [[kids_channel]]
