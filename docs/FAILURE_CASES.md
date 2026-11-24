# 💥 FAILURE_CASES.md — 실패 사례집

> 파이프라인 운영 중 겪은 실패·버그·품질 이슈와 **원인·해결·재발방지** 기록.
> 같은 실수 반복 방지가 목적. 성공 사례보다 실패가 더 많은 정보를 담는다.
>
> 작성 기준일: 2026-04-22

---

## 🎬 영상 렌더링 관련

### FC-001: 캐릭터가 너무 큼
- **날짜**: 2026-04-21
- **증상**: 첫 렌더본에서 캐릭터가 화면 절반 이상 차지 → 자막 공간 부족, 압박감
- **원인**: `CHAR_HEIGHT_FRAC = 0.58` (기본값) — 숏폼 감도 테스트 전 추정치
- **해결**: `0.58 → 0.38`로 감소. `CHAR_CENTER_Y`도 `0.38 → 0.36` 조정해 상단으로
- **재발방지**: 새 영상 첫 렌더는 반드시 5초 프리뷰로 검증 후 풀 렌더
- **관련**: `make_animated_clip.py`, `docs/DECISIONS.md §3`

---

### FC-002: 자막 잘림 (긴 줄)
- **날짜**: 2026-04-21
- **증상**: "순간 지난밤 봤던 익명의 댓글이 떠올랐어" 같은 긴 줄이 화면 밖으로 잘림
- **원인**: 자동 줄바꿈 로직 없음. 폰트 54px × 16자 이상이면 980px 초과
- **해결**:
  1. `_wrap_text()` 함수 추가 (공백 기준 분할)
  2. `MAX_TEXT_WIDTH = 980` 상수화
  3. `SIZE_CURRENT` 60→54 감소
  4. 어둡게 처리 영역 400→520px 확대
- **재발방지**: 모든 가사 줄에 대해 렌더 전 길이 검증 루틴 추가 필요
- **관련**: `make_animated_clip.py:_wrap_text`

---

### FC-003: 영상 길이 32초로 잘려 음악 훅 실종
- **날짜**: 2026-04-21
- **증상**: "영상이 짤려서 그런지 음악이 귀에 다 안들어와" — 벌스1만 남고 브릿지+벌스2 실종
- **원인**: "숏폼 = 60초 이하" 고정관념으로 강제 컷
- **해결**: 인트로 10초만 트림, 나머지는 풀 유지 (165.74초)
- **재발방지**: 숏폼 길이 제약은 "60초"가 아니라 "훅 3초 + 완결 서사"로 재정의
- **관련**: `DECISIONS.md §2 오디오 & 인트로`

---

### FC-004: 배경이 밋밋함 (단색 그라디언트)
- **날짜**: 2026-04-21
- **증상**: "캐릭터만 나오는게 밋밋해보여, 랩을 하는데 빈 화면에 그냥 나오는 것이"
- **원인**: 초기 버전은 단색 그라디언트만 사용 (프로토타입 수준)
- **해결**: 무대 효과 시스템 구축
  - 선버스트 빔 14개
  - 파티클 55개 (6색, 2개는 순백)
  - 흰색 십자 스파클 18개
  - 무대 바닥 타원 글로우
  - 비트 펄스 가장자리 플래시
- **재발방지**: 프로토타입 "MVP"라도 배경 최소 2 레이어 필수
- **관련**: `DECISIONS.md §5`

---

### FC-005: 캐릭터 표정 바뀌어도 배경은 고정
- **날짜**: 2026-04-21
- **증상**: sly → crying 급변인데 배경은 동일 K-pop neon → 인지부조화
- **원인**: 무드 시스템이 캐릭터만 적용, 배경은 상수
- **해결**: `MOOD_CONFIG` 도입 — 11개 무드 각각에 선버스트/파티클/스파클/무대바닥/비트/틴트 매핑. `lerp_mood()`로 9프레임 크로스페이드
- **재발방지**: 감정 변화 = 배경 동조. 새 영상도 이 원칙 유지
- **관련**: `DECISIONS.md §6`

