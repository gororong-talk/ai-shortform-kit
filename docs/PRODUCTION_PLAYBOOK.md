# 🎬 PRODUCTION_PLAYBOOK.md — 사연 → 숏폼 영상 생산 표준 절차

> 한 production 을 처음부터 끝까지 끌고가는 **검증된 단계별 가이드**.
> chinjeong_gift (`202604251015_chinjeong_gift`) 작업에서 모든 실패와 해결책을 정리.
> 다음 production 시작 전 **반드시 이 문서 통독 + KNOWN_PITFALLS 섹션 체크**.
>
> 마지막 갱신: 2026-05-31 (쭌빠 채널 운영 기준 v1 통합 / 13 production 누적)
> 검증 기반: 13 production (chinjeong → eonni_uphill A/B) — 청춘의_청구서, acestep_demo 부분 참고

---

## 🧭 채널 운영 기준 (쭌빠 채널 v1 — 최상위 규칙)

> 출처: SNS 채널 운영 가이드 (2026-05-31 수용). 본 섹션은 개별 production 단계보다 **상위**다.
> 검토 결과: 12개 조항 중 **10개 수용**, 2개 보류 (아래 ⏸️ 참조).

### 운영 전제 (확정)
- **사연 1건 = 1포맷** 만 만들어 3플랫폼 크로스포스트 (두 포맷 동시 제작 ❌ = 비용·시간 낭비). 기본 포맷 = **나레이션** (인하우스·저비용·BGM 외주 불필요).
- TikTok 은 **무료 크로스포스트**로만 유지 (나레이션이 TikTok 완주율은 불리하나 비용 0 + 도달 작은 플랫폼이라 손실 제한적).
- YT Shorts·IG Reels = 동일 영상 크로스포스트, **YouTube 최적화 우선**.
- **Sniper 유지**: 고품질 1건 → 1영상. 대량 생산 X.
- **장르 = 드라마 단일** — *정의*: "서사·갈등·정서 곡선이 있는 사연". 시댁·결혼·가족 갈등 ✅ / 반려동물 **감동 서사** ✅ (hongi_rescue, puppy_rescue) / 반려동물 **순수 코믹** ⚠️ (junja, pudel — 드라마 경계, 신규는 지양).
- **안전 게이트 통과 못 하면 제작 중단** (명예훼손·마녀사냥 거부).

### §A. 정책 생존 규칙 (수익화 차단 방지 — 최우선) ⭐
드라마 + AI 보이스 + AI 이미지 = 플랫폼 "AI 슬롭" 1순위 표적. 못 채우면 그 영상 폐기.
- [ ] 원문 낭독 ❌ → 구성·대사·전개가 원본과 다르게 **각색**됐나 (이미 적용: 가사·나레이션 전부 재구성)
- [ ] ⏸️ **"이미지 슬라이드 + TTS" 형태 ❌** → 장면 연출·컷 전환·시각 스토리텔링 있나 — **보류 (① 결정 대기)**: 현재 Ken Burns 슬라이드쇼가 이 기준 미달. 해결 방향 결정 후 본 항목 활성화.
- [ ] 같은 템플릿 기계 반복 ❌ → 오프닝·구성·연출에 식별 가능 변주 있나 (Ken Burns 라운드로빈 = 변주 약함, ①과 연동)
- [ ] 조회수만 노린 게 아니라 감정/재미의 실질 가치를 주나

### §B. 개인정보·명예훼손 게이트 (드라마 특화) ✅
- [ ] 실명·지명·소속·날짜 등 특정 식별자 제거/변경했나
- [ ] 특정 실존 인물·업체 알아볼 수 있나 → 알아보면 각색 강화
- [ ] 원작성자 글 통째 복제 아닌가 (모티프 차용 vs 복제)
- [ ] 단정적 사실 주장 대신 "각색·픽션" 프레이밍 있나

### §C. 제작 게이트 (업로드 전) ✅
- [ ] **첫 3초 훅**: 첫 컷에서 갈등·긴장·궁금증 즉시 (도입 설명 ❌) — pudel/eonni 충격 압축형 패턴
- [ ] **길이**: 이야기가 결정, **짧고 꽉 차게** 우선. 늘어지면 완주율 사망. 60s+ 는 틱톡 수익화 자격 라인 (습관화 권장, 단 우리 도달 데이터상 길이=도달 상관 약함)
- [ ] **중간 이탈 방어**: 30~40초 텐션 장치 (반전 예고·질문)
- [ ] **엔딩**: 완결 또는 다음 편 후킹

