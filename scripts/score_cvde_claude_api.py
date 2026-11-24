#!/usr/bin/env python3
"""score_cvde_claude_api.py — CVDE 채점을 Claude API 직접 호출로 (Gemini/서브에이전트 불요).

story_scorer.py(Gemini)와 **동일한 CVDE 루브릭**을, anthropic SDK 없이 stdlib urllib 로
api.anthropic.com/v1/messages 에 직접 호출한다. → launchd 등 완전 헤드리스에서 작동.
"막힌 건 호출 경로지 채점 추론이 아니다" — Gemini가 429여도, /score-cvde 의 Workflow(서브에이전트)
없이도, ANTHROPIC_API_KEY 만 있으면 스케줄러가 스스로 채점한다.

대상: stories.db 의 category='미분류' stories (<사연 수집기> 가 미분류로 적재).
출력: cvde_score(total)·score_detail·category·emotion UPDATE (apply_cvde_scores.py 와 동일 포맷).

사용:
  .venv/bin/python scripts/score_cvde_claude_api.py                 # 미분류 전량, Haiku
  .venv/bin/python scripts/score_cvde_claude_api.py --limit 20 --dry-run
  .venv/bin/python scripts/score_cvde_claude_api.py --model claude-sonnet-4-6 --batch 8
"""
import os, sys, json, time, sqlite3, argparse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "stories.db")
ENV = os.path.join(ROOT, ".env")
API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"  # 채점은 구조화 루브릭이라 Haiku로 충분·저렴


