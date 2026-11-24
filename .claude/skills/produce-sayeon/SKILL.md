---
name: produce-sayeon
description: 사연 숏폼 1편을 처음부터 끝까지 풀 제작 — 사연 선택(CVDE+베스트댓글 감성 스크리닝)→막장 각색 대본→이미지 프롬프트(웹툰 캐릭터 일관)→fal 이미지→Fish S2-Pro 나레이션(폴백 SunHi)→Ken Burns 렌더→업로드 메타까지 "업로드 준비 완료"로. Gemini 안 씀(Claude 창작+fal+Fish/edge-tts+ffmpeg). 사용자가 "/produce-sayeon", "새 사연 만들어줘", "사연 제작", "사연으로 진행", "사연 한 편 뽑아줘" 같은 표현 사용 시 호출. 후행=**게시(별도 게시 프로그램 또는 수동)**(3플랫폼 완전자동 게시; 실패 시에만 게시(수동) 폴백).
---

# /produce-sayeon — 사연 숏폼 1편 풀 제작 (선택→대본→이미지→TTS→렌더→메타, 업로드 준비까지)

## 트리거
- `/produce-sayeon [post_id]` · "새 사연 만들어줘" · "사연 제작" · "사연으로 진행"
- 산출: `productions/<ts>_<name>/` 에 `06_render_v1.mp4` + `_pubmeta.json` = 업로드 준비 완료. (게시는 **게시(별도 게시 프로그램 또는 수동)** — 3플랫폼 완전자동)

## 왜 이 스킬 (2026-06-17 박제)
이 전체 흐름을 매번 수동으로 했음 → 한 스킬로. **Gemini 안 씀**(막힘): 창작(대본·프롬프트)=Claude 직접, 이미지=fal, TTS=Fish S2-Pro(폴백 SunHi edge-tts — §3), 렌더=ffmpeg. 비용 ≈ fal ₩12×컷수. **이미지 무료 대안(2026-11-16): `scripts/doodle_kit.py`** — 코드로 그리는 파스텔 손그림(₩0·무제한·인물 100% 일관). `<prod>/doodle_scenes.py`에 장면을 SVG로 정의→`doodle_kit.py <slug>`→`flow_images/B##.png`. #59가 첫 적용(판정 대기), 레퍼런스=`productions/<예시_production>/doodle_scenes.py`. ⚠️**컷수 상한 = 6컷(2026-11-16 사용자 승인 시범 — 기존 10컷에서 인하)**. 여러 라인을 한 비트에 묶고(같은 컷을 떨어진 라인에 재사용 가능), 핵심 대사 1~2개는 `00_meta.text_card_lines`(타이포 카드, ₩0)로 뺀다. 2~3편 성과가 중앙값 아래로 떨어지면 10으로 복귀(판정 = `docs/2026-11-15-전체검토-결과.md` §3).

## ★ 최적화·판정 기준 = **Instagram 도달 1순위** (2026-08-06 실측으로 무대 이동)

디스커버리가 지배). 지금까지 판정을 YouTube 평균조회율로 해왔는데 **주전장은 IG였다.**

- **훅·첫 3초·`thumbnail_title` 은 IG 릴스 기준으로 쓴다**(소리 없이 스크롤하다 멈추게 하는 화면).
  YouTube 평균조회율은 **같은 플랫폼 내 비교용 보조지표**로 내린다.
- **트랙/소재 판정도 IG 도달을 먼저 본다.** 플랫폼 간 비교는 **조회수로만**(완주율 정의가 다름).
- **구독·팔로우 전환을 목표로 훅을 비틀지 마라** — 전환장치 3종 실측 결과 전환은 어느 레버로도
  안 움직였다(YT 0.152%→0.090%, IG 0.066%). 목표함수는 **도달 × 완주율**이다.
- 근거: `docs/2026-08-06-판정게이트-결과.md`.

## 0. 사연 선택 = 점수 + 베스트댓글 (CVDE만 믿지 마라)
```bash
python scripts/pick_story.py --min-cvde 86 --limit 12
```
- CVDE 점수는 막장 키워드 밀도 과대평가 → **베댓이 진짜 신호.** 🔴혹평("주작·개노잼·오글·뻔한·설득력")=버려라(예: 환갑봉투 <글번호>=95점인데 혹평→폐기). **🟢호응 + 명확한 악역 + 피해자 공감 + 믿을만함**을 골라라.
- ⚠️민감(자살·아동학대·성범죄)=엔터/플랫폼 정책상 제외. ⏭️제작됨(post_id가 productions에 있음)=제외.
- 선택 즉시 클레임(중복 제작 방지): `python scripts/pick_story.py --claim <PID>` (이전 수동 sqlite 한 줄을 대체, 2026-06-24).