---

## 🎼 음악·오디오 관련

### FC-006: BGM 생성 곡 앞 10초가 Instrumental Buildup
- **날짜**: 2026-04-21 (Lyria 시점), ACE Step 에서도 재발 가능성 확인됨
- **증상**: 곡 시작하자마자 훅을 기대했는데 10초간 피아노 빌드업만 있어 "지루한 시작"
- **원인**: 음악 생성 모델은 곡 구조를 자율적으로 결정. 프롬프트에 "no intro" 명시해도 7/10 확률로 빌드업이 붙음
- **해결**:
  - (Lyria) `AUDIO_START_OFFSET = 10.0s` 로 오디오/영상 모두 10초 지점부터 시작
  - (ACE Step) 캡션에 `hook on first bar` + `[Intro - brief]` 또는 Intro 태그 아예 생략
- **재발방지**:
  - 생성 후 반드시 **첫 10초 들어보기**
  - 훅 지점을 수동 확인해 `03_audio_meta.json > measured.audio_start_offset_sec` 에 기록
  - ACE Step 은 멀티 시드(batch=2~3) 후 가장 intro 짧은 시드 선택

---

### FC-007: Whisper STT 한국어 랩 정확도 부족
- **날짜**: 2026-04-21
- **증상**: 일부 가사가 "아르바이트"→"아르바잇", 조사 누락 등
- **원인**: 빠른 랩 + 은어 + 한국어에 대한 Whisper의 한계
- **해결**: 원본 가사와 1:1 수동 대조하여 교정. 비용 큼 (15~30분)
- **재발방지**:
  - Whisper `large-v3` 모델 고정 사용
  - 교정 체크리스트: 조사, 은어, 단어 경계, 빠른 구간
  - **절대로 STT 결과를 검증 없이 씬 플래너에 투입하지 말 것**

---

## 🤖 AI 파이프라인 관련

### FC-008: 씬 플래너가 livingroom 남발
- **날짜**: 2026-04-21
- **증상**: 40씬 중 28씬이 livingroom (70%) → 같은 배경만 반복
- **원인**: Gemini 기본 경향: 안전한 배경 선호
- **해결**: 프롬프트에 배경 다양화 4조항 추가
  - livingroom 40% 이하
  - 동일 배경 연속 3씬 금지
  - 가사 키워드 → 배경 추론표
  - 클라이맥스는 outdoor 계열 번갈아
- **재발방지**: 새 씬 플랜 생성 후 배경 분포 자동 체크 루틴 예정
- **관련**: `PROMPTS.md §7.2`

---

### FC-009: 씬 플래너가 "남편" 언급 씬도 주인공으로 생성
- **날짜**: 2026-04-21
- **증상**: 가사 "남편이 ~"인데 화면은 주인공(f_30s) 얼굴만 나옴
- **원인**: 프롬프트에 캐릭터 전환 규칙이 모호 ("적절히 바꾸라" 수준)
- **해결**: 키워드 → chibi_type 하드 매핑 테이블 명시
  - "남편/그이/신우/아범" → m_30s
  - "시어머니/어머니/시대" → f_60s
  - "한통속" → f_60s
- **재발방지**: 새 곡마다 등장인물 키워드 테이블 먼저 만들기 (씬 플래너 입력 전)
- **관련**: `PROMPTS.md §7.1`

---

### FC-010: Gemini 씬 플래너 temperature 0.7에서 규칙 위반 빈도 높음
- **날짜**: 2026-04-21
- **증상**: 명시한 규칙을 3/10 확률로 무시 (배경 제한 등)
- **원인**: 창작 온도(0.7)가 규칙 준수에 부적합
- **해결**: `temperature = 0.3`으로 낮춤
- **재발방지**:
  - 규칙 기반 구조 생성 = 0.2~0.3
  - 창작(트리트먼트/나레이션) = 0.7~0.9
  - 가이드 정리 → `PROMPTS.md` 온도 가이드
- **관련**: `PROMPTS.md §공통 튜닝 패턴`

---

