---
name: upload-meta
description: 07_upload_meta.md 자동 생성 (TikTok / YouTube / Instagram 캡션 + 체크리스트). 가사·메타·영상 정보 기반 자동 채움. chinjeong/dirty 검증 패턴 따름. 사용자가 "/upload-meta <slug>" "업로드 메타 만들어" 같은 표현 사용 시 호출.
---

# /upload-meta — 07_upload_meta.md 자동 생성

## 트리거
- 사용자가 `/upload-meta <slug>` 슬래시 명령
- 자연어: "업로드 메타 만들어", "07_upload_meta 작성", "캡션 자동 생성" 등

## 사전 조건
- `06_render_flow.mp4` (또는 `06_render_chibi.mp4`) 완성
- `00_meta.json` 작성됨
- `02_step3_narration.txt` 8섹션 가사 있음
- `03_audio_meta.json` BGM 메타 있음

## 입력 자동 추출

```python
import json
prod = Path(f"productions/{slug}")
meta = json.loads((prod / "00_meta.json").read_text())
audio_meta = json.loads((prod / "03_audio_meta.json").read_text())
lyrics = (prod / "02_step3_narration.txt").read_text()
mp4_path = prod / "06_render_flow.mp4"

# 영상 길이 + 크기 추출
import subprocess
duration = float(subprocess.check_output([
    "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1", str(mp4_path)
]).strip())
size_mb = mp4_path.stat().st_size / 1024 / 1024
```

## 플랫폼 호환성 자동 판정

```python
def platform_check(duration_sec):
    return {
        "TikTok": "✅ 통과" if duration_sec <= 600 else "❌ 초과",
        "Instagram_Reels_표준": "✅" if duration_sec <= 90 else "⚠️ 표준 초과 → 확장 모드 (~3분) 또는 90s 컷",
        "YouTube_Shorts": "✅" if duration_sec <= 60 else "❌ 초과 → 일반 영상 (`#shorts` 미사용)",
    }
```

## ★회차번호 (episode_number, 사연 사연 채널 전용 — 전환장치 2026-07-09)

캡션 작성 **전에** 먼저 다음 회차번호를 뽑는다:
```bash
.venv/bin/python scripts/parse_upload_meta.py --next-episode
```
채널이 `@your_story_channel`(사연)이면 그 번호 N을 **YT 제목 맨 앞**에 "사연 채널 #N" 형태로 붙이고, TikTok/IG 캡션 첫 줄에도 자연스럽게 녹인다(예: "사연 채널 #42 — <hook line>"). 명언·키즈는 회차번호 대상 아님(명언은 요일 테마·키즈는 자체 시리즈명 사용).
- 번호는 `parse_upload_meta.py`가 `_pubmeta.json` 작성 시 **자동으로 다시 계산해 고정**한다(위 커맨드로 미리 확인한 값과 동일 — 세션 중간에 다른 사연이 끼어들지만 않으면 일치). 한 세션에서 여러 사연을 순차로 낼 땐 매번 새로 조회할 것(값이 밀림).
- 왜: [[channel-roi-audit]] 전환장치 3종 중 하나 — 독립 사연(Sniper 원칙 유지)이어도 순번을 매겨 "이어지는 프로그램"으로 인식시켜 재방문(구독) 동기를 만든다.

## ★고정댓글 문구 (pinned_comment, 사연·명언 — 전환장치 2026-07-09)

`02_step3_narration.txt`의 **CTA 질문 라인**(다음편 떡밥 라인 말고, 그 앞의 질문형 문장)을 거의 그대로 가져와 `07_upload_meta.md` 헤더에 다음 줄로 추가한다:
```
**댓글고정문구**: <CTA 질문을 댓글용으로 살짝 다듬은 한 문장>
```
예: 나레이션 CTA가 "여러분이라면 위자료를 포기하시겠어요, 끝까지 받아내시겠어요?"면 → `**댓글고정문구**: 여러분이라면 위자료 포기 vs 끝까지 받아내기, 어느 쪽?"` 처럼 댓글창에 바로 붙여도 되는 짧은 형태로. 이 필드가 없으면 `parse_upload_meta.py`가 `_warnings`에 경고를 남긴다. 게시(수동)가 게시 직후 이 문구를 고정댓글로 올린다(첫 60분 댓글속도=초기 추천 트리거, [[channel-growth-playbook]] §4).