### 0.5 정보형 사연 후보 인지 (선택, `docs/PRACTICAL_INFO_FORMAT.md`)
`--category` 값이 `직장갈등`·`금전갈등`·`학교폭력`·`부부갈등`·`가족갈등`·`시댁갈등`·`이혼` 중 하나이고 사연 안에 신고·상담·소송 등 **명확한 해결경로**가 있으면, 사용자에게 "이 사연은 정보형(실생활 대처 정보 결합)으로 만들까요?"를 물어본다. Yes면 `/draft-narration` 단계에서 정보형 서브트랙 절차(§정보형 사연 서브트랙)를 따른다. 새 채널·새 스킬 아님 — 기존 파이프라인 그대로에 `00_meta.story_type="practical_info"`만 추가되는 것.

## 1. 막장 각색 방향 (사이다 흐름)
사연을 그대로 읽지 말고 **각색**: ①앞 양념(첫사랑·순수함 등 "왜 결혼했냐" 반박 차단) ②결혼식/특정시점 **돌변** ③막장 빌드업(피해자에게 명확한 가해: 면박·무릎꿇림·방관) ④**숨은 우위**(경제력·이직·이혼준비 등 "저들이 모르는 패") ⑤**사이다 한 방**(통쾌한 선긋기/참교육) ⑥떠남/결말. 떡밥은 회수(예: 무릎 꿇림→"무릎은 잘못한 사람이 꿇는다"). 주작 느낌 금지(베댓이 가장 싫어함).

- ★**우선 패턴 = "형평성/이중잣대 위반→논쟁형 사이다" (2026-07-09 실측 반영)**: 사용자가 직접 게시해 터진 IG 릴스 2건(banban_marriage 13K뷰·sidaek_katok 11K뷰)과 그 패턴을 재현한 billion_facade(15K뷰)까지 3건 연속 확인. 후보 스크리닝(§0) 시 "한쪽만 조건을 지켰는데 상대는 몰래 어겼다/숨겼다"류 형평성 위반 소재를 우선 고려하고, 각색 시 가해자 쪽 반박("내가 더 냈다", "계산적이다" 등)을 대본에 그대로 남겨 "누가 맞냐" 댓글 논쟁을 유도할 것. 해시태그도 `#막장사연` 광범위 계열보다 `#이중잣대` 같은 니치 태그를 포함.

## 2. 소스 파일 5종 작성 (참고 모델: `productions/<예시_production>/`)
디렉토리 `productions/<YYYYMMDDHHMM>_<eng_name>/flow_images/` 만들고:
- **00_meta.json**: post_id, slug, format="narration_short", target_duration_sec, category, narration_tone, image_backend, format_decision, core_identity, hook, key_details[], characters[], **safety**(실명·로고·가짜글자 금지, 폭력없음, 비방아님), **thumbnail_title**(★신규 2026-07-09, 아래 참고), **next_preview_lines: 1**(★신규 2026-07-09, 사연 표준 — 마지막 나레이션 1줄=다음편 떡밥을 블랙카드로. 아래 §3 참고).
  - **thumbnail_title**: 나레이션 원문(S01)과 **별개로** 짧게 새로 짓는 압축 문구(6~14자 내외, 클릭베이트체, "~습니다" 등 서술형 어미 금지 — 예 "1억은 선물이 아니라 대출?", "밥값도 이중잣대?"). `compose_narration.py`가 오프닝 1.8초 동안 화면 상단에 큰 박스체 제목카드로 자동 렌더(하단 나레이션 자막과 동시 노출, §3).
