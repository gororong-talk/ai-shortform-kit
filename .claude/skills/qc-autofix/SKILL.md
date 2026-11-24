---
name: qc-autofix
description: production 이미지의 자율 QC 루프 — 검출(검은프레임·가짜글자·얼굴/손/정체성)→분류→자동수정(글자=인페인트 구도보존 / 그외=재생성)→재검증을 깨끗할 때까지(최대 3회) 한 명령으로. 사람이 매 컷 못 보는 자율생성의 필수 게이트. 사용자가 "/qc-autofix", "이미지 QC", "이미지 검수", "가짜글자 잡아", "QC 돌려", "이미지 자동수정" 같은 표현 사용 시 호출.
---

# /qc-autofix — 자율 이미지 QC 루프

## 트리거
- `/qc-autofix <slug>` 또는 "이미지 QC 돌려", "가짜글자 잡아", "이미지 검수"
- 전제: `productions/<slug>/flow_images/B##.png` 생성됨(+ 인물 사연이면 `_ref_*.png`)

## 핵심
`scripts/qc_autofix.py` 래퍼. `verify_images`의 판정을 재사용해 결함을 **종류별로 라우팅**:
- 글자/간판만(`gibberish_text`) → `scrub_text --inpaint`(표면교체, **구도 보존**)
- 얼굴/손/정체성 등 → `generate_images_fal` 재생성(기존 백업 후)
- 글자가 1회 스크럽 후에도 남으면 → 재생성 에스컬레이션(무한 스크럽 방지)

깨끗할 때까지 최대 3회 반복. **exit 0 = 전부 통과 / exit 1 = 한도 내 못 고친 결함 남음**(사람 확인 권장).

## 실행
```bash
.venv/bin/python scripts/qc_autofix.py --production <slug>            # 자동(최대 3회)
.venv/bin/python scripts/qc_autofix.py --production <slug> --dry-run  # 판정·라우팅만(수정 X)
.venv/bin/python scripts/qc_autofix.py --production <slug> --only 6,13 # 특정 비트만
```
- `ANTHROPIC_API_KEY` 필요(비전 QC). 비용 = 컷수 × 소액 vision + 재생성 시 fal ₩12/장.

## ★ 재발방지 연결 (반드시)
이미지를 **고쳤으면 재렌더**해야 한다 — 안 하면 stale 영상이 게시됨(cafe_farewell 사고, [[stale-render-and-foreground-text-qc]]):
```bash
# qc_autofix가 이미지를 바꿨으면(exit/변경) → 재렌더 → freshness 가드로 확인
PATH=/opt/homebrew/bin:$PATH .venv/bin/python scripts/compose_narration.py <slug> --kenburns
.venv/bin/python scripts/prep_upload.py <slug> --no-open   # STALE 렌더 경고 없으면 OK
```

## 흐름 (produce-sayeon / produce-kids 내부에서 자동 호출)
1. 이미지 생성 직후 `check_black_frames` → `qc_autofix`(자율).
2. exit 1이면 사용자에게 잔존 결함 보고(수동 확인).
3. 이미지가 바뀌었으면 **재렌더 → prep_upload**(freshness 가드 통과 확인)까지.

## 참조
- `scripts/qc_autofix.py` · `scripts/verify_images.py` · `scripts/scrub_text.py` · `scripts/generate_images_fal.py`
- 후행 재렌더: `scripts/compose_narration.py --kenburns` → `scripts/prep_upload.py`
- 캐릭터 일관성: `docs/CHARACTER_CONSISTENCY.md` [[character-consistency]]