### §D. 측정 루프 (북극성 = 완주율 / 시청 유지율) ✅ 활성
- [x] ✅ **완주율 측정 — 가능 확정 (2026-05-31)**: Chrome MCP + TikTok Studio 로그인 세션으로 영상별 완주율·평균시청·이탈지점 자동 수집. `analytics/` 시스템 (analytics_db/ingest/report). 경로: `analytics/content` → "데이터 보기" → `/analytics/{video_id}/overview` → get_page_text.
- [x] **포맷×플랫폼 상호작용 = 1순위 변수** (양 플랫폼 실측) → `memory/retention_insights.md`
  - **TikTok (완주율, 13개)**: 가사곡 6.2~14.6% >> 나레이션 0.8~2.7% (junja 15% 예외). → TikTok 단독 최적화라면 가사곡.
  - ⚠️ **두 지표는 정의가 달라** (TikTok 완주율 ≠ YouTube 평균조회율) 직접 비교 금지 — 모순 아님, 플랫폼별로 유리 포맷이 갈린다.
  - **신규 production 기본 = 나레이션** (앵커가 YouTube/IG). 비용·속도 + YouTube 리텐션 우위. (TikTok 한정이면 가사곡이 맞으나 앵커 아님)
  - **첫 2초가 공통 관문** (전 영상 0:01~0:02 이탈) → 08_image S01-S02 가장 역동적 컷
  - 슬라이드쇼 자체는 OK. 전면 Flow 영상화 불필요.
- [ ] 완주율 상위 영상 공통점 기록 (소재/훅/길이/구조)
- [ ] 이탈 급감 구간 → 다음 영상 보강
- [ ] 상위 패턴 복제, 하위 폐기
- 조회·좋아요·팔로워 = **후행 참고용** (북극성 아님)

### §E. 운영 리듬 ✅
- **빈도**: 주 1~2회 (품질·HITL 안 무너지는 선). 무리한 양 증가 X (§A 충돌).
- **분석**: 주 1회 상위/하위 리뷰.
- **플랫폼 우선순위**: YouTube/IG 앵커 + TikTok 무료 크로스포스트 (2026-06-03 전환 — YouTube 도달·나레이션 리텐션 우위 근거). 나레이션 포맷의 YouTube 추세를 2~3주 관찰해 표준 확정.

### 📊 주간 측정 기록표 (`docs/WEEKLY_METRICS.md` 에 누적)
| 영상 | 길이 | 소재유형 | 훅방식 | 완주율 | 이탈구간 | 메모 |
|---|---|---|---|---|---|---|

### ⏸️ 보류 2건 (결정·테스트 후 활성화)
| # | 항목 | 상태 | 선결 조건 |
|---|------|------|----------|
| ① | 이미지 슬라이드+TTS → 영상 연출 전환 | 🔴 결정 대기 | 슬라이드쇼 절충(xfade+모션+핵심컷 Flow) vs 전면 Flow 영상 — 비용 범위 결정 |
| ② | 완주율 북극성 측정 | 🟡 테스트 대기 | TikTok Studio retention 데이터 접근 가능 여부 캡처 확인 |

### 현실 기대치
초반 수십 개는 캘리브레이션 구간, 대부분 묻힌다. 한 방 없음. **잘된 영상 분석 → 복제 루프**가 채널 성장 엔진. 수익화는 루프의 결과.

---

## 📋 0. 시작 전 체크리스트

- [ ] `.env` 의 `GOOGLE_API_KEY`, `ACESTEP_API_KEY`, `ELEVENLABS_API_KEY` 모두 활성
- [ ] Flow 크레딧 잔액 확인 (1 production = 약 200~280 크레딧 + reference 이미지 ₩504)
- [ ] 디스크 여유 5GB+ (Flow 클립 19개 + 합성본 ~700MB / production)
- [ ] `docs/KNOWN_PITFALLS.md` 또는 본 문서 §10 (체크리스트) 1회 통독
- [ ] `references/` 의 lyrics good/bad 누적 확인 (5개 이상이면 자동 reference 주입 활성)

---

## 🎯 1. 사연 선택 + Step 0 (PD/훅)

**도구**: `python run_master.py` 또는 `skills/story_scorer.py` (CVDE 스코어링)

**확인:**
- [ ] CVDE 스코어 80+ 권장
- [ ] 안전 필터 (`is_defamation`, `is_meaningless_meme`) 통과
- [ ] 1인칭 단일 시점 명확 (Sniper 원칙)
- [ ] **선명한 위선/모순 또는 폭발 지점 1개** (3초 훅으로 쓸 만한 라인 추출 가능해야)

**산출**: `productions/<slug>/00_meta.json` (title, hook_sentence, narration_tone, target_duration_sec)

---

## 📝 2. Step 1-2 (Research + Treatment)

기존 `skills/content_generation.py` 흐름. 변경 없음.

**산출**: `01_step3_narration.original.json` (Step3 입력용 트리트먼트)

---

## 🎤 3. Step 3 — 가사 (가장 중요)

### 3.1 가사 작성 원칙 (청춘의_청구서 패턴 = 검증된 OK 표준)

