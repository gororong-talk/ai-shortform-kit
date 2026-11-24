---
name: score-cvde
description: 미분류 사연을 CVDE 프레임워크로 채점하되 Gemini API 대신 Claude 서브에이전트(Workflow)로 직접 — Gemini 크레딧 소진/차단 시 폴백. C/V/D/E(각0~25)+category+emotion 채점 → stories.db UPDATE. 사용자가 "/score-cvde", "CVDE 채점", "사연 점수 매겨", "검수", "Gemini 막혔는데 채점", "일괄 채점" 같은 표현 사용 시 호출.
---

# /score-cvde — CVDE 채점 (Claude 폴백, Gemini 불요)

`skills/story_scorer.py`의 CVDE 루브릭(C 갈등·V 바이럴·D 디테일·E 감정, 각 0~25 → total 100)을 **Claude 서브에이전트로 직접** 적용. Gemini API가 막혀도(크레딧 소진) 채점 가능. 막힌 건 호출이지 채점 추론이 아님.
근거·검증(1,423건) → 메모리 `claude_cvde_fallback.md`.

## 흐름
0. **옛 batch 치우기(필수)** — `apply_cvde_scores.py`는 `data/reservoir/scores/batch_*.jsonl`을 **전부** 재적용한다. 남아 있으면 이전 채점이 다시 덮어써진다:
   ```bash
   d=data/reservoir/scores; ls $d/batch_*.jsonl >/dev/null 2>&1 && mkdir -p "$d/_applied_before_$(date +%Y%m%d)" && mv $d/batch_*.jsonl "$d/_applied_before_$(date +%Y%m%d)/"
   ```
1. **미분류 스냅샷 export**(소비측 venv) — DB 비접촉용 정적 슬라이스:
   ```bash
   .venv/bin/python -c "import sqlite3,json; c=sqlite3.connect('stories.db'); c.row_factory=sqlite3.Row; rows=c.execute(\"SELECT post_id,title,substr(body,1,900) body,best_comments FROM stories WHERE category='미분류' ORDER BY post_id\").fetchall(); open('data/reservoir/scores/_input.jsonl','w').writelines(json.dumps(dict(r),ensure_ascii=False)+chr(10) for r in rows)"
   ```
2. **채점 워크플로**(ultracode Workflow) — N배치(30건/에이전트) 병렬, 각 에이전트가 스냅샷 슬라이스 읽고 CVDE 채점 → `data/reservoir/scores/batch_*.jsonl`:
   ```
   Workflow({scriptPath:"scripts/cvde_score_workflow.mjs", args:{total:<미분류수>, batch:30, outdir:"data/reservoir/scores"}})
   ```
   - args는 객체로 전달(스크립트가 문자열도 파싱). 스냅샷 읽기라 동시 backfill 쓰기와 충돌 없음.
3. **DB 반영**:
   ```bash
   .venv/bin/python scripts/apply_cvde_scores.py   # batch jsonl → cvde_score·score_detail·category·emotion UPDATE
   ```
4. 누락분(파싱실패/소량)은 직접 채점해 `batch_manual.jsonl`에 추가 후 재-apply.

## 산출 포맷 (배치 1줄 = 1사연)
`{post_id,conflict,virality,detail,emotion,total,category,emotion_tag,reason}` — total은 4항 합과 일치. category=사연계(시댁갈등/부부갈등/…) 또는 비사연(연예/정치/일상→저점). 노이즈 저점 필터링 정상.

## 운영
- Gemini 충전되면 기존 `skills/story_scorer.py`(gemini-2.5-flash)가 더 쌈 — 막혔을 때만 이 경로.
- 선행: `(사연 적재)`(미분류 적재) → 이 스킬로 채점 → `/start-production`이 cvde_score로 Top 선택.

## 참조
- `scripts/cvde_score_workflow.mjs` · `scripts/apply_cvde_scores.py` · `skills/story_scorer.py`(루브릭 출처)