### FC-011: Claude가 코미디 장르에 억지 교훈 삽입
- **날짜**: (청춘의 청구서 이전 운영 중 발견)
- **증상**: 코미디 장르인데 결말에 "이래서 ~해야 합니다" 같은 교훈 삽입
- **원인**: 프롬프트에 "금지" 구문 없음
- **해결**: squad_prompt에 "억지 교훈이나 억지 사이다 반격을 주지 마라" 명시
- **재발방지**: 장르별 squad_prompt에 **금지 사항**을 긍정 지시보다 먼저 배치
- **관련**: `PROMPTS.md §3`

---

## 🗃️ 저장소·운영 관련

### FC-012: 초기 git staging 221MB
- **날짜**: 2026-04-21
- **증상**: 첫 `git add .` 후 221MB 스테이징
- **원인**: `.gitignore` 불완전 — `*.png`, `*.mp3`, `reference/` 누락
- **해결**: `.gitignore` 전면 재작성 (대용량 바이너리 전방위 제외) → 688KB로 축소
- **재발방지**:
  - 새 프로젝트 초기에 `.gitignore` 먼저 확정
  - `git status --short | wc -l` + `du -sh .git/` 체크
- **관련**: `.gitignore`

---

### FC-013: 치비 에셋 용량이 GitHub 무료 한도 우려
- **날짜**: 2026-04-21
- **증상**: character_pool 전체 치비를 git에 포함 시 수백 MB 예상
- **원인**: Imagen4 1024×1024 PNG가 각 500KB~2MB, 15종×11표정 = 165장
- **해결**:
  - character_pool 전체를 gitignore
  - 클라우드(Google Drive)로 동기화 예정
  - registry.json만 git에 포함 (메타데이터)
- **재발방지**: 대용량 바이너리는 **생성 가능한 에셋** → git 제외, **재현 어려운 결정** → git 포함 원칙

---

### FC-014: ACE Step Turbo tail 토큰 반복 (outro 품질 저하)
- **날짜**: 2026-04-23
- **증상**: 생성곡 마지막 5~15초에 동일 오디오 코드 반복 (`<audio_code_35847>` 패턴). 실제 오디오는 한 음이 늘어지거나 노이즈로 마무리
- **원인**: Turbo 모델이 CFG 없이 8 diffusion step 으로 빠르게 수렴하다 outro 토큰 분포가 degenerate 상태에 빠짐. LM 레이어의 EOS 타이밍 실패.
- **실측 샘플**: `chatcmpl-d7e29f8098a68b54_1.mp3` (90s 원본). audio_codes 말미에 `audio_code_35847` 21회 연속. 5Hz LM 기준 ≈ 4.2s.
- **해결 (우선순위 순)**:
  1. `batch_size=2~3` + `seed="42,123,456"` 로 **멀티 시드 후 가장 깨끗한 시드 선택** (가장 저비용)
  2. 문제 구간만 `task_type=repaint` + `repainting_start/end` (§docs/ACE_STEP_GUIDE.md §5.1)
  3. 최후: `ffmpeg -t 86 -af "afade=t=out:st=83:d=3"` 로 강제 트림+페이드 (2026-04-23 demo 적용)
- **재발방지**:
  - `scripts/generate_bgm.py --batch 3` 기본 사용 권장
  - 업로드 전 **끝 10초 수동 청취** (ASSET_GUIDE.md §10 체크리스트)
  - 장기적: tail 반복 자동 감지 스크립트 (DECISIONS.md §9.2)

---

### FC-015: generate_timing.py CORRECTION_PROMPT Python format 충돌
- **날짜**: 2026-04-23
- **증상**: `python3 scripts/generate_timing.py --production <slug>` 실행 시 `KeyError: '"start"'`. Whisper 전사는 성공하지만 Gemini 교정 호출 직전에 `prompt.format(narration=..., segments_json=...)` 단계에서 터짐.
- **원인**: `CORRECTION_PROMPT` 내부 "출력 형식" JSON 예시가 단일 중괄호 `{"start": 14.76, ...}` 로 들어가 있어, `str.format()` 이 이를 format field 로 오해하고 `"start"` 라는 이름의 key 를 찾다 실패.
- **해결**: JSON 예시의 리터럴 중괄호를 `{{` / `}}` 로 이스케이프. `{narration}` / `{segments_json}` 은 진짜 format field 이므로 단일 중괄호 유지.
  ```python
  # Before (broken)
  [{"start": 14.76, "end": 16.16, "text": "..."}]
  # After (fixed)
  [{{"start": 14.76, "end": 16.16, "text": "..."}}]
  ```
