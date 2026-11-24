---
name: tighten-narration
description: 완성된 나레이션 영상이 늘어질 때 재-TTS 없이 페이스를 빠르게 조임. 기존 03_audio_narration_only.mp3 를 atempo 로 가속(피치 보존) + 04_timing.json 비례 축소 + compose_narration 재실행. 원본 백업으로 멱등(다른 속도로 재실행 안전). uncle_car·ex_90million 둘 다 "늘어진다"로 검증. 사용자가 "/tighten-narration <slug>", "영상 늘어져", "빠르게 해줘", "페이스 조여", "tighten" 같은 표현 사용 시 호출.
---

# /tighten-narration — 나레이션 페이스 조임 (재-TTS 없음)

## 트리거
- `/tighten-narration <slug> [속도]` 또는 "늘어져, 빠르게 해줘", "페이스 조여"
- 전제: `03_audio_narration_only.mp3` + `04_timing.json` 존재 (compose 까지 한 번 됨)

## 왜
Gemini TTS(Kore)는 또박또박이라 ~24라인이면 120s+ 늘어지기 쉬움(uncle_car 137s, ex_90million 124.6s). **재-TTS는 쿼터 낭비** → 기존 오디오를 가속하고 타이밍만 비례 축소.

## 사용
```bash
python scripts/tighten_narration.py <slug>            # 기본 1.12x (2026-07-25 조정, ~89% 길이)
python scripts/tighten_narration.py <slug> --speed 1.15   # 더 조임(상한 권장선)
python scripts/tighten_narration.py <slug> --no-recompose # 오디오·타이밍만(직접 compose)
python scripts/tighten_narration.py <slug> --kenburns      # ⚠️ 롱폼/스틸(Ken Burns) 빌드면 필수 — 재합성에 전달
```
처리: 오디오 atempo(피치 보존) → `04_timing.json` 전 시간 ÷속도 → `compose_narration` 재실행 → `06_render_v1.mp4` 갱신.

## ⭐ 멱등 (안전)
첫 실행 때 `audio/03_audio_pre_tighten.mp3` + `04_timing_pre_tighten.json` 로 **원본 백업**. 이후 매 실행은 *원본에서* 재계산 → 다른 `--speed` 로 여러 번 돌려도 **누적 가속 안 됨**. (원본 페이스로 되돌리려면 `--speed 1.0`.)

## 속도 가이드
- ⚠️ **자연속도 우선**(2026-06-26 사용자 지침) — 늘어질 때만 조이고, 되도록 atempo보다 대본 압축을 먼저 고려할 것.
- `1.1` — 살짝 (늘어짐 약간)
- `1.12` — 기본값 (~11% 단축, 자연스러움 유지)
- `1.15` — 권장 상한 (~13% 단축)
- `1.18` 이상은 지침상 과속 판정 — 쓰려면 사용자에게 먼저 확인.

## 다음
- 재렌더 검수(프레임 추출) → 페이스 OK → `/upload-meta`.

## 절대 하지 말 것
- **롱폼(Ken Burns 빌드)에 `--kenburns` 없이 tighten** — 재합성이 정지화면으로 됨 (broken_engagement류)
- 조이려고 **재-TTS**(generate-narration 재실행) — 쿼터 낭비. 이 스킬로.
- 원본 백업(`_pre_tighten`) 삭제 (멱등·되돌리기 불가해짐)
- 과속으로 발화 뭉개기

## 참조
- `scripts/tighten_narration.py` — 구현
- 선행: `/compose-narration` · 후행: `/upload-meta`