| 요소 | 사양 | 예시 |
|---|---|---|
| **구조** | **8 섹션 기승전결** — Intro / Verse1 / Verse2 / Pre-Chorus / Chorus / Verse3 / Bridge / Outro | (chinjeong iter3 참조) |
| **라인 길이** | **5~7 음절/라인** 규율 | "각자 돈 각자 관리" (8자 — 한계) |
| **섹션 디렉티브** | 각 섹션마다 보컬 지시 메타 태그 | `[Intro - solo female intimate confession]` |
| **직접 인용** | 핵심 갈등 라인 1-2 개 큰따옴표로 | "돈이 썩어나는 모양이야" |
| **후렴 반복** | 핵심 메시지 3회 반복 | "이제 나도 외동" × 3 |
| **신체 묘사** | 감정의 신체화 1-2 개 | "손이 부르르 떨려 / 가슴이 쿵 떨어져" |
| **운율 시도** | 끝 운율 / 어미 일치 | "버럭하던 그 입으로 / 자랑하던 그 입으로" |
| **영문 마무리** | Outro 라인에 1줄 | "I won't hold back for you anymore" |

### 3.2 게이트 사이클

```bash
# 가사 작성 후
python scripts/iterate_step3.py --production <slug> --show

# 사용자 OK
python scripts/iterate_step3.py --production <slug> --decision OK \
    --note "iter1 청춘의 청구서 패턴 적용"

# 사용자 NG
python scripts/iterate_step3.py --production <slug> --decision NG \
    --tags hook_weak,emotion_flat,generic,rhyme_poor \
    --note "구체적 사유"
```

**3회 NG 도달 시** → Hybrid 모드 자동 트리거 (사용자 후크 1-2줄 직접 작성)

### 3.3 ⚠️ chinjeong_gift 에서 배운 교훈

- **iter1 실패 사유**: 줄거리 요약체로 작성 (8섹션 구조 무시) → hook_weak + emotion_flat + generic + rhyme_poor 4태그 NG
- **이번에는**: **처음부터 8섹션 구조로 작성**. 줄거리 요약체 출발 금지.
- **외부 클로드/세션 통합 가능**: indie acoustic 톤으로 다른 세션이 더 잘 만들면 그걸 가져와서 통합 가능 (`02_step3_narration.iter*` 백업)

---

## 🎵 4. BGM 생성 (외부 도구 선택 자유 — FC-028 이후)

> **2026-05-14 갱신 (FC-028)**: `api.acemusic.ai` 5일째 다운 + 로컬 ACE Step 톤 변경 시 잡음. **사용자 외부 작업 패턴 (옵션 4) 정착**:
> - ACE Step v1.5 cover mode (회복 시)
> - **Gemini Lyria** (puppy_rescue 사이클로 검증, FC-028 임시 폴백)
> - Suno / Udio / 기타 외부 도구
> - 사용자가 청취 + 도구별 결과 비교 + 선택. 메인 세션은 객관 측정만 (mean dB, 다이내믹 범위, silencedetect).

### 4.0 BGM 생성 (ACE Step v1.5 — 회복 시 기본)

### 4.1 장르 결정 — 사연 정서 매칭

**현재 검증된 매칭**:

| 사연 정서 | 장르 | 예시 |
|---|---|---|
| 분노 + 결심 (강렬한 폭발) | K-Trap 120-130 BPM | (memory: bgm_template) |
| **고백 + 각성 (잔잔한 빌드업)** | **Korean indie acoustic pop** (폴킴/이무진/죠지 톤) BPM 100-110 D-major | **chinjeong_gift** ⭐ |
| 슬픔 + 회한 | Indie ballad 70-90 BPM | (미검증) |

**중요**: 사연이 indie acoustic 톤인데 K-Trap 으로 만들면 사용자 청취 평가에서 NG. **사용자 톤 평가 필수.**

### 4.2 명령어

```bash
python scripts/generate_bgm.py --production <slug>
```

`03_audio_meta.json` 의 `request.prompt` 를 장르에 맞게 수정 후 실행.

### 4.3 게이트

```bash
python scripts/iterate_song.py --production <slug> --show
python scripts/iterate_song.py --production <slug> --decision OK|NG --tags ... --note "..."
```

태그: `melody_dull` `bpm_wrong` `vocal_off` `lyrics_mismatch` `mood_wrong`

### 4.4 ⭐ 외부 음악 전담 세션 통합 워크플로우 (권장)

> chinjeong_gift 검증: 음악 한 단계만 전담하는 별도 클로드 세션이 우리 멀티태스크 세션보다 일관되게 더 나은 곡을 생성. 포커스 차이가 핵심.

**왜 분업이 좋은가:**
- 전담 세션은 한 곡에 3-10회 시도 + prompt 정교화 + seed 비교 가능 (우리는 보통 1-2회)
- 가사 ↔ 음악 동시 최적화 (음절 안 맞으면 가사도 수정)
- 우리 세션은 영상·자막·합성에 집중 가능

**워크플로우:**

```
[여기]                  [음악 전담 세션]              [여기]
사연 선택               ↓                            ↓
Step 1-2                가사 받기                    03_audio.mp3 받기
Step 3 가사 OK ──→     음악 생성·시도·다듬기         + 표준 5종 자료
                        ↓                            ↓
                        OK 곡 + 메타 전달  ──→      §5 STT (initial_prompt)
                                                     §6 ~ §8 진행
```