def load_env():
    """anthropic SDK·dotenv 의존 없이 .env 파싱 → os.environ (이미 있으면 보존)."""
    if not os.path.exists(ENV):
        return
    for line in open(ENV, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


RUBRIC_HEAD = """당신은 유튜브 숏폼 채널의 콘텐츠 기획 디렉터입니다.
아래 사연들을 CVDE 프레임워크로 채점하세요.

[CVDE 채점 기준 (각 0~25점, 총 100점)]
- C (Conflict, 갈등 선명도): 빌런과 주인공의 대립이 명확/구체적인가?
- V (Virality, 바이럴): 베플 반응이 뜨겁고 "나도 이런 경험" 공감/공유 욕구가 있는가?
- D (Detail, 디테일): 구체적 대사·행동·사물이 있어 영상으로 재현 가능한가? 1~2줄 빈약글이 아닌가?
- E (Emotion, 감정 곡선): 고구마→사이다·반전 등 감정 낙차로 끝까지 보게 하는가?

또한 각 사연을 분류:
- category: 사연계면 구체 유형(시댁갈등/부부갈등/직장갈등/친구갈등/가족갈등/연애갈등/육아갈등/돈문제/복수사이다 등),
  사연이 아니면(연예/정치/스포츠/일상잡담/홍보/뉴스/의미없음) 해당 일반명사로 적고 점수를 낮게.
- emotion_tag: 분노/슬픔/통쾌/불안/따뜻함/허탈/충격 중 대표 1개.

# 출력: 순수 JSON 배열만 (설명·코드펜스 금지). total 은 4항 합과 정확히 일치시킬 것.
[{"post_id":"...","conflict":20,"virality":18,"detail":22,"emotion":24,"total":84,"category":"시댁갈등","emotion_tag":"분노","reason":"한 줄 근거"}]

[채점할 후보 사연들]
"""


def _comments_str(raw):
    if not raw:
        return ""
    try:
        v = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(v, list):
            return " / ".join(str(x)[:80] for x in v[:3])
    except Exception:
        pass
    return str(raw)[:200]


def fetch_unscored(limit):
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    q = ("SELECT post_id,title,substr(body,1,900) AS body,best_comments "
         "FROM stories WHERE category='미분류' OR category IS NULL ORDER BY post_id")
    rows = c.execute(q).fetchall()
    c.close()
    if limit and limit > 0:
        rows = rows[:limit]
    return [dict(r) for r in rows]


def build_prompt(batch):
    parts = [RUBRIC_HEAD]
    for r in batch:
        parts.append(
            f"\n■ post_id: {r['post_id']}\n"
            f"  제목: {r.get('title','') or ''}\n"
            f"  본문: {(r.get('body','') or '')[:500]}\n"
            f"  베플: {_comments_str(r.get('best_comments'))}"
        )
    return "".join(parts)


def call_api(model, prompt, max_tokens, retries=3):
    body = json.dumps({
        "model": model, "max_tokens": max_tokens, "temperature": 0.3,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=body, headers={
        "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    })
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
            return text, data.get("usage", {})
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:200]!r}"
            if e.code in (429, 500, 503, 529):
                time.sleep(2 * (attempt + 1)); continue
            break
        except Exception as e:
            last = str(e); time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"API 실패: {last}")


def parse_scores(text):
    t = text.strip()
    if "```" in t:
        t = t.replace("```json", "").replace("```", "").strip()
    s, e = t.find("["), t.rfind("]")
    if s != -1 and e != -1:
        t = t[s:e + 1]
    return json.loads(t)


def apply_rows(scored):
    c = sqlite3.connect(DB)
    n = 0
    for d in scored:
        try:
            pid = str(d["post_id"])
            total = int(d.get("total", 0))
            detail = json.dumps({"conflict": d.get("conflict", 0), "virality": d.get("virality", 0),
                                 "detail": d.get("detail", 0), "emotion": d.get("emotion", 0),
                                 "reason": d.get("reason", ""), "by": "claude-cvde-api"}, ensure_ascii=False)
            cur = c.execute("UPDATE stories SET cvde_score=?, score_detail=?, category=?, emotion=? WHERE post_id=?",
                            (total, detail, d.get("category", "기타"), d.get("emotion_tag", ""), pid))
            n += cur.rowcount
        except Exception as ex:
            print(f"   ⚠️ 적용 실패 {d.get('post_id')}: {ex}")
    c.commit(); c.close()
    return n


def main():
    ap = argparse.ArgumentParser(description="CVDE 채점 (Claude API 직접 호출, 헤드리스)")
    ap.add_argument("--limit", type=int, default=0, help="채점 상한 (0=미분류 전량)")
    ap.add_argument("--batch", type=int, default=10, help="API 호출당 사연 수")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dry-run", action="store_true", help="DB 미반영, 결과만 출력")
    args = ap.parse_args()

    load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️ ANTHROPIC_API_KEY 없음 — 채점 건너뜀 (수집 잡은 정상 종료).")
        return 0
    if not os.path.exists(DB):
        print(f"⚠️ DB 없음: {DB}"); return 0

    todo = fetch_unscored(args.limit)
    if not todo:
        print("✅ 미분류 사연 없음 — 채점할 대상 0."); return 0
    print(f"▶ CVDE 채점 대상 {len(todo)}건 · model={args.model} · batch={args.batch}"
          f"{' · DRY-RUN' if args.dry_run else ''}")

    applied = in_tok = out_tok = fail = 0
    for i in range(0, len(todo), args.batch):
        batch = todo[i:i + args.batch]
        try:
            text, usage = call_api(args.model, build_prompt(batch), max_tokens=max(1024, 220 * len(batch)))
            in_tok += usage.get("input_tokens", 0); out_tok += usage.get("output_tokens", 0)
            scored = parse_scores(text)
        except Exception as e:
            fail += len(batch); print(f"   ✗ 배치 {i//args.batch+1} 실패: {e}"); continue
        if args.dry_run:
            for d in scored:
                print(f"   [{d.get('post_id')}] {d.get('total')}점 {d.get('category')}/{d.get('emotion_tag')} — {d.get('reason','')[:50]}")
        else:
            applied += apply_rows(scored)
        print(f"   …{min(i+args.batch, len(todo))}/{len(todo)} (in={in_tok} out={out_tok} tok)")

    # 토큰 합계 + 대략 비용(추정 — 정확 단가는 메모리 llm_pricing 참조)
    print(f"\n✅ 완료 · 적용 {applied}건 · 실패 {fail}건 · 토큰 in={in_tok:,} out={out_tok:,}")
    if "haiku" in args.model:
        est = in_tok / 1e6 * 1.0 + out_tok / 1e6 * 5.0  # Haiku 4.5 추정 단가
        print(f"   대략 비용(추정, Haiku ~$1/$5 per M): ${est:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
