export const meta = {
  name: 'cvde-score-stories',
  description: '커뮤니티 미분류 사연을 Claude 서브에이전트로 CVDE 채점(Gemini 불요)',
  phases: [{ title: 'Score', detail: '배치별 CVDE 채점 → batch 파일' }],
}

// args = { total: <미분류 건수>, batch: 40, outdir: 'data/reservoir/scores' }
const A = typeof args === 'string' ? JSON.parse(args || '{}') : (args || {})
const BATCH = A.batch || 40
const TOTAL = A.total || 0
const OUT = A.outdir || 'data/reservoir/scores'
const N = Math.ceil(TOTAL / BATCH)
phase('Score')
log(`CVDE 채점 시작 — 미분류 ${TOTAL}건 / 배치 ${BATCH} / 에이전트 ${N}개 → ${OUT}/batch_*.jsonl`)

const RUBRIC = `
[CVDE 채점 기준 — 각 0~25점, total=합산(0~100)]
- conflict(갈등 선명도): 빌런↔주인공 대립이 명확/구체적인가
- virality(바이럴): "나도 겪음" 공감대·공유욕구·베플 반응 폭발 가능성
- detail(디테일): 구체적 대사·행동·사물 있는가 / 1~2줄 빈약글 아닌가 / AI 영상 재현 가능 장면
- emotion(감정곡선): 고구마→사이다·빌드업→반전 등 감정 낙차, 끝까지 보게 하는 훅

[category] 사연이면: 시댁갈등/부부갈등/가족갈등/직장갈등/연애/이혼/금전갈등/육아갈등/학교폭력/기타사연.
  사연이 아니면(연예가십·아이돌·정치·홍보·잡담 등): 연예/정치/유머/일상/기타 — 이런 건 우리 막장사연 채널에 부적합하니 conflict/emotion 낮게.
[emotion_tag] 분노/답답함/사이다/슬픔/감동/황당/불안/공감/무덤덤 중 하나.
`

const results = await parallel(
  Array.from({ length: N }, (_, i) => () =>
    agent(
`너는 유튜브 막장사연 숏폼 채널의 콘텐츠 기획 디렉터다. 커뮤니티 사연 ${BATCH}건을 CVDE로 채점한다.

1) 너의 배치 사연을 읽어라(프로젝트 루트에서 Bash 실행, stdlib만 — 정적 스냅샷 슬라이스):
python3 -c "import json; ls=open('data/reservoir/scores/_input.jsonl',encoding='utf-8').read().splitlines(); rows=[json.loads(x) for x in ls[${i * BATCH}:${i * BATCH + BATCH}]]; print(json.dumps(rows,ensure_ascii=False))"

2) 각 사연을 아래 루브릭으로 채점한다. 본문·제목·베플(있으면)을 근거로 정직하게. 과대평가 금지.
${RUBRIC}

3) 결과를 파일 ${OUT}/batch_${i}.jsonl 에 써라(Write 도구). 사연 1건당 한 줄 JSON:
{"post_id":"...","conflict":0~25,"virality":0~25,"detail":0~25,"emotion":0~25,"total":0~100,"category":"...","emotion_tag":"...","reason":"한 줄 근거(40자 이내)"}
- total은 네 항목 합과 일치시켜라. 읽은 모든 사연(최대 ${BATCH}건)을 빠짐없이 한 줄씩.
- 본문이 비거나 광고/홍보면 낮은 점수 + category 적절히.

4) 반환: 채점해서 파일에 쓴 줄 수(count).`,
      { label: `score:b${i}`, phase: 'Score', schema: { type: 'object', properties: { count: { type: 'integer' } }, required: ['count'] } }
    )
  )
)
const done = results.filter(Boolean)
const totalScored = done.reduce((s, r) => s + (r.count || 0), 0)
log(`완료: ${done.length}/${N} 배치, 채점 ${totalScored}건`)
return { batches: N, ok: done.length, scored: totalScored }