**전담 세션에 전달할 입력:**

```
1. 가사 본문 (8섹션 + 5-7음절 + 직접인용 + 후렴 + 영문 마무리)
   — 우리 §3.1 표준 형식
2. 사연 정서 키워드 (예: "고백·각성", "분노·결심", "슬픔·회한")
3. 핵심 정체성 1줄 (예: "남편 위선 발견 후 외동으로서 자기선언")
4. 추천 장르 매칭 (우리 §4.1 표 기반 후보 1-2개)
5. 길이 목표 (60s/90s/130s 등)
```

**전담 세션에서 받아올 표준 5종 자료** (재현·디버깅용):

| 파일 | 필수 내용 |
|---|---|
| `03_audio.mp3` | 최종 곡 |
| `02_step3_narration.txt` | **8섹션 태그 포함 가사** (섹션 디렉티브 + 보컬 무드 메타) |
| `03_audio_meta.json` | `request.prompt`, `bpm`, `key`, `duration`, `style_ref` 배열, `seed`, `vocal_language` |
| `03_audio_response.json` | ACE Step 원본 응답 (audio_codes 등) |
| `03_audio_README.md` | 어떤 시도 끝에 이게 채택됐는지 메모 |

**통합 시 체크리스트:**

```bash
DST="productions/<slug>"

# 1. 5종 파일 복사
cp <외부_세션_경로>/FINAL_*_1.mp3            $DST/03_audio.mp3
cp <외부_세션_경로>/FINAL_*_lyrics.txt       $DST/02_step3_narration.txt
cp <외부_세션_경로>/FINAL_*.json             $DST/03_audio_response.json
cp <외부_세션_경로>/README.md                $DST/03_audio_README.md
# 03_audio_meta.json 은 외부 메타를 우리 스키마에 맞춰 작성

# 2. 옛 곡 백업 (있다면)
mv $DST/03_audio.iter_old.mp3 $DST/_backup_*/
mv $DST/02_step3_narration.iter_old.txt $DST/_backup_*/

# 3. 03_audio_meta.json 의 measured 필드 추가
# (effective_end_sec, tail_silence 등 — make_animated_clip.py 가 읽음)

# 4. 게이트 등록
python scripts/iterate_song.py --production <slug> --decision OK \
    --note "외부 전담 세션 통합 — <장르> <BPM>BPM <key>"
```

**chinjeong_gift 통합 사례 참조**: `productions/<예시_production>/03_audio_meta.json` 의 `notes` 필드 + `_backup_iter2_ktrap/` 구조.

**자체 생성 vs 외부 통합 결정 기준:**

| 상황 | 추천 |
|---|---|
| 빠른 반복 / 실험 / 첫 production | **자체 생성** (우리 §4.2) |
| 품질 우선 / 게시용 / 검증된 사연 | **외부 전담 세션 통합** (§4.4) |
| 음악 톤 결정 어려움 (어떤 장르?) | **자체 생성으로 1차** → 사용자 청취 → 안 맞으면 외부 전담 |

---

## 🔍 5. STT (가사 ↔ 시간 정렬)

### 5.1 ⚠️ chinjeong_gift 의 큰 함정

- 단순 `python scripts/generate_timing.py` 로는 **indie acoustic 가사 인식률 23%** (10/44 라인만 잡힘)
- 원인: 노래(sung) 보컬은 spoken-word 보다 발음이 모호 → whisper 인식 실패

### 5.2 표준 절차 (반드시 이렇게)

```python
# /tmp/retry_timing.py 또는 generate_timing.py 호출 시 다음 옵션 강제:
model.transcribe(
    str(audio),
    language="ko",
    vad_filter=False,                # 노래 무성 구간을 끝으로 오인 방지
    initial_prompt=lyrics_text,       # 02_step3_narration.txt 본문 주입
    word_timestamps=True,
    temperature=0.0,
    condition_on_previous_text=True,
)
```

### 5.3 후처리 — Gemini 교정 + 멀티라인 분할

**3.1 Gemini 텍스트 교정** (`/tmp/correct_timing.py` 패턴):
- whisper 가 받아쓴 부정확한 텍스트를 원본 가사 라인으로 매칭
- 타임스탬프는 그대로 유지

**3.2 멀티라인 분할** (`/tmp/split_segments.py` 패턴):
- Gemini 가 종종 한 세그먼트에 여러 라인을 `\n` 으로 묶음
- 라인별 분할 + 음절 수 비례 시간 배분 필수
- 안 하면 자막이 한 화면에 4-5줄 겹쳐 표시됨 (chinjeong 1차 실패 사례)

**산출 timing.json 필수 필드**:
- `total_segments`, `audio_file`, `full_text`, `segments`
- `language`, `language_probability`, `duration`

---

## 🎬 6. Scene Plan (chibi 영상용, 기존 흐름)

```bash
python plan_music_video.py --production <slug>
python make_animated_clip.py --production <slug>
```

