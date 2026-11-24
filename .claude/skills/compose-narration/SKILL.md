---
name: compose-narration
description: 나레이션/하이브리드 production 최종 합성. 04_timing.json(가변 비트) + flow_images(mp4+png 혼합) + 03_audio_narration_only.mp3 → 비트 세그먼트 빌드·concat·한글자막(ASS, 세이프영역) burn·오디오 mux → 06_render_v1.mp4. compose_flow_clips.py(옛 19클립/130s 하드코딩)가 못 다루는 나레이션 케이스 전용. uncle_car(#13) 검증. 사용자가 "/compose-narration <slug>", "나레이션 합성", "compose narration", "최종 렌더" 같은 표현 사용 시 호출.
---

# /compose-narration — 나레이션/하이브리드 최종 합성

## 트리거
- `/compose-narration <slug>` 또는 "나레이션 합성", "최종 렌더", "compose narration"
- 전제: `04_timing.json` + `flow_images/B##.{png,mp4}` + `03_audio_narration_only.mp3`

## 왜 이 스킬 (배경)
- `compose_flow_clips.py` 는 **옛 19클립/130s 고정 타임라인** 하드코딩 → 나레이션(가변 비트 수·길이) 못 씀.
- 나레이션은 **혼합 미디어**(하이브리드: 모션 클립 mp4 + 정지 png) + **04_timing.json 비트 타임라인** 기반이라 별도 compose 필요.

## 핵심 동작 (스크립트)
```bash
python scripts/compose_narration.py <slug>
# 옵션:
#   --kenburns               PNG 스틸에 Ken Burns(느린 줌인) — 롱폼/스틸-위주 필수(정적 방지). 첫 비트 강한 푸시인
#   --out 06_render_v1.mp4   출력 파일명
#   --marginv 420            자막 하단 여백(밴드 위 세이프영역). 밴드 높이 바꾸면 함께 조정
#   --fontsize 58            자막 크기
#   --next-preview-lines N   마지막 N개 자막(다음편 떡밥)을 이미지 위 겹침 대신 화면 완전 블랙+중앙 크게(예고 카드).
#                            미지정 시 00_meta.next_preview_lines(기본 0=off). 사연 표준=1 (2026-07-09 사용자 지침).
#   ※ 00_meta.thumbnail_title 있으면 오프닝 --title-card-sec(기본 1.8s) 상단 제목카드 자동. 훅(첫줄)은 --hook-scale(1.5×) 자동.
```
처리:
1. `04_timing.json` 의 `beats[file,start,end]` 순서로 **비트 세그먼트 빌드**
   - `.png` = 해당 길이 정지(loop) / `.mp4` = trim, 비트가 더 길면 **마지막 프레임 hold**(tpad clone)
   - 전부 1080×1920·30fps·yuv420p 통일
2. 세그먼트 concat → 한 트랙
3. `subtitles[text,start,end]` → **ASS 자막**(한국어 폰트 자동탐지, 흰/검정외곽, 세이프영역) **burn**
4. 마지막 비트를 오디오 끝까지 연장(트레일링 무음 hold) + 나레이션 mux
5. `06_render_v1.mp4` (h264+aac, faststart)

## 권장 — 렌더 후 QA (필수)
프레임 추출해서 자막·구도·밴드 확인:
```bash
# 핵심 4지점 프레임 → 그리드
for t in 5 35 85 130; do ffmpeg -y -ss $t -i productions/<slug>/06_render_v1.mp4 -frames:v 1 -vf scale=300:533 /tmp/q$t.png; done
ffmpeg -y -i /tmp/q5.png -i /tmp/q35.png -i /tmp/q85.png -i /tmp/q130.png -filter_complex "[0][1]hstack[a];[2][3]hstack[b];[a][b]vstack" /tmp/qa.png
```
→ Read `/tmp/qa.png`: ① 자막이 밴드 위에 떠 있나 ② 한글 줄바꿈·가독성 ③ 비트↔나레이션 싱크 ④ 클립 모션 정상.

## 함정 / 주의
- **자막 한국어 폰트**: 스크립트가 `fc-list :lang=ko` 로 자동 탐지 (Apple SD Gothic Neo 우선). 빈 박스로 나오면 폰트 설치 필요.
- **자막 위치 vs 밴드**: `normalize-flow-assets` 밴드(바닥 ~17%)와 자막 `--marginv 420`(밴드 위)이 짝. 밴드 높이 바꾸면 marginv도.
- **ffmpeg-full 필요** (`/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`, libass). lite ffmpeg 는 ass 미지원.
- 세그먼트는 `_tmp_compose/seg/` 에 남음 (재렌더 빠름). 오디오/타이밍 바꾸면 _tmp 정리 후 재실행.
- 길이 조임: 오디오를 `atempo`로 조이면 04_timing.json 도 비례 재계산 필요 → `generate-narration` 재실행이 더 안전.
- **🆕 롱폼(비트<라인)**: `_beat_map.json`이 여러 라인을 한 비트(이미지)에 매핑하면 그 컷이 여러 라인 걸쳐 hold (broken_engagement #15, 59라인→31컷). seg 파일명=순번(idx)이라 같은 비트 반복돼도 안 깨짐(수정 완료).
- **🆕 스틸-위주 롱폼은 `--kenburns` 필수** — 안 쓰면 PNG가 완전 정지(5분 멈춘 그림=이탈). zoompan 2x 프리스케일로 떨림 방지.

## 절대 하지 말 것
- `compose_flow_clips.py`(옛 가사곡 19클립용)를 나레이션에 쓰기
- 자막을 밴드 안(바닥)에 두기 — 플랫폼 UI에 가림 (세이프영역 유지)
- 04_timing.json 없이 호출 (`/generate-narration` 먼저)

## 참조
- `scripts/compose_narration.py` — 실제 구현
- `productions/<예시_production>/06_render_v1.mp4` — 검증 사례
- 선행: `/generate-narration` + `/normalize-flow-assets` · 후행: `/upload-meta`