- **재발방지**:
  - f-string 대신 `str.format()` 을 쓰는 멀티라인 프롬프트에 JSON/코드 예시 넣을 땐 **중괄호 2배 escape 규칙** 체크리스트화
  - 장기적으론 prompt template 을 `string.Template` 또는 jinja2 로 마이그레이션하는 것이 안전

---

## 📋 실패 분류 통계 (작성 시점)

| 카테고리 | 건수 | 주요 원인 |
|---|---|---|
| 렌더링 품질 | 5 | 파라미터 튜닝 부족 |
| AI 출력 품질 | 4 | 프롬프트 규칙 부족 |
| 오디오 | 3 | 외부 도구 특성 + 생성 모델 수렴 실패 |
| 저장소 | 2 | 초기 설정 미흡 |
| 스크립트 버그 | 1 | Python format spec literal brace |

**패턴**: 대부분 "첫 시도 → 피드백 → 수정" 사이클. 다음 영상부터는 체크리스트(ASSET_GUIDE.md §10)로 선제 대응.

---

## 🧯 재발방지 공통 원칙

1. **첫 렌더 = 5초 프리뷰로**. 풀 렌더 낭비 방지
2. **STT 결과는 항상 수동 교정**. 검증 없이 하류 투입 금지
3. **AI 프롬프트에 금지 사항은 긍정 지시보다 먼저**
4. **생성곡(Lyria/ACE Step 불문)은 직후 첫 10초 + 끝 10초 청취** (FC-006 / FC-014)
5. **새 영상 시작 전 ASSET_GUIDE.md §10 체크리스트 확인**
6. **파라미터 변경은 DECISIONS.md §변경 이력에 반드시 기록**

---

## 🆕 chinjeong_gift 사이클 (2026-04-28 ~ 04-30)

### FC-016 — Step 3 가사 줄거리 요약체 출발

- **현상**: chinjeong iter1 가사가 8섹션 구조 없이 줄거리 요약 8문장. 게이트 4태그 NG (hook_weak / emotion_flat / generic / rhyme_poor).
- **원인**: 청춘의_청구서 패턴 reference 누적 부족 (5 미만)이라 자동 주입 안 됨. 출발 시 패턴 인식 부재.
- **해결**: iter2 8섹션 재작성 + iter3 외부 세션 통합 → OK.
- **재발 방지**: PRODUCTION_PLAYBOOK §3.1. 첫 시도부터 8섹션 + 5-7음절 + 직접 인용 + 후렴 적용.

### FC-017 — 사연 정서 ↔ BGM 장르 미스매치

- **현상**: chinjeong iter1 BGM K-Trap 자동 생성. 사용자: "고백·각성 톤엔 indie acoustic 더 어울림".
- **원인**: 모든 사연 K-Trap 강제 default. 정서별 매칭 가이드 부재.
- **해결**: 외부 indie acoustic 130s 통합.
- **재발 방지**: PRODUCTION_PLAYBOOK §4.1. 사연 정서별 장르 결정.

### FC-018 — Whisper 노래 인식률 23%

- **현상**: indie acoustic 130s 곡 default `generate_timing.py` → 10/44 라인만 인식. 30초 이후 누락.
- **원인**: VAD 가 무성을 곡 끝으로 오인 + sung vocal 모호.
- **해결**: `vad_filter=False` + `initial_prompt=lyrics` + Gemini 교정 → 93% 커버.
- **재발 방지**: PRODUCTION_PLAYBOOK §5.2. sung 곡은 강화 옵션 필수.