**산출**: `06_render_chibi.mp4` (130s 기준 약 1-2시간 렌더)

**자막 위치 정책 (반드시)**:
- `make_animated_clip.py` 의 `SUBTITLE_CENTER_FRAC = 0.60` 고정
- 89% (이전 default H-200) 사용 금지 → 플랫폼 UI 가림 영역
- DARKEN 영역도 50%-72% 띠로 동기화

---

## 🎨 7. Flow 클립 생성 (선택 — 고품질 영상)

### 7.1 Reference 이미지 (₩504, 또는 매칭 시 ₩200-300)

#### 7.1.1 Step A — character_pool 매칭 시도 (`/match-characters`) ⭐

매번 9장 새로 만들기 전에 기존 풀에서 매칭 후보 검색:

```bash
python scripts/match_characters.py --production <slug>  # (Skill 백엔드)
```

매칭 알고리즘:
1. `00_meta.json` 의 등장 인물 5-6명 추출
2. `character_pool/registry.json` 에서 role + tone + category 매칭
3. 후보 3명/role 사용자 확인 (AskUserQuestion)
4. 매칭된 인물 → 그대로 활용 또는 `image-input + strict spec` 으로 표정·의상 변형 (₩56/장)
5. 매칭 안 된 인물만 새로 생성

**경제 효과 (chinjeong/dirty 검증):**
- 매칭률 50% 가정 시 ₩504 → ₩200-280 (44% 절감)
- character_pool 누적될수록 매칭률 ↑ (장기 ROI)

#### 7.1.2 Step B — 매칭 안 된 인물 신규 생성

```bash
python scripts/gen_flow_references.py --production <slug>
```

`scripts/gen_flow_references.py` 가 9장 생성 (실사 K-drama 톤):
- `zhiyoung_front`, `zhiyoung_3q`, `zhiyoung_side` (주인공)
- `husband_masked_front`, `husband_masked_smirk`, `husband_masked_side` (악역 → **가면 처리**)
- `mother_front`, `mother_side`, `mother_hands` (조연)

#### 7.1.3 Step C — 의상·각도 Variation 누적 정책 ⭐

생성된 reference 가 재사용 가치 있으면 `character_pool/<style>/` 에 등록 + registry.json 갱신.

**registry.json 확장 필드:**
```json
{
  "actor_id": {
    "style": "photoreal | chibi | webtoon",
    "tone_match": ["코믹·체념", "슬픔·결단", ...],
    "usage_history": ["202605010005_dirty_inlaws", "202605041854_hyungbu_house"],
    "reusable_as": ["며느리", "예비신부", "직장인 30대 여성"],
    "variation_paths": {
      "outfit_apron_mint": "photoreal/wife_neutral.png",       (dirty 의상)
      "outfit_casual_decisive": "photoreal/wife_decisive.png",  (hyungbu 의상)
      "outfit_office": "(향후 추가)"
    }
  }
}
```

**누적 효과 (장기):**
- 한 캐릭터당 의상·각도 5-10개 누적되면 새 production 시 거의 0원으로 reference 확보
- 사연 채널 시청자에게 "익숙한 캐릭터 재등장" 효과 (시리즈 느낌)
- 1년 후 예상 ROI: production 당 reference 비용 ₩504 → ₩100-200

#### 7.1.4 폴더 구조 (통합 후)

```
character_pool/
├── registry.json              ← 마스터 (style/tone/usage_history/reusable_as/variation_paths)
├── chibi/                     ← 117명 chibi
├── photoreal/                 ← 4명+ photoreal (dirty/chinjeong 출신 + 추가)
├── webtoon/                   ← 옵션 (K-webtoon 정상 비율, 향후)
└── sd_chibi/                  ← 옵션 (SD 만화, 향후)
```

별도: `assets/characters/` 는 chibi 영상 렌더 표정 라이브러리 (5명 × 12-13 표정), reference 풀 X.

### 7.2 ⚠️ 검증된 비주얼 톤 (chinjeong_gift)

| 시도 | 결과 |
|---|---|
| Indie watercolor | ❌ Flow 출력과 미스매치, 표정 약함 |
| Manhwa K-drama (일러스트) | ❌ Flow 가 자체 해석으로 다른 사람 그림 |
| **실사 K-drama (Sony A7S III, 35mm film)** | ✅ **검증** — Flow 자연스러운 출력과 정합 |

**Style Bible**:
```
Photorealistic K-drama cinematic still in motion, 35mm film aesthetic
Sony A7S III, 50mm f/1.8, shallow DOF, deep amber bokeh
Warm honey color grade, deep shadow contrast, slight film grain
9:16 vertical, single key light, naturalistic skin texture
```

### 7.3 ⚠️ 인물 일관성 전략 (검증됨)

| 캐릭터 | 처리 |
|---|---|
| **주인공** | 실사, 얼굴 일부 보임 OK. 옆모습/3q 위주, 정면은 1-2 클립만 |
| **악역** | **흰 세라믹 가면** (3 각도 reference) — 가면 디자인 자체에 표정 sculpted |
| **조연 (엄마/아빠 등)** | 실사, 손/뒷모습/멀리 위주 |

