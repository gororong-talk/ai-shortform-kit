---
name: compress-deliver
description: 완성 영상을 앱으로 안전 전달하기 위해 압축 + 신선도(stale) 가드. 25MB+ mp4 는 앱 다운로드가 실패하므로(secret_wedding 30MB 실패 실사례) ffmpeg -crf 30 으로 ~10MB 로 줄이고, 렌더가 소스 이미지/오디오보다 오래됐으면(옛 영상) 먼저 막는다. 사용자가 "/compress-deliver <slug>", "압축해서 보내줘", "앱으로 보내", "전달용 압축", "영상 줄여서 줘", "compress" 같은 표현 사용 시 호출.
---

# /compress-deliver — 앱 전달용 압축 + stale 가드

## 트리거
- `/compress-deliver <slug>` 또는 "압축해서 보내줘", "앱으로 보내", "전달용으로 줄여줘"
- 전제: 완성 렌더 `productions/<slug>/06_render*.mp4`(또는 `--file <경로>`) 존재

## 왜 (재발 방지 박제)
1. **앱 다운로드 임계값**: ~25MB 이상 mp4 는 앱 채널에서 다운로드 실패 → 손으로 보내다 secret_wedding(2026-06-26) 30MB 가 실제로 실패해 수동 재압축·재전송(왕복 손실). 임계값·플래그를 매번 기억에서 재유도하던 걸 스크립트로 고정.
3. 저모션 KenBurns 영상은 crf30 에서 **무손실급**(1080p 유지)이라 화질 손해 거의 0. (근거 [[narration-pace-natural-over-gate]] 류 실측)

## 실행
```bash
.venv/bin/python scripts/compress_for_delivery.py <slug>
# 더 작게 / 상한 조절:
.venv/bin/python scripts/compress_for_delivery.py <slug> --crf 32 --ceiling-mb 20
# stale 경고 무시하고 강행(드묾):
.venv/bin/python scripts/compress_for_delivery.py <slug> --force
```
동작:
1. `<slug>` → 가장 최근 `06_render*.mp4`(명언은 `video.mp4`) 자동 선택.
2. **stale 가드** — `flow_images/B*.png|mp4`·`audio/03_audio*.mp3`·`04_timing.json` 중 렌더보다 나중에 수정된 게 있으면 **중단**(재렌더 먼저). `--force` 로만 통과.
3. 원본 ≤12MB → 무손실 그대로. 그 외 → `ffmpeg -crf 30` 압축, 상한(기본 24MB) 넘으면 crf 올려 재시도.
4. 마지막 줄 `DELIVER: <경로>` 출력.

## 출력 → 전달
- 전달 캡션엔 plat별 캡션 대신 "받아서 폰에서 게시" 한 줄. 캡션·게시 체크리스트는 `_pubmeta`/게시(수동) 가 따로 담당.

## 절대 하지 말 것
- stale 경고를 무턱대고 `--force` — 옛 영상(고치기 전)이 게시됨. 먼저 재렌더.
- 압축본(`*_app.mp4`)을 _pubmeta.video 로 덮어쓰기 — 원본 06_render 가 진실원(게시는 원본 기준), `_app.mp4` 는 전달용 사본일 뿐.

## 참조
- `scripts/compress_for_delivery.py` — 구현(stale 가드 + crf 에스컬레이션)
- 선행: `/produce-sayeon`(렌더까지) · 후행: 사용자 폰 게시
  ⚠️ 앱 전달은 **사용자가 직접 보고 싶어할 때**만이다 — 자동 게시는 게시(별도 게시 프로그램 또는 수동) 가 이미 3플랫폼을 처리한다.
- 메모리: [[deliver-render-via-app-channel]] · [[stale-render-and-foreground-text-qc]]