### FC-019 — Gemini 교정 멀티라인 한 세그먼트 (자막 4-5줄 겹침)

- **현상**: Gemini 가 `\n` 으로 묶음 → 같은 위치에 4-5줄 동시 표시.
- **해결**: 음절 비례 시간 배분 분할 (20→37 세그먼트).
- **재발 방지**: PRODUCTION_PLAYBOOK §5.3. 후처리 필수.

### FC-020 — 자막 위치 89% (TikTok/Reels UI 가림)

- **현상**: chibi 영상 자막 H-200 (Y 89%). 플랫폼 UI 가림.
- **해결**: `SUBTITLE_CENTER_FRAC = 0.60` 고정. DARKEN 50%-72%.
- **재발 방지**: PRODUCTION_PLAYBOOK §6. 상수 변경 금지.

### FC-021 — Flow Reference 스타일 표류

- **현상**: indie watercolor → 출력은 manhwa drama / 다른 인물.
- **원인**: Veo 가 reference 를 스타일 힌트 정도만 사용. 출력 자연 톤과 미스매치 시 무시됨.
- **해결**: 실사 K-drama 35mm 톤으로 reference 변경.
- **재발 방지**: PRODUCTION_PLAYBOOK §7.2. 실사 K-drama 강제.

### FC-022 — Flow 손 추가 결함

- **현상**: 엄마 손 close-up = 손 3개 + 팔 2개.
- **해결**: `EXACTLY ONE/TWO HANDS belonging to the SAME person, no other limbs in frame`.
- **재발 방지**: PRODUCTION_PLAYBOOK §7.5.

### FC-023 — Flow 텍스트/숫자 결함 (USD / 오타)

- **현상**: "Transanion Alert USD 1,500.00" / "4,999.00" — 오타 + 외국 통화.
- **해결**: 텍스트 흐림 강제 (`OUT OF FOCUS, NO READABLE TEXT, NO numbers, NO currency symbols`). 한국 컨텍스트 명시.
- **재발 방지**: PRODUCTION_PLAYBOOK §7.5.

### FC-024 — ffmpeg lite 자막 burn-in 실패

- **현상**: `Unknown filter 'ass'`. Homebrew default ffmpeg 가 libass 미컴파일.
- **해결**: `brew install ffmpeg-full` + `compose_flow_clips.py` 가 자동 절대경로 사용.
- **재발 방지**: PRODUCTION_PLAYBOOK §7.8. 신규 머신 셋업 시 ffmpeg-full 필수.

### FC-025 — Flow 클립 다운로드 누락 (히스토리 휘발)

- **현상**: C13 mp3 다운로드 깜빡 → 다음 날 Downloads 없음. 다행히 Flow 히스토리 남아있어 복구.
- **해결**: 각 클립 생성 직후 다운로드 + production 폴더 일관 명명 복사.
- **재발 방지**: PRODUCTION_PLAYBOOK §7.7.

### FC-026 — Flow 입모양 ↔ 가사 미스매치

- **현상**: 첫 manhwa husband 테스트 — 입모양 가사와 어긋나 어색.
- **해결**: `mouth firmly closed throughout, no speech, no lip-sync` 기본. 핵심 감정 3클립만 `lips PART SLIGHTLY as if exhaling, NOT syncing to any words`.
- **재발 방지**: PRODUCTION_PLAYBOOK §7.4.

---

## 🆕 dirty_inlaws 사이클 (2026-05-02 ~ )

### FC-027 — Flow 만화 그래픽 효과 영구 잔존 (sigh-puff stuck on mouth)