이유: Flow 클립 간 얼굴이 미세하게 달라지는데, 가면은 일관됨. 옆모습은 시청자가 차이를 덜 인식.

### 7.4 ⚠️ 입모양 정책 (mouth-closed, 부분 lips parted)

**원칙**: AI 비디오는 한국어 립싱크 불가능. 입모양 ↔ 가사 매칭 시도 자체를 포기.

| 분류 | 클립 수 (예시: chinjeong) | 입 처리 |
|---|---|---|
| **A. Mouth closed** | 6 | 입 굳게 닫음, 호흡만 (모든 일반 인물 클립) |
| **B. Mouth ajar** | **3** | 핵심 감정 클립만 (Chorus / 카운터 / 마무리) "lips part slightly as if exhaling held breath" |
| **C. Body only** | 9 | 가면 / 손 / 풍경 / 사물 / 뒷모습 (입 안 보임) |
| **D. 가면 (악역)** | 1 | 가면이 입 가림 |

**핵심 프롬프트 어구**:
- 일반: `mouth firmly closed throughout, no speech, no lip-sync`
- 핵심 감정: `lips PART SLIGHTLY as if exhaling a held breath, NOT syncing to any words, just an emotional release gesture`
- 절대 금지: 입 활짝 벌림, 노래하는 동작, 정확한 가사 발음 시도

### 7.5 ⚠️ AI 결함 회피 프롬프트 패턴

| 결함 | 회피 어구 |
|---|---|
| 손 추가 (3-4 hands) | `EXACTLY ONE HAND` 또는 `EXACTLY TWO HANDS belonging to the SAME person`, `no other limbs in frame` |
| 잘못된 텍스트/숫자 | `text intentionally OUT OF FOCUS / blurred`, `NO READABLE TEXT, NO numbers, NO currency symbols` |
| 외국 통화/언어 | `KOREAN` 명시 + 텍스트 흐림 강제 |
| 얼굴 확대 도구 (hoe, basket 등) | 도구 등장 시 "extreme close-up of just the hands holding tool" 대신 wider shot 또는 도구 없는 컷 |
| 인물 추가 (single → multiple) | `single subject`, `no other people in frame` |
| **만화 그래픽 효과 영구 잔존** (FC-027) | **`drawn / cloud / bubble / puff / calendar-flip` 단어 사용 금지**, 모든 인물 클립에 표준 가드 추가 (아래 참조) |
| **전자기기(노트북 등) 소품에 실제 브랜드 로고 노출** (FC-031, 2회 재발) | "no logos"만으로 부족 — `completely unbranded, plain black/silver, NO logo NO brand marks`처럼 소품 특화 문구 필수 + **생성 후 매번 육안 재확인**(1회성 아님) |
| **FLUX negative 프롬프트가 오히려 그 요소를 그림** (FC-031) | FLUX는 guidance-distilled라 negative를 무시 — `"NO glasses"` 대신 `"bare face"`처럼 항상 **positive 표현**으로 원하는 최종 상태를 서술 |

#### 7.5.1 SD chibi / 만화 인물 클립 표준 가드 (FC-027 대응)

만화 그래픽 효과 단어를 프롬프트에 넣으면 Veo 가 **정적 오버레이로 해석** → 영상 내내 떠 있는 결함. 모든 SD chibi / 만화 인물 클립에 다음 표준 가드 문구 필수:

```
ABSOLUTELY NO floating effects, NO speech bubbles, NO breath puffs,
NO sigh clouds, NO thought bubbles, NO sparkles around character,
NO emotion graphics overlaid.
```

**감정 표현은 만화 효과 대신 자연스러운 대체로:**

| 만화 효과 (금지) | 자연 대체 (권장) |
|---|---|
| 한숨 cloud / breath puff drawn | `lips slightly parted in soft exhale shape` (입 모양만) |
| 자랑 sparkle / shimmer effect | `bright warm ambient glow lighting`, `subtle uplighting` (조명) |
| 충격 emotion mark | `eyes wider with eyebrows raised high`, `frozen pose with subtle micro-shake` (표정·동작) |
| Thought bubble / question marks | `unfocused gaze looking up at ceiling`, `eyes drift slightly away` (시선) |
| Calendar-flip / date overlay | `slow camera pullback revealing parallel layered scenes` (카메라) |
| Speech bubble / text effect | `expressive body language gesture` (몸짓) |

**확인 방법**: 1차 시도 결과 영상에서 입·이마·머리 주변에 **떠 있는 그래픽**이 있으면 즉시 재시도. 0.5초 이상 정적 오버레이는 무조건 결함.

**검증 production**: `productions/<예시_production>/08_flow_clips_prompt_sheet.md` (10클립 패치 패턴 사례).

### 7.6 클립 분할 (130s 기준 19개)

