# 💸 최소자본 영상생산 스택 (2026-06-13)

> 목표: 구독 끊고 **종량제(장당 수~수십원)·무료**로 사연→영상 양산 지속.
> 환경: MacBook Pro **M1 Pro / 16GB** / 90GB. → 로컬 디퓨전은 빠듯, **로컬 비디오 불가**.
> 6도메인 웹리서치(현재가) + 레포 분석 합성. 단가는 공시가 기반(★=실측 1회 필요).

## 단계별 최종 스택

| 단계 | 현재(누수) | **최소자본 권장** | 단가 | 연동 |
|---|---|---|---|---|
| 나레이션 | edge-tts SunHi | **유지**(무료) + 로컬 Kokoro 폴백 설치 | $0 | ✅ + 폴백 TODO |
| **이미지** | Gemini-image(막힘)·Flow구독 | **fal.ai FLUX schnell** | **~₩12/장**(8~12) | ✅ `generate_images_fal.py` |
| 이미지(핵심컷) | — | fal FLUX dev / Kontext | ~₩33 / ~₩53 | `--model dev` |
| 모션(기본 90%) | Ken Burns(ffmpeg) | **유지**(무료) + xfade/gblur 보강 | $0 | ✅ `--kenburns` |
| 모션(핵심 비트만) | Kling(Flow) | fal LTX-2 Fast / Wan 2.5 | ~₩330/6s · ₩340/5s | i2v→B##.mp4 TODO |
| BGM | ACE Step 클라우드(FREE) | **유지** + fal ACE-Step 폴백 | $0 / ~₩16/분 | ✅ + 폴백 TODO |
| STT·합성·자막 | faster-whisper·ffmpeg | **유지**(무료) | $0 | ✅ |

## 현실 경제성 (편당 이미지+모션비)

- **숏폼**(8~12컷, 모션 0~2): 이미지 ~₩100 + 모션 ~₩0~660 = **편당 ₩100~760**
- **롱폼**(80~120컷, 모션 3~5): 이미지 ~₩700~1000 + 모션 ~₩1000~1700 = **편당 ₩1.7k~2.7k**
- TTS·BGM·합성 = 사실상 ₩0. → **Flow 월구독(수만원) 대비 양산해도 압도적으로 쌈.**

## 핵심 통찰

1. **무료 단계는 이미 잡혀 있다** — TTS(SunHi)·모션(Ken Burns)·합성(ffmpeg)·STT(whisper).
2. **유일한 진짜 비용·불안정 = 이미지 생성**. 그리고 **제일 싼 해법(fal.ai)은 키가 이미 결제돼 있는데 코드 0줄 연동이었음** → 이번에 해소.
3. **로컬 생성은 16GB에서 양산 비현실** — schnell 장당 ₩12·3.9초 vs 로컬 장당 30초~수분+메모리 점유. "시간=비용"이라 종량제 압승. (로컬은 오프라인 프리뷰 보조로만)
4. **전량 유료 비디오는 비현실** — 하이브리드(무료 Ken Burns 기본 + 핵심 비트만 i2v)가 정답.

## 연동 코드 경로 (fal_client, 동일 패턴)

```python
import fal_client  # .venv 0.13.1, FAL_KEY 자동인식
# 이미지 (구현됨): generate_images_fal.py
r = fal_client.subscribe("fal-ai/flux/schnell", arguments={"prompt":..., "image_size":"portrait_16_9"})
# 비디오 i2v (TODO): 스틸 업로드 → 모션
url = fal_client.upload_file("flow_images/B07.png")
r = fal_client.subscribe("fal-ai/ltxv-2/image-to-video/fast",
        arguments={"image_url":url, "prompt":"subtle head turn, eyes well up", "duration":6, "resolution":"1080p"})
# → r['video']['url'] 다운로드 → flow_images/B07.mp4 (compose_narration 이 mp4 혼합비트로 그대로 합성)
# BGM 폴백 (TODO): fal_client.subscribe("fal-ai/ace-step", {"tags":캡션,"lyrics":가사,"duration":60})
```
- 비디오 모델 가성비순: **LTX-2 Fast**($0.04/s) → **Wan 2.5**($0.05/s) → 임팩트컷만 **Kling 2.5**($0.07/s).
- compose_narration 이 `flow_images/B##.mp4`(모션) + `B##.png`(스틸) **혼합비트를 이미 지원** → 스키마 변경 없이 일부 비트만 모션화 가능.

## 프로세스 개선 로드맵 (process 도메인, 우선순위)

| # | 개선 | 상태 |
|---|---|---|
| 1 | 이미지 막힌 Gemini → **fal schnell 연동** | ✅ **완료**(스모크 검증 ₩12·3.9s·웹툰OK) |
| 2 | `content_generation.py` Step0/1/4 Gemini 직접호출 **폴백 추가**(기존 `_call_with_fallback` 5곳 적용) | TODO — 막힘 면역 |
| 3 | **캐싱**: character_pool(122명)·flow_images 재사용으로 재생성비 0 (`asset_matcher` 해시 dedup) | TODO |
| 4 | 모션 i2v 어댑터(fal LTX/Wan/Kling) — 핵심 비트만 | TODO(ROI 검증 후) |
| 5 | STT `generate_timing.py`(Gemini 교정) → `stt_with_fixes.py`(Claude, FC-028) **일원화** | TODO — 중복 제거 |

## 솔직한 한계 / 검증 필요(★)

- fal 비디오·BGM·dev 단가는 **공시가/2차 출처 추정** — 본격 사용 전 **호출 1건 실측** 필수("될 것 같다" 금지).
- **Seedance(SEEDANCE_AK/SK)**: 2026초 일반 API 미개방 보고 다수 — 보유 키로 i2v 실제 되는지 **미검증**. fal 미러로 먼저 검증.
- edge-tts SunHi: MS 비공식 엔드포인트 → 토큰정책 변경 시 403 통째 막힘 전례(7.2.8은 패치본). **Kokoro 로컬 폴백 미리 설치 권장**(ban 불가·오프라인).
- fal 캐릭터 일관성: schnell 단독은 랜덤 → 같은 인물 여러 씬은 FLUX.2 dev 멀티레퍼런스 or character_pool 병행.
- **스타일 일치(검증 2026-06-13)**: FLUX 기본은 반실사 → 기존 Meta 클린웹툰과 따로 놂. `generate_images_fal --style webtoon`(기본)이 "flat 2D, NOT 3d/realistic" 강제로 **Meta 결 복귀**(B01/B03/B14 비교). schnell-webtoon이 Meta 최근접. **production당 백엔드 통일**(fal+Meta 혼합 시 미세차).
- Gemini 충전 복구 시: TTS는 Kore(감정+한국어), 텍스트단계는 그대로 복귀 가치(현재는 막힘).