## ★정보검증출처 (info_source, 정보형 사연 전용 — `docs/PRACTICAL_INFO_FORMAT.md`)

`00_meta.json`에 `story_type: "practical_info"`가 있으면 07 헤더에 다음 줄을 반드시 추가한다:
```
**정보검증출처**: <WebSearch로 확인한 기관 홈페이지/검색 쿼리 + 확인 날짜>
```
예: `**정보검증출처**: 대한법률구조공단 공식 사이트(www.klac.or.kr) 대표번호 132, 2026-07-14 WebSearch 확인`

이 필드가 없으면 `parse_upload_meta.py`가 `_warnings`에 "미검증 정보 게시 금지" 경고를 남긴다(코드 게이트, `scripts/parse_upload_meta.py` process() 참조). 없이 게시하지 말 것.

**고정댓글 확장**: 정보형 사연의 고정댓글엔 영상 내 압축 문구(기관명+번호)보다 자세한 내용을 담는다 — 관련 법조항, 신고·상담 절차(단계별), 상담 가능 시간대. 반드시 "참고용" 또는 "법률 자문"이라는 표현을 포함해 안전고지를 남긴다(빠지면 역시 `_warnings`에 경고).

## 캡션 자동 생성 패턴


### TikTok 캡션 (검증 패턴)
```
<title_short> — <hook line 1>

<key_details 4-5개 짧은 라인>

<chorus 1-2줄 인용>

<outro 1줄 인용>

🤖 이 영상은 AI(ACE Step·ElevenLabs·Gemini·Veo)로 생성·편집되었습니다.
※ 본 영상은 각색된 사연이며, 실제 인물/단체와 무관합니다.

#사연 #<category 한자> #<emotion 핵심> ... #AI영상 #AI콘텐츠 #AIcontent
```

### YouTube 일반 영상 (≤60s 한도 초과 시)
```
제목: <hook 강조 + AI 각색 사연 표시>
설명: 가사 본문 풀어쓰기 (사연 형식, 긴 글)
태그: #사연 #<category> ... (#shorts 제외)
```

### Instagram Reels (90s 표준 / 확장 130s+)
```
<hook 1-2줄>
<key 메시지 4-5줄>
<chorus + outro 인용>
🤖 AI 생성 표시
#사연 ... #reels #릴스
```

## 자동 채움 필드