| 종류 | 클립 수 | 비용 |
|---|---|---|
| Hook | 1 (3초) | 10크 |
| Main | 18 (각 7초) | 180크 |
| **합계** | 19 | **190크** |

**+ 재시도 버퍼 60-120크 권장** → 1 production 약 200-280크

### 7.7 Flow 운영

- 한 번에 **묶음 진행 권장** (4-6개씩)
- 각 클립 다운로드 시 **즉시** Downloads 에서 production 폴더로 복사 + 일관 명명 (`H01.mp4`, `C01.mp4` ~ `C18.mp4`)
- 다운로드 안 받으면 며칠 후 Flow 히스토리에서 사라짐 (chinjeong C13 사례)

### 7.8 합성

```bash
python scripts/compose_flow_clips.py --production <slug>
```

**산출**: `06_render_flow.mp4` (130s 기준 약 5-10분)

**필수 의존성**: `ffmpeg-full` (libass 포함). lite ffmpeg 는 ass 필터 미지원.

```bash
brew install ffmpeg-full  # 1회 설치
```

---

## 📤 8. 자막 + 합성 정책

| 항목 | 값 |
|---|---|
| 자막 안전 영역 (Y 위치) | `SUBTITLE_CENTER_FRAC = 0.60` (영상 높이의 60%) |
| 자막 폰트 | AppleSDGothicNeo-Bold 64pt (현재 라인) / Regular 38pt (캡션) |
| 자막 외곽선 | 4px 검정 (가독성) |
| 어둡게 띠 | y 50%-72% gradient (자막 배경) |
| Hook 큰 따옴표 | 80pt 굵게, y 45%, 1.0-2.5s |
| Hook 캡션 | 38pt, y 53%, 2.5-3.0s |

---

## 🌐 9. 업로드

### 9.1 07_upload_meta.md 갱신

영상 길이/크기/스타일 변경 시 반드시 갱신.

**필수 항목**:
- 영상 파일 (chibi or flow), 길이, 크기
- 플랫폼별 호환 (TikTok ≤10분 / Reels ≤90s 표준 / Shorts ≤60s)
- 캡션 본문 (가사 후크 인용)
- 해시태그 9개 이상
- 썸네일 추천 시점

### 9.2 Drive 동기화

```bash
```

`--copy` (안전 모드, 삭제 없음) 권장. `--sync` 는 Drive 측 옛 파일 삭제 위험.

### 9.3 플랫폼별 체크 (각 플랫폼 직접)

- TikTok: AI 생성 콘텐츠 토글 ON
- YouTube: "변경되거나 합성된 콘텐츠 포함" ON, "아동용 아님"
- Instagram: AI 정보 라벨 ON, 130s 는 확장 Reels 모드 (90s 표준 초과)

### 9.4 ⭐ 플랫폼 음원 추천 매트릭스 (BGM 없는 영상용)

> milk_sleep / junja_yorkie / minam_cat 부터 모든 production 의 07_upload_meta.md 에 자동 포함 (upload-meta skill 표준).
> Original narration **보존 필수** (음원은 보조).

#### 영상 톤별 검색 키워드 매트릭스

| 영상 톤 | TikTok 키워드 | Reels 키워드 | Shorts 키워드 | 음량 (Original/Music) |
|---|---|---|---|---|
| **잔잔·귀여움** (milk_sleep) | lo-fi cute pet, sleepy puppy, cozy ambient, aesthetic | wholesome pet, soft acoustic, lullaby | lo-fi beats, cute background | 80-100% / 20-30% |
| **격렬·코믹·사고뭉치** (junja_yorkie) | ukulele bouncy, playful funny pet, hyper happy, chaotic comedy | quirky upbeat, bouncy comedy | comedy background, upbeat ukulele | 80-100% / 30-50% |
| **반전·정·비포애프터** (minam_cat) | throwback then and now, memory transition, funny cat, nostalgic cute | then now reveal, wholesome reflective | nostalgic lo-fi, cat funny | 80-100% / 25-40% |
| **분노·각성** (chinjeong) | (보통 가사 곡 사용, 음원 추가 X) | — | — | 100% / 0% |
| **코믹·체념** (dirty) | (보통 가사 곡 사용) | — | — | 100% / 0% |
| **슬픔·결단** (hyungbu) | (보통 가사 곡 사용) | — | — | 100% / 0% |
| **위로·감동** (puppy_rescue) | (보통 가사 곡 사용) | — | — | 100% / 0% |
| **향수·세대공감** (paper_master) | (보통 가사 곡 사용) | — | — | 100% / 0% |

→ 가사 곡 사용 production (chinjeong/dirty/hyungbu/puppy/paper) 은 BGM 이 핵심이라 음원 추가 X.
→ narration-only production (milk/junja/minam) 은 음원 추가 권장.

#### 구체 곡 후보 (저작권 무료)
- **Bensound**: Acoustic Breeze / Sunny / Funny Song / Ukulele / Buddy / Happiness / Cute
- **Twin Musicom**: Italian Afternoon
- **Audionautix**: Carefree / Cheerful
- **YouTube Audio Library** → "Music for Shorts" → Genre 필터
- **Creator Music** (YouTube, 라이센스 자동 처리)