- **현상**: dirty_inlaws C01 시도 시 SD chibi 며느리 입에 한숨 puff cloud 가 영상 7초 내내 정적으로 떠있음. 자연스러운 흐름이 깨지고 viewer 가 "버그처럼" 인지.
- **원인**: 프롬프트에 `Small visible sigh-puff drawn near her mouth (Korean webtoon style)` 같은 만화 그래픽 효과 단어를 넣으면 Veo 가 **정적 오버레이 graphic** 으로 해석. "drawn / cloud / bubble / puff / calendar-flip / sparkles around" 같은 단어가 트리거.
- **해결**: 프롬프트에서 만화 효과 단어 제거 + 모든 인물 클립에 가드 추가:
  ```
  ABSOLUTELY NO floating effects, NO speech bubbles, NO breath puffs,
  NO sigh clouds, NO thought bubbles, NO sparkles around character,
  NO emotion graphics overlaid.
  ```
- **자연 대체 패턴 (감정 표현)**:
  - 한숨 → `lips slightly parted in soft exhale shape` (입 모양만)
  - 자랑 sparkle → `bright warm ambient glow lighting` (조명)
  - 충격 → `eyes wider, eyebrows raised high` (표정)
  - Thought bubble → `unfocused gaze looking up` (시선)
  - Calendar-flip → `slow camera pullback with parallel layers` (카메라)
- **재발 방지**: PRODUCTION_PLAYBOOK §7.5.1 (SD chibi / 만화 인물 클립 표준 가드).
- **검증 production**: `productions/<예시_production>/08_flow_clips_prompt_sheet.md` 의 10클립 패치 사례.

---

### FC-028 — ACE Step v1.5 인프라 장애 + 로컬 학습 부족 (BGM 생성 완전 차단)

- **현상 (2026-05-14 puppy_rescue 사이클 발견)**:
  1. **D 핵심**: `api.acemusic.ai` **5일째 다운** → 클라우드 호출 불가
  2. **C**: 로컬 ACE Step (맥북 MPS/MLX) 으로 톤 변경 시 (예: 여성→남성) **윙윙거리는 잡음** 심함 → 로컬 학습 덜 됨
  3. **B**: 발음 살짝 뭉개짐 (hyungbu cover mode 패턴과 유사 — 무시 수준이지만 누적)
- **원인 추정**:
  - API: ACE Step 공식 인프라 운영 불안정 (FREE 티어 우선순위 낮음 가능성)
  - 로컬: ACE Step Turbo 가 다양한 톤 (특히 남성 보컬) 학습 부족
- **영향**: BGM 생성 파이프라인 완전 차단 — chinjeong/dirty/hyungbu 까지 정상 작동했으나 puppy_rescue 부터 막힘.
- **회피책 (이번 사이클 검증)**: **Gemini Lyria 임시 폴백** (사용자 외부 작업) — 두 곡 OK 받음.
- **장기 대응 옵션**:
  1. ACE Step API 회복 모니터 (수동, 불확실)
  2. **Gemini Lyria 영구 회귀** (Gemini API 안정성 더 좋음) — `docs/DECISIONS.md §7.1` 재검토 필요
  3. 다중 폴백 (ACE Step → Lyria → Suno 등) 자동 선택 로직 구축
  4. Suno 같은 외부 도구 다변화 (사용자 외부 작업 패턴)
- **재발 방지**:
  - `_music_handoff/` 패키지에 도구 선택 (ACE Step / Lyria / 사용자 결정) 항목 추가
  - `docs/PRODUCTION_PLAYBOOK.md §4.4` 폴백 정책 명시
  - BGM 생성 결과 객관 검수 (mean dB, 다이내믹 범위, silencedetect) 표준화 — puppy_rescue 의 두 곡 비교 분석 패턴 정착
- **검증 production**: `productions/<예시_production>/` (A 곡 열다섯_해의_약속 + B 곡 십오_년의_약속, 둘 다 Gemini Lyria).

---

