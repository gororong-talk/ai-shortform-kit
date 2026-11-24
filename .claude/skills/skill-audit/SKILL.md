---
name: skill-audit
description: 스킬을 실제 작업으로 검증·개선하는 dogfooding 프로토콜. 자동 정적 감사(scripts/validate_skills.py — frontmatter·dead-ref·스크립트 syntax)와 실사용 패스(파이프라인을 스킬로 한 단계씩 돌려 작동·갭 확인)를 결합, 발견 즉시 수정·커밋하고 scorecard 보고. uncle_car/ex_90million dogfood에서 stale·커플링·dead-ref 다수 검출·수정. 사용자가 "/skill-audit", "dogfood", "스킬 검증", "스킬 점검", "skill audit", "파이프라인 점검" 같은 표현 사용 시 호출.
---

# /skill-audit — 스킬 dogfooding 프로토콜

## 트리거
- `/skill-audit` 또는 "dogfood 해", "스킬 검증/점검", "skill audit"
- 정례 또는 스킬·파이프라인 대거 변경 후 권장.

## 철학
**실제로 써봐야 문제가 보인다.** 스킬을 "있다"가 아니라 "작동한다"로 검증. 발견은 *즉시 수정*(fix-as-you-go). 갭은 신규 스킬 후보로.

## STEP 1 — 자동 정적 감사 (무실행, 안전)
```bash
python scripts/validate_skills.py
```
검출: ① frontmatter name/description ② **dead-ref**(SKILL.md가 참조하는 레포 파일 부재) ③ 스크립트 **syntax**(ast) ④ orphan 스크립트(정보).
→ **ERROR/WARN 즉시 수정** (dead-ref 경로 교정, 구문오류 fix). 재실행해 0 ERROR 확인.

## STEP 2 — 실사용 패스 (진짜 dogfood)
실제 작업(또는 fixture production)을 **파이프라인 스킬로 한 단계씩** 진행. 각 단계마다:
1. **스킬 매핑**: 이 단계 담당 스킬이 있나? 없으면 **갭 후보** 기록.
2. **실행**: 해당 스킬/스크립트를 *실제로* 돌린다(Skill 툴 또는 스크립트).
3. **관찰**: 산출물 생기나? 기대대로인가? (영상=프레임 추출 검수, 오디오=길이, 텍스트=내용)
4. **기록**: scorecard 에 ✅작동 / 🔧버그 / 🕳️갭 / ⏳차단(HITL·자산대기).

예) 나레이션 파이프라인: start-production → draft-narration → iterate-step3 → generate-hybrid-sheet → [Flow] → normalize-flow-assets → generate-narration → compose-narration → upload-meta → collect-analytics.

## STEP 3 — 발견 → 수정
- **버그/stale**: 해당 SKILL.md·스크립트 즉시 편집. (예 dogfood 검출: start-production 체크리스트 stale, generate_narration 클립판정 커플링, integrate-music dead-ref.)
- **갭**: 반복되는 비스킬 단계 → 신규 스킬 빌드(가능하면 `skill-creator` 또는 프로젝트 규약 SKILL.md+스크립트).
- 학습은 다른 스킬에도 전파(예 "Storybook 캡션" → 프롬프트 규칙).

## STEP 4 — 커밋 + 보고
- 수정·신규 스킬 커밋(스킬별 또는 묶음).
- **scorecard 보고**:
```
| 스킬 | 검증 | 비고 |
✅ 작동 / 🔧 수정 / 🕳️ 갭 / ⏳ 차단
```

## ⚠️ 한계 (정직)
- **창작/HITL 스킬**(draft-narration, generate-hybrid-sheet) = 완전 자동검증 불가. 사람이 결과 판단. STEP 2에서 산출물 *육안 검수*까지만.
- **비용/부작용 스모크**(generate-narration=Gemini 쿼터, compose=ffmpeg 시간, collect-analytics=브라우저) = 무분별 자동실행 금지. 정적감사(STEP1)는 항상, 실행(STEP2)은 실제 작업 맥락에서.
- 브라우저/외부 의존 스킬은 라이브 환경 필요(헤드리스 cron에선 못 함).

## 절대 하지 말 것
- "있으니 작동하겠지" 가정 (반드시 실행 검증)
- 발견만 하고 안 고치기 (fix-as-you-go)
- 쿼터·과금 스킬을 검증 명목으로 남발

## 참조
- `scripts/validate_skills.py` — STEP 1 자동 감사
- (선택) `skill-auditor` 서브에이전트로 STEP 1 fan-out 자율화 가능
- 검증 사례: uncle_car #13 / ex_90million #14 dogfood (신규 6 + 수정 4)