- **02_step3_narration.txt**: `S01`~`S18~21` 한 줄=한 비트(존댓말·담담→사이다). ~85~130s.
- **08_image_prompts.md**: `B01`~`B06`(★상한 6컷 시범, 2026-11-16). 각 비트=장면+세팅+`Korean webtoon illustration style, clean bold linework, soft flat cel shading, vertical 9:16 (1080x1920)`.
  - ★**인물 일관성 = 레퍼런스 잠금 (2026-06-21 표준, `docs/CHARACTER_CONSISTENCY.md` 필독)**: 인물이 여러 컷 등장하면 **반드시 레퍼런스 잠금**(§3) — text-only 외형블록 복붙은 **얼굴 드리프트**(elder_love 검증 실패). 비트엔 **짧은 레퍼런스-일치 식별자만**(역할토큰+핵심특징+위치, 예 `GRANDPA (white hair, beige cardigan, LEFT)`). ❌풀 외형블록 재기술(레퍼런스와 충돌→색 드리프트) ❌외형0(멀티 레퍼런스 정체성 병합). 색은 **구체값**("dusty rose pink", ~~"soft-lavender"~~ 금지).
  - ⚠️**FLUX는 negative 무시** → `no text/violence` 식은 약함, **positive로 표현**. **손/반지 클로즈업 금지**(프레임밖·단순, FLUX 최악 약점 — elder_love B08 공중부양 반지).
  - ★★**'안경'은 부정형으로도 쓰지 마라(2026-08-08 실측)**: 레퍼런스에 안경이 없는데 FLUX 가 자꾸 안경을 그려서 `bare eyes with no eyewear` / `none of them wear glasses` 로 막으려 했더니 **오히려 두 인물 전원에게 안경을 그렸다**(negative 무시 함정의 최악 사례). → **안경·eyewear·glasses 라는 단어를 프롬프트에서 통째로 뺀다.** 대신 `bare face, large clear brown eyes` 처럼 **긍정 표현만** 쓴다. 그래도 가끔 붙으면 **같은 프롬프트 재시도**로 빠진다(비결정적).
  - ★★**다인물 비트가 계속 깨지면 단독 구도로 갈아탄다(2026-08-08 실측)**: `stock_tax_trap` B10(2인 대치)에서 ①두 인물이 같은 옷으로 **정체성 병합** → ②역할 구분 후엔 **양쪽에 안경** → ③화자가 **여성으로 성별 전환**, 3연속 실패. 반면 같은 production 의 단독 인물 컷 8개는 **전부 1회 통과**. → 2인 비트에서 2회 실패하면 프롬프트를 더 조이지 말고 **단독 인물 구도로 재설계**한다(상대는 화면 밖=시청자 시점으로 처리해도 서사가 산다). 비용·시간 모두 이쪽이 싸다.
  - ★**밤거리/편의점/간판 장면 금지(2026-06-18 B04 3롤 낭비)**: fal이 'no signage'를 무시하고 네온간판에 깨진 가짜 한자/글자를 자주 박음. → 그런 비트는 **평면 스튜디오 배경 또는 얼굴 클로즈업**(no scenery/no building/no sign)으로 우회. 배경 없으면 글자 못 박음.
  - ★**폭력·접촉 비트(모욕·다툼·DV)**: `no physical contact/touching/grabbing/raised hands` 만으론 부족 — **구도로 강제**(두 인물 분리 + 가해자 손 내림/팔짱 + 사이 빈 공간). 한 명만 화내고 다른 명은 떨어져 반응. (DV 소재면 메시지=피해자편·안전한 손절, 설명에 1366 안내.)
- **_beat_map.json**: `{"<라인번호>":[<비트>], ...}` — ★키는 **라인번호 문자열**(`"1"`,`"2"`…`"21"`), `"S01"` 아님. 스크립트가 `line2beats.get(str(li))`로 읽어 틀리면 **조용히 1:1 폴백 → 없는 B15+ 컷 참조 → compose 실패**(toto_family 실측). 여러 줄이 한 비트 공유 가능(예 `"2":[2],"3":[2]`).
  - ★**나레이션 길이 선검증(toto_family 2026-06-24)**: edge SunHi 첫 생성이 목표의 ~1.8배(165s vs 90s)로 길어질 수 있음. 생성 직후 `04_timing.json`의 `total_duration ≤ ~105s` 와 `unique beat#`=실제 컷수 확인. 길면 02_step3 대본 압축(라인 ~15~20자) 재생성 → 그래도 길면 `tighten_narration.py --speed 1.25 --kenburns`. ⚠️타이밍을 고쳤다면 먼저 `audio/03_audio_pre_tighten.mp3`+`04_timing_pre_tighten.json` 삭제(잘못된 타이밍이 백업되면 tighten 재실행도 실패).
- **_clips.json**: `{"clips": []}` (빈 배열=KenBurns 스틸).