### FC-029 — 해시태그 '최대 5개' 정책 미준수 (전 카탈로그 17/39)
- **날짜**: 2026-06-22
- **증상**: `parse_upload_meta.py --lint` 신설 후 전수 검사 → **39건 중 17건이 플랫폼당 해시태그 6~10개**(사연 8~10 · 키즈 6). 정책(upload-meta SKILL.md:92,212 "각 플랫폼 최대 5개", 2026-05-25)이 생성 단계에서 강제된 적 없어 누적 드리프트. 대부분 이미 게시됨.
- **원인**: 정책이 사람(=Claude) 지침에만 있고 코드 가드 없음 → 캡션 생성마다 휴리스틱으로 누락. 일부는 `_source:manual`이라 파서도 안 거침.
- **해결**: `parse_upload_meta.py`에 `hashtag_warnings()` 백스톱(파싱 시 `_warnings`에 ">5" 경고) + `--lint` 전수 감사 모드(수동 pubmeta 포함) 추가. upload-meta SKILL "절대 하지 말 것"에 lint 호출 명시. **게시된 과거 17건은 수정 안 함**(라이브 미반영 + 게시기록 왜곡 방지 — 이력 보존).
- **재발방지**: 새 production은 `/upload-meta` 후 `python scripts/parse_upload_meta.py --lint`로 확인. ✅ **정책 완화 결정(2026-06-22)**: 팩트체크상 "6개+가 도달을 깎는다"는 외부 근거 없음(YT 15개 허용·count는 레버 아님) → '최대 5개'를 **니치 우선·최대 8개**로 완화(`MAX_TAGS=8`), broad 필러(#fyp #추천 #viral)는 `BROAD_TAGS`로 경고. 게시된 과거 17건은 이력 보존(미수정).

---

### FC-030 — 검증 안 된 알고리즘 '꿀팁' 추종 위험 (인스타 '인스턴트 기능' 신화)
- **날짜**: 2026-06-22
- **증상**: 마케팅 블로그가 주장한 '인스타 인스턴트 기능 토글', '저장이 최강 신호', '조회 2~4배/저장 70%/팔로워 35%', '릴스 7~12초'를 그대로 영상 전략에 넣을 뻔.
- **원인**: 한국 SEO/마케팅 블로그는 1차 출처 없는 자작 수치·존재하지 않는 기능을 '공식'처럼 서술. 자극적이라 그대로 믿기 쉬움.
- **재발방지**: 외부 알고리즘 조언은 **(강함)=플랫폼 공식·대규모 데이터일 때만** 행동 기준으로. 마케팅 블로그 단일 출처는 (약함·검증필요) 이하 → 행동 근거 금지. 의심 주장은 Workflow/deep-research 팩트체크 후 채택.

---

### FC-031 — fal FLUX 이미지에서 노트북 소품에 실제 브랜드 로고 반복 노출 (2회 재발 → 가드 승격)
- **날짜**: 2026-07-25 (serial_betrayal_divorce #53, B09) → 2026-07-28 (office_kindness_stalker #54, B08) **동일 결함 2회 재발**
- **증상**: "정보탐색(노트북 사용)" 비트 프롬프트가 노트북을 소품으로 등장시킬 때 FLUX가 뒷면에 실제 Apple 로고를 그림 — 저작권 정책(실제 브랜드 → 일반명사/무지물 대체) 위반.
- **원인**: `08_image_prompts.md`의 노트북 등장 프롬프트에 "no logos"라는 일반 문구는 있었지만, 노트북처럼 **로고가 브랜드 정체성 자체인 소품**은 일반 "no logos"만으로 FLUX가 억제되지 않음(전자기기 소품 특화 가드 부재).
- **추가 발견 (2026-07-28 재생성 중)**: FLUX는 guidance-distilled라 **negative 프롬프트를 무시**(`generate_images_fal.py` 자체 경고문과 일치) — "NO glasses" 같은 negative 표현을 넣었더니 오히려 안경을 계속 그림. positive 표현("bare face")으로 바꾸고서야 해결.
- **해결**: 두 production 모두 육안 검수에서 발견 즉시 "completely unbranded, plain black/silver, NO logo NO brand marks" 포함해 재생성(또는 최종적으로 로고 언급 자체를 빼고 순수 positive 묘사로 재작성)해 통과.
- **재발 방지 (승격, PRODUCTION_PLAYBOOK §7.5 표에 항목 추가 필요)**:
  1. **전자기기(노트북·폰·태블릿) 소품이 프롬프트에 등장하면 매번 생성 후 육안 재확인 필수** — "no logos" 문구를 이미 넣었어도 안심하지 말 것(1회성 아님, 2 production 연속 재발 확인).
  2. **FLUX 프롬프트 수정 시 "NO X" 부정 표현 금지** — 원하는 상태를 항상 positive로 서술(예: "no glasses" 대신 "bare face", "no logo" 문구 자체보다 "completely unbranded plain matte black laptop"처럼 최종 상태를 직접 지정).
  3. 이 패턴이 3번째 production에서도 재발하면 `generate_images_fal.py`에 전자기기 키워드 자동 감지 + 로고 방지 접미 문구 자동 주입(코드 가드)으로 추가 승격 검토.
- **관련**: `productions/<예시_production>/07_upload_meta.md` 사이클 메모, `productions/<예시_production>/07_upload_meta.md` 사이클 메모, `docs/PRODUCTION_PLAYBOOK.md §7.5`

---

## FC-032 — 성과 수집 연속 실행 → Instagram 계정 봇 오인 정지
- **날짜**: 2026-11-15(원인 추정 행동) → 2026-11-21(정지 확인·이의제기 복구)
- **증상**: 채널 계정 프로필 "이용할 수 없음"(로그아웃 상태 동일). IG 메일 = 검토 결과 규정 준수, "저희 실수".
- **원인(추정)**: 11-15 23:17~23:52 `collect_analytics_auto.py`를 6회 연속 실행(릴스 약 180편을 고정 4.5초 간격으로 열고 인사이트 클릭). 보조 후보 = 11-17 수집 1회, 11-18 게시 프로그램 게시 확인 루프(20초마다 릴스 탭 재열람), 자동화 Chrome에 개인 계정 동시 로그인.
- **해결**: 수집 즉시 중단, 이의제기(사용자)로 복구.
- **재발 방지**: ①약관이 자동 수집을 허용하지 않아 **IG 자동 수집 중단**(사용자 결정 2026-11-21) — `collect_analytics_auto.py`는 IG를 지정하면 열지 않고 끝난다(우회 옵션 없음) ②IG 게시 = 수동, 숫자 = 앱 인사이트에서 손으로 ③남의 서비스에 접속하는 수집기의 디버깅은 저장한 페이지로 ④2026-11-22: 이 계정은 웹 접근 불가(앱 전용) 확인 — 웹 수집 재시도 금지.
- **관련**: 커밋 `9d17b74`, `.claude/skills/collect-analytics/SKILL.md` 함정, `docs/2026-11-21-전체재검토-방향-설계.md` §6 Q3, 전자책 3장 사례 22

---

## 🗓️ 문서 이력

| 날짜 | 변경 | 건수 |
|---|---|---|
| 2026-04-22 | 초판 작성 | 13건 |
| 2026-04-23 | FC-006 ACE Step 재발 가능성 반영, FC-014 (ACE Step Turbo tail 반복) 신규 | 14건 |
| 2026-04-23 | FC-014 실측 샘플 + ffmpeg 트림 적용 기록, FC-015 (generate_timing.py format KeyError) 신규 | 15건 |
| 2026-04-30 | chinjeong_gift 사이클 11건 추가 (FC-016 ~ FC-026) | 26건 |
| 2026-05-03 | dirty_inlaws 사이클 FC-027 (만화 그래픽 효과 영구 잔존) 신규 | 27건 |
| 2026-05-14 | puppy_rescue 사이클 FC-028 (ACE Step 인프라 장애 + 로컬 학습 부족) 신규 | **28건** |
| 2026-07-28 | office_kindness_stalker 사이클 FC-031 (FLUX 노트북 로고 2회 재발 + negative 프롬프트 무시) 신규 | **31건** |
| 2026-06-22 | 성장 플레이북 사이클 FC-029(해시태그 5개 정책 미준수·가드 신설)·FC-030(검증 안 된 알고리즘 꿀팁 추종 방지) 신규 | **30건** |
| 2026-11-21 | FC-032 (성과 수집 연속 실행 → IG 봇 오인 정지) 신규 | **32건** |