| 필드 | 자동 채움 |
|---|---|
| 영상 파일 | `06_render_flow.mp4 (130.0s · 1080×1920 · 66.1MB)` |
| 길이 | `00_meta.target_duration_sec` 또는 ffprobe 측정 |
| 플랫폼 호환 | platform_check 결과표 |
| 각색 검증 | `00_meta.key_details` 기반 (실명·브랜드·지역 자동 체크) |
| 핵심 훅 | `00_meta.hook_sentence` |
| BGM 메타 | `03_audio_meta.request` (genre, BPM, key, style_ref) |
| 해시태그 | **니치 우선·각 플랫폼 최대 8개** (2026-06-22 완화 — count는 도달 레버 아님). broad 필러(#fyp #추천 등) 제거, category+tone+format+AI라벨+니치타겟 |
| 썸네일 추천 | scene_plan 기반 또는 핵심 시점 (Hook, Chorus, Outro) |
| 회차번호 | `parse_upload_meta.py --next-episode` (사연 전용, ★전환장치) |
| 고정댓글 문구 | `02_step3_narration.txt` CTA 질문 라인 축약 (사연·명언, ★전환장치) |

## 표준 출력 구조 (chinjeong/dirty 검증)

```markdown
# 07_upload_meta.md — 업로드 정보 (<slug>)

> 프로덕션: `<slug>`
> 영상 파일: `<file>` (<duration>s · 1080×1920 · h264+aac · 30fps · <size>MB)
> 기반 정책: `docs/CHANNEL_POLICY.md`
> 작성: <date>

---

## 🚨 업로드 전 꼭 읽기
### (1) 자동 업로드 없음
### (2) 규격 호환성 매트릭스 (<duration>s)
### (3) 각색 검증

## 🎵 TikTok
### 캡션 / 플랫폼 설정

## 📺 YouTube
### 제목 / 설명 / 플랫폼 설정

## 📸 Instagram Reels
### 캡션 / 플랫폼 설정

## 🎵 플랫폼별 음원 추천 ⭐ NEW (모든 production 필수)
### TikTok: 검색 키워드 + 카테고리 + 구체 곡 후보 + 음량 설정
### Reels: 동일 구조
### YouTube Shorts: 동일 구조
### 트렌딩 사운드 찾는 법

## ✅ 업로드 전 최종 체크리스트

## 📎 메타 요약

## 🆕 <slug> 사이클 메모
```

(상세 구조는 `productions/<예시_production>/07_upload_meta.md` 참조 — 검증 템플릿)

### 🎵 음원 추천 섹션 자동 생성 가이드 (모든 production 필수)

**삽입 위치**: `## ✅ 업로드 전 최종 체크리스트` 직전

**영상 톤별 키워드 매트릭스** — `00_meta.narration_tone` + `emotion` 기반 자동 매칭:

| 영상 톤 | TikTok 키워드 | Reels 키워드 | Shorts 키워드 | 음량 (Original/Music) |
|---|---|---|---|---|
| 잔잔·귀여움 (milk_sleep 류) | lo-fi cute pet, sleepy puppy, cozy ambient, aesthetic | wholesome pet, soft acoustic cute, lullaby | lo-fi beats, cute background, relaxing | 80-100% / 20-30% |
| 격렬·코믹·사고뭉치 (junja_yorkie 류) | ukulele bouncy, playful funny pet, hyper happy, chaotic comedy | quirky upbeat, bouncy comedy | comedy background, upbeat ukulele | 80-100% / 30-50% |
| 반전·정·비포애프터 (minam_cat 류) | throwback then and now, memory transition, funny cat, nostalgic cute | then now reveal, wholesome reflective | nostalgic lo-fi, cat funny background | 80-100% / 25-40% |
| 분노·각성 (chinjeong 류) | intense dramatic, anger no copyright, justice music | dramatic emotional, serious | dramatic instrumental, intense | (보통 가사 곡 사용, 음원 추가 X) |
| 코믹·체념 (dirty 류) | comedy resigned, sarcasm humor, ironic upbeat | resigned comedy | comedy ironic | (보통 가사 곡 사용) |
| 슬픔·결단 (hyungbu 류) | sad emotional, decision moment, contemplative | melancholy, reflective sad | sad instrumental, emotional | (보통 가사 곡 사용) |
| 위로·감동 (puppy_rescue 류) | wholesome rescue, emotional pet, warm story | uplifting wholesome, heartwarming | uplifting emotional, heartwarming | (보통 가사 곡 사용) |
| 향수·세대공감 (paper_master 류) | nostalgic 90s, generation memory, throwback emotional | retro emotional | nostalgic instrumental | (보통 가사 곡 사용) |

**구체 곡 후보 (저작권 무료 — 모든 톤에 활용)**:
- Bensound: Acoustic Breeze / Sunny / Funny Song / Ukulele / Buddy / Happiness / Cute
- Twin Musicom: Italian Afternoon
- Audionautix: Carefree / Cheerful
- YouTube Audio Library → Music for Shorts

**음량 가이드 (공통)**:
- Original sound (narration/가사) **반드시 80-100%** — narration 보존이 핵심
- Added music: 톤에 따라 20-50% (잔잔할수록 낮게, 격렬할수록 살짝 높게)

**트렌딩 사운드 찾는 법 (공통)**:
1. TikTok: 사운드 옆 ↑ = 트렌딩
2. 사용 영상 수 1,000-100,000 사이가 sweet spot
3. 영상 길이 매칭 (30s/60s)
4. 비슷한 카테고리 인기 영상의 사운드 분석
5. 2-3개 시도 후 도달 비교

## 출력 형식

```
✅ 07_upload_meta.md 작성 완료
📁 productions/<slug>/07_upload_meta.md

| 플랫폼 | 호환 | 비고 |
|---|---|---|
| TikTok | ✅ | <duration>s OK |
| Reels | <status> | <note> |
| YouTube Shorts | <status> | <note> |

자동 추출:
- 핵심 훅: <hook_sentence>
- BGM: <genre> <BPM>BPM
- 해시태그 N개

다음 단계:
- 사용자 캡션 검토 (수정 가능)
- Git push
- **게시 → 게시(수동) <slug>`** (3플랫폼 반자동, 파일 드롭만 사용자 / 캡션·AI라벨·게시 자동)
```

## 🔁 기계 구조화 — `_pubmeta.json` (2026-06-15 신설, 필수)

07_upload_meta.md(사람용 Markdown) 작성 **직후 반드시** 파서를 돌려 기계용 JSON도 같이 남긴다.
이게 업로드 자동화의 선결 과제 — 메타가 Markdown에만 있으면 게시 도구가 매번 화면 보며 파싱해야 해 토큰을 먹는다.
```bash
.venv/bin/python scripts/parse_upload_meta.py <slug>   # → productions/<slug>/_pubmeta.json
```
- 산출: `{slug, video, channel, channel_handle, channel_id, made_for_kids, ai_label, visibility, facebook_crosspost, pinned_comment, episode_number(사연만), platforms:{youtube{title,description}/tiktok{caption}/instagram{caption}}, _status, _warnings}`.
- **`_status: ok`** = 현행 포맷 정상 파싱. 게시 도구/향후 userscript가 이 JSON을 읽어 폼을 채움(스샷·md파싱 불요).
- 헤더에 **`**채널**: <이름> @handle`** 한 줄을 꼭 넣을 것 — 없으면 `channel/channel_id`가 null이 되고 `_warnings`에 "채널 미지정"이 뜬다(YT URL 직행에 channel_id 필요).
- 헤더에 **`**댓글고정문구**: <문구>`** 한 줄도 꼭 넣을 것(사연·명언 — ★전환장치) — 없으면 `_warnings`에 뜬다. `episode_number`(사연)는 md에 안 적어도 파서가 자동 배정(위 §회차번호).
- `00_meta.json`의 `made_for_kids`로 아동용을 교차검증한다(불일치 시 _warnings).

## 절대 하지 말 것
- 가짜 데이터 자동 채움 (모든 필드는 실제 production 자료 기반)
- **`_pubmeta.json` 생성 누락** (07 작성 후 파서 필수 — 안 돌리면 게시 도구가 구조화 메타 못 읽음)
- 각색 검증 자동 통과 (실명·브랜드 등 의심 항목 발견 시 사용자 알림)
- `#shorts` 태그 (60초 초과 영상에)
- **태그 9개 이상 / broad 필러(#fyp #추천 등)** — 정책 = 니치 우선·플랫폼당 **최대 8개**(2026-06-22 완화). 작성 후 `python scripts/parse_upload_meta.py --lint`로 백스톱 검사(>8 또는 broad 필러 경고).
- **명령형 CTA**('저장하세요/공유하세요/태그 10명') — engagement-bait 도달 강등. 질문형 1줄("당신이라면?")만.
- **회차번호 누락**(사연) — 캡션 작성 전 `--next-episode` 조회 없이 그냥 진행 금지(★전환장치).
- **고정댓글 문구 누락**(사연·명언) — `**댓글고정문구**:` 헤더 없이 07 작성 금지(★전환장치, `_warnings`로 백스톱됨).

## 태그 선정 우선순위 (니치 우선·최대 8개, 모든 플랫폼 공통)

1. **카테고리 핵심** — `#명절` `#결혼` `#사연` 등 키워드
2. **콘텐츠 톤** — `#인디발라드` `#잔잔` `#코믹` 등
3. **사연 형식** — `#사연` `#vlog` `#릴스` 등 플랫폼별
4. **AI 라벨** — `#AI영상` `#AI콘텐츠` (사연/키즈 필수, 명언 불요)
5. **니치 타겟 키워드 1~4개** — 검색 유도 정밀태그 (`#막장사연` `#시댁` `#반전결말` `#명절스트레스` 등)

→ **count는 도달 레버가 아님**(2026-06-22 팩트체크): 광범위 인기태그·broad 필러(`#fyp` `#추천` `#viral`)는 도달 기여 ~0 → **제거**. 니치 정밀태그로 8개 이내. 무리해 8개 채우지 말 것(명언처럼 3~4개도 OK).

## 참조
- 후행: 게시(수동) — 생성된 캡션으로 3플랫폼 반자동 게시 (게시 실행 = 이 스킬, "자동 업로드 없음"은 이제 게시 도구로 대체)
- `productions/<예시_production>/07_upload_meta.md` — chinjeong 검증 템플릿
- `productions/<예시_production>/07_upload_meta.md` — dirty 검증 템플릿
- `docs/CHANNEL_POLICY.md` — 각 플랫폼 정책 + 각색 §2
- `docs/PRODUCTION_PLAYBOOK.md` §9 — 업로드 정책
