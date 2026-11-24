---
name: generate-narration
description: 나레이션 production 의 감정 나레이션 TTS + 타이밍 자동 생성 (신규 표준). 02_step3_narration.txt 의 라인을 라인별 감정태그로 Fish Audio S2-Pro(신규 1순위, 음질·감정 SunHi 우위)로 생성 → 03_audio_narration_only.mp3 + 04_timing.json. 위계 Fish>SunHi>Gemini Kore(막힘)>ElevenLabs. uncle_car(#13) 검증. 사용자가 "/generate-narration <slug>", "나레이션 생성", "TTS 만들어", "감정 나레이션" 같은 표현 사용 시 호출.
---

# /generate-narration — 감정 나레이션 TTS + 타이밍 자동 생성

## 트리거
- `/generate-narration <slug>` 또는 "나레이션 생성", "TTS 만들어줘", "감정 나레이션"
- 전제: `02_step3_narration.txt` (S01.. 라인) 존재 + 가사 게이트 OK

## 왜 이 스킬 (배경)
- **TTS 표준 = Fish Audio S2-Pro** (`scripts/generate_narration_fish.py`). 위계 Fish > SunHi(edge-tts) > Gemini Kore(막힘) > ElevenLabs. (아래 Gemini 서술은 2026-06 이전 기록)
- ElevenLabs 무료는 영어 프리메이드 voice뿐 → **한국어 발음 NG** (Yooni 네이티브는 유료). Google **Cloud** TTS 는 키 차단. **Gemini API 는 됨.**
- Gemini TTS 는 **자연어로 감정 지시** 가능("분하게 또박또박") → 구간별 감정선 표현.

## ⚠️ TTS 백엔드 현황 (2026-06-20 갱신 — 중요, 읽고 시작)
**위계: Fish S2-Pro > SunHi > Gemini Kore(막힘) > ElevenLabs.**
- **★ 신규 1순위 = Fish Audio S2-Pro** (`scripts/generate_narration_fish.py`, 2026-06-20 빌드·실API 검증). 음질·감정 SunHi 우위. raw REST(`/v1/tts`·model:s2-pro·JSON). **라인별 감정태그**(`[slightly sad]/[angry]/[determined]`) 그대로 반영. 보이스 자동배정(`data/fish_voices.json` assignments: 사연숏폼 f_soft_shorts·롱폼 f_storytelling·명언 f_anchor_calm·키즈/토리 char_cat_cute). **requests+dotenv 만 있으면 됨**(edge venv 불요), 키 = `.env` FISH_API_KEY. 비용 ~$0.02/분.
- **2순위 작동 폴백 = edge-tts SunHi** (무료 네이티브). `scripts/generate_narration_edge.py`, 격리 venv `/tmp/edgetts_venv`. 감정 자연어지시 불가 → 구간별 **rate 변주**. broken_engagement(#15) 검증.
- **Gemini Kore** = 크레딧 소진 막힘(429). OpenAI = 한국어 발음 NG(거부). ElevenLabs Yooni = 유료 전용.

## 핵심 규칙
1. **감정맵을 먼저 만든다** — 라인별 감정은 Claude(사람 이해 필요)가 사연 흐름 보고 부여. 스크립트는 기계적 TTS·연결만.
2. **숫자 한글교정** — 스크립트가 `오백 원/삼백만 원/오년` 등 자동 치환 (발음 안정). 새 패턴은 스크립트 `NUM_FIX` 에 추가.
3. **하이브리드면 비트맵** — `productions/<slug>/_beat_map.json` 있으면 35비트로 분할(8 split-line), 없으면 1라인=1비트.

## 실행 단계

### STEP 1 — 감정 부여 (Claude)
- **★ Fish(1순위) = 라인별 인라인 태그가 정석.** `02_step3_narration.txt` 의 각 `S## ` 본문 앞에 `[slightly sad]`/`[angry]`/`[determined]`/`[excited]`/`[calm]` + 강도 `[slightly]/[very]` + 포즈 `[break]/[long-break]` 를 붙인다(draft-narration 이 작성). Fish 모듈이 그대로 반영하고 **자막엔 태그를 자동 제거**. 태그가 없으면 위치기반 보수적 fallback(오픈·폭로·CTA).
- (Gemini 경로) 아래 `_narration_emotion.json` 자연어 감정맵은 Gemini Kore 복구 시만. SunHi 는 구간별 rate 자동.

`02_step3_narration.txt` 라인을 읽고 **정서 흐름**(회상→빌드업→폭로→사이다/단호 등)에 맞춰 라인별 한국어 감정 디렉티브를 `productions/<slug>/_narration_emotion.json` 에 작성(Gemini용):
```json
{
  "1": "어이없고 분한 마음을 꾹 누르며 또박또박",
  "2": "어이없고 분한 마음을 꾹 누르며 또박또박",
  "15": "불길한 정적을 깔듯 낮고 느리게",
  "18": "분노가 터지듯 날카롭고 빠르게",
  "27": "시청자에게 직접 묻듯 진중하고 또렷하게",
  "gap_2": 0.35, "gap_15": 0.35, "gap_20": 0.35
}
```
- 키 = 라인번호(문자열). `gap_<n>` = 그 라인 뒤 정적(드라마틱 포즈, 기본 0.22s). 폭로 직전/직후를 길게.
- 톤 매핑은 `00_meta.narration_tone` 참고 (분노·각성 / 감동·위로 / 코믹·체념 등).
- (감정맵 생략 시 스크립트가 톤 기반 기본 디렉티브 1개를 전 라인 적용 — 가능하면 라인별로.)

### STEP 2 — TTS 생성 (스크립트)
```bash
# ★ 1순위 = Fish Audio S2-Pro (음질·감정 우위). requests+dotenv 만 있으면 됨(edge venv 불요):
.venv/bin/python scripts/generate_narration_fish.py <slug>
#   보이스 자동(00_meta 의 track/channel/format 기반). 강제: --voice <key|reference_id>
#   감정: 02_step3 라인 앞 [감정태그] 그대로 반영. 태그 없는 라인은 --emotion-profile(auto) 보수적 fallback.
#   청취/비교: scripts/fish_voice.py say <key> "텍스트"  ·  키 = .env FISH_API_KEY

# 2순위 폴백 = SunHi (무료, Fish 키 막힘/장애 시). venv 필수:
# /tmp/edgetts_venv/bin/python scripts/generate_narration_edge.py <slug>
#   venv 없으면: python3 -m venv /tmp/edgetts_venv && /tmp/edgetts_venv/bin/pip install -q edge-tts

# (Gemini 충전 복구 시): python scripts/generate_narration.py <slug>   # voice Kore
```
→ `03_audio_narration_only.mp3` (stereo 44.1k + dynaudnorm + 끝 1.2s 패딩) + `04_timing.json` (라인 timing + 비트 매핑)
→ **세 백엔드 모두 동일 출력 계약** — `compose_narration.py` 가 그대로 읽음(무수정 호환). 백엔드만 다름.

### STEP 3 — 보고 + 다음
- 길이 확인. **~90s 권장**(eonni 83s 89.9% 참고). 137s급으로 길면 사용자에게 "atempo 1.2로 조임?" 안내.
- 사용자 청취 → OK → **다음: `/compose-narration <slug>`** (혼합 compose).

## 함정 / 주의
- **★ Fish 자막 태그 번인 트랩** — 02_step3 라인에 `[감정]` 태그가 있으면 그게 자막에 박일 수 있다. Fish 모듈은 **TTS 텍스트(태그+숫자정규화)와 자막 텍스트(태그 제거·원문 숫자)를 분리**해 해결됨(`split_tags`). 모듈 수정 시 이 분리 깨지 말 것.
- **★ Fish 402** = API 크레딧 미충전(구독≠API크레딧). `fish.audio/app/billing` 충전. **401/403** = 키 오류 → `.env` FISH_API_KEY 확인.
- **★ Fish 보이스 audition** — char_cat_cute/f_anchor_calm/kid_bright 는 `audition:false`(미청취). 새 채널 첫 production 전 `scripts/fish_voice.py say <key>` 로 한 번 듣고 확정 권장.
- **Gemini TTS 429**(분당 쿼터) — 라인별 8s 대기 후 재시도. (Gemini 경로 한정)
- 라인별 생성이라 **각 라인 길이를 정확히 알아 STT(faster-whisper) 불필요** — 04_timing.json 의 라인 timing 이 곧 진실. (Fish/SunHi/Gemini 공통)

## 절대 하지 말 것
- ElevenLabs 영어 voice 로 한국어 나레이션 생성 (발음 NG — 사용자 명시 거부)
- 감정맵 없이 무조건 밋밋하게 (가능하면 STEP 1 감정맵부터)
- 02_step3 라인 본문 수정 (이 스킬은 TTS 생성 전용)

## 참조
- `scripts/generate_narration_fish.py` — ★ 1순위 구현(Fish) · `scripts/generate_narration_edge.py` — SunHi 폴백 · `scripts/generate_narration.py` — Gemini
- `scripts/fish_voice.py` / `data/fish_voices.json` — 보이스 청취·레지스트리·배정 · `scripts/verify_fish_tts.py` — REST 검증
- 메모리 `narration_tts_standard.md` — voice·settings (Fish 표준)
- `productions/<예시_production>/` — 검증 사례 (감정맵·타이밍)
- 다음 단계: `/compose-narration`