#### 트렌딩 사운드 찾는 법
1. **TikTok**: 사운드 옆 ↑ 표시 = 트렌딩 (알고리즘 친화)
2. **사용 영상 수** 1,000-100,000 사이가 sweet spot (너무 많으면 묻힘, 너무 적으면 알고리즘 약함)
3. **영상 길이 매칭** (30s/60s) — 트랙 트림 가능 (in-app)
4. 비슷한 카테고리 인기 영상의 사운드 분석
5. **2-3개 시도** 후 도달 비교 (alt 계정 활용)

---

## 🔁 10. 다음 production 시작 시 체크리스트 (요약)

새 슬러그 만들 때 이 순서:

```
1. /start-production               → 사연 선택 + production 폴더 생성
2. Step 1-2 진행                   (research + treatment)
3. ⭐ Step 3 가사 (8섹션 + 5-7음절 + 직접 인용 + 후렴 + 영문 마무리)
   → /iterate-step3 OK
4. /music-handoff                  → 외부 음악 전담 세션 의뢰 (선택)
5. /integrate-music                → 음악 통합 (페이드 + measured + 게이트)
   또는 /iterate-song OK
6. /correct-timing                 → STT (FC-018+019 fix)
7. /match-characters               → character_pool 매칭 + _match_plan.json
8. /generate-references            → 부족분 reference 생성 (선택, 또는 사용자 외부)
9. /import-references --mode ref   → Downloads PNG → flow_reference/ ⭐ NEW
10. /generate-flow-prompts         → 08_flow_clips_prompt_sheet.md ⭐ NEW
    (베이스 스타일 + 19 클립 프롬프트 + 안전 단어 lint)
11. (사용자 외부 Flow 19개 작업)
12. /import-references --mode clips → Downloads MP4 → flow_clips/ ⭐ NEW
13. /verify-clips                  → 19 클립 메타 검수 ⭐ NEW
    (compose 가 자동 호출 — 별도 실행 불필요)
14. /compose-final                 → 합성 (검수 + Hook + 자막 + Veo 가림 + QA 캡처)
15. /upload-meta                   → 07_upload_meta.md
17. 플랫폼 업로드 (AI 라벨 ON)
```

**Flow 클립 단계 (9-14) 자동화 효과** (hyungbu_house 검증):
- 캐릭터 매칭으로 Reference 비용 ₩504 → ₩200-300 (40-60% 절감)
- 안전 단어 자동 회피로 Veo 거부율 ↓
- compose 단계 통합 (검수 + Veo 가림 + QA 캡처) — 인코딩 1회

---

## 📚 부록 — chinjeong_gift 에서 배운 교훈 한 줄 요약

| # | 교훈 |
|---|---|
| 1 | 가사는 처음부터 8섹션 구조 + 5-7음절 라인 규율로 작성 (줄거리 요약체로 출발 금지) |
| 2 | BGM 장르는 사연 정서에 매칭 (모든 사연에 K-Trap 강제 X) |
| 3 | Whisper 노래 인식 = 23%. **반드시** initial_prompt + VAD off + Gemini 교정 |
| 4 | 자막 위치 60% 고정 (89% 는 플랫폼 UI 가림 영역) |
| 5 | Flow Reference = 실사 K-drama 톤이 가장 정합 (수채/manhwa 시도 실패) |
| 6 | 악역 캐릭터 = 흰 세라믹 가면 (일관성 + 위선의 메타포) |
| 7 | 입모양 ↔ 가사 매칭 포기. mouth-closed 기본, 핵심 감정 3클립만 lips-parted |
| 8 | 손 close-up = "EXACTLY ONE/TWO HANDS, no other limbs" 강제 |
| 9 | 텍스트/숫자는 항상 흐림 처리 ("blurred, NO READABLE TEXT") |
| 10 | Flow 클립 다운로드 즉시 production 폴더로 복사 (히스토리 휘발) |
| 11 | 합성 = ffmpeg-full 필수 (libass). lite ffmpeg 미지원 |
| 12 | 외부 클로드/세션 산출물 통합 가능 — 더 좋으면 가져와서 백업 후 교체 |

---

## 🔗 관련 문서

- `docs/CHANNEL_POLICY.md` — 플랫폼 업로드 정책
- `docs/DECISIONS.md` — 파라미터 결정 근거
- `docs/FAILURE_CASES.md` — 실패 사례집 (이 문서 §10 항목들의 상세)
- `docs/ACE_STEP_GUIDE.md` — BGM 운영 상세
- `docs/ASSET_GUIDE.md` — 캐릭터 풀/배경/폰트
- `docs/PROMPTS.md` — 단계별 프롬프트 모음
- `references/README.md` — 가사·노래 게이트 reference 라이브러리
- `productions/<예시_production>/08_flow_clips_prompt_sheet.md` — Flow 19클립 실제 프롬프트 예시 (참고용)