## 3. 생성 (스크립트)
```bash
# ★인물이 여러 컷 등장 = 레퍼런스 잠금(docs/CHARACTER_CONSISTENCY.md). 안 그러면 얼굴 드리프트.
#  (1) 역할별 레퍼런스 1장(schnell, 정면·손 프레임밖·구체 색 — 깨끗할 때까지 재롤):
python scripts/generate_images_fal.py --production <slug> \
  --prompt "front-facing waist-up character reference portrait of NARRATOR, <구체 외형>, hands out of frame, plain background, single character, centered" \
  --out flow_images/_ref_narrator.png      # 역할마다 반복 → _ref_<role>.png
#  ★(2) all-FLUX.2 레퍼런스 잠금(2026-06-21 A/B 기본 — 멀티인물 일관성+가격 우위·화풍 균일):
python scripts/generate_images_fal.py --production <slug> --flux2 \
  --ref narrator=flow_images/_ref_narrator.png --ref <role2>=flow_images/_ref_<role2>.png   # 인물 사연
#  ⚠️한 에피소드=한 경로(혼용 금지)·4인+는 ≤3 프레이밍·식별자는 ref에 맞춤(FLUX 안경 자주 추가). docs/CHARACTER_CONSISTENCY.md
#  ★FLUX.2 edit 콘텐츠체커가 갈등·감정 프롬프트에 비결정적으로 걸림(막장 사연 실측 10건+) →
#    대응 순서·확인된 트리거 단어 블록리스트는 `.claude/skills/produce-story-world/SKILL.md` 함정9(b) 참조(범용 적용).
#  (플랫 만화풍 필요 시만 --flux2 빼고 --ref=Kontext 폴백. 키즈 마스코트는 --style cute 로 충분.)
python scripts/generate_images_fal.py --production <slug> --style webtoon --dry-run   # 컷수 확인(text-only)
python scripts/generate_images_fal.py --production <slug> --style webtoon              # text-only(인물 적을 때)
# ★이미지 검수 = 사용자 직접(기본·2026-06-25 지침). 생성이 끝나면 generate_images_fal 이 Finder 로
#   flow_images 폴더를 자동으로 띄움 → 사람이 눈으로 본다. 자동 비전QC 루프는 기본 OFF(옵션).
python scripts/check_black_frames.py <slug>                                            # ① 검은이미지(무료·빠른 게이트, 자동 OK)
#  (옵션) 자동 비전QC 를 원할 때만 명시 실행 → /qc-autofix:
#  .venv/bin/python scripts/qc_autofix.py --production <slug>   # 자율 QC 루프(검출→글자=인페인트/그외=재생성, 최대3회). 기본은 안 돌림.
#  의심 컷만 수동 재생성: generate_images_fal --only <beat>. 캐릭터 일관성 docs/CHARACTER_CONSISTENCY.md
#  ★★나레이션 1순위 = Fish Audio S2-Pro (2026-06-19 결제·전환 표준). 음질·감정이 SunHi 우위 → sayeon 기본:
.venv/bin/python scripts/generate_narration_fish.py <slug>                             # Fish S2-Pro(00_meta 기반 voice 자동·인라인 감정태그). 위계 Fish>SunHi>Gemini>ElevenLabs
#  (폴백만) Fish 장애 시: /tmp/edgetts_venv/bin/python scripts/generate_narration_edge.py <slug>   # SunHi (edge-tts, 로봇톤 — 최후 폴백)
#  ⚠️ SunHi 를 기본으로 쓰지 마라: geumsu_bloodline(2026-07-04) 에서 SunHi+1.12× tighten 이 "목소리 이상"으로 정정 → Fish 재생성.
PATH=/opt/homebrew/bin:$PATH .venv/bin/python scripts/compose_narration.py <slug> --kenburns   # 06_render_v1.mp4 (★QC가 이미지 고쳤으면 이 재렌더가 반드시 그 뒤에)
#  ★훅(첫 자막 줄)은 기본 1.5배 큰 인스타툰식 제목카드로 자동 렌더(2026-07-07 표준, --hook-scale 로 조절)
#  ★썸네일 제목카드(2026-07-09): 00_meta.thumbnail_title 있으면 오프닝 1.8초 화면 상단에 큰 박스체로 자동 겹침(--title-card-sec 로 조절). 필드 없으면 조용히 생략.
#  ★다음편 예고 블랙카드(2026-07-09): 00_meta.next_preview_lines=1 이면 마지막 나레이션 1줄(다음편 떡밥)을
#    이미지 위에 겹치지 않고 화면을 완전 블랙으로 덮은 뒤 중앙에 크게 띄운다("이미지 위 겹침이 혼잡"하다는 사용자
#    피드백). 사연 표준=1. CLI 오버라이드 --next-preview-lines. 필드 없으면 기존처럼 이미지 위 자막(하위호환).
# ffmpeg로 훅·엔딩 프레임 뽑아 자막·영상 Read 검증
```

## 4. 업로드 메타 (_pubmeta.json 직접 작성)
채널 = **사연 채널** `@your_story_channel`(`UC_YOUR_CHANNEL_ID`) · `made_for_kids=false` · `ai_label=true`(fal) · `visibility=public` · `facebook_crosspost=false`. platforms.youtube{title,description(+🤖AI고지+해시태그)}, tiktok{caption(니치 해시태그 ≤8 — #fyp·#추천 같은 broad 필러는 prep_upload 게이트가 경고하므로 넣지 않음)}, instagram{caption(+#릴스)}. (모델: sidaek_katok `_pubmeta.json`.)

## 5. 업로드 준비 완료 → 보고 + (요청 시) 게시(수동)
```bash
.venv/bin/python scripts/prep_upload.py <slug> --no-open   # ★freshness 가드(렌더<소스면 STALE → 중단, --force로만 강행) + 게시前 정책 게이트(해시태그·경고). 경고 없어야 게시 OK.
```

## 참조
- 표준 파이프라인 메모리 / `docs/PRODUCTION_PLAYBOOK.md` · 실측 모델 = `productions/<예시_production>/`
