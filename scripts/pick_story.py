#!/usr/bin/env python3
"""사연 선택 — CVDE 점수 + 베스트댓글 감성 스크리닝 (2026-06-17 박제).

배경: CVDE 점수는 막장 키워드 밀도를 과대평가한다. 실제 독자 반응(베스트댓글)이
진짜 신호 — 95점이라도 베댓이 '주작·개노잼·오글'이면 사이다 채널에선 망한다
(예: 환갑잔치 봉투 <글번호>). 그래서 ①미사용 ②미제작(productions에 post_id 흔적 없음)
③민감소재 제외(자살·아동학대) ④베댓 감성(🟢호응/🔴혹평/⚪중립)까지 본 뒤 고른다.

  python scripts/pick_story.py                 # 상위 후보 + 감성태그 + 추천
  python scripts/pick_story.py --min-cvde 85 --limit 15
  python scripts/pick_story.py --category 시댁갈등
"""
import argparse, glob, json, os, re, sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "stories.db")
PROD = os.path.join(ROOT, "productions")

NEG = re.compile(r"노잼|주작|재미없|오글|뻔한|설득력|수준\s*(낮|높)|별로|억지|개노잼|작작|소설")
POS = re.compile(r"사이다|속\s*시원|화나|공감|응원|힘내|이혼|손절|잘했|대박|어이없|미친년|참교육|싸가지")
SENSITIVE = re.compile(
    r"자살|죽이|죽고|목숨|성폭|강간|아동\s*학대|딸을.*때리|애를.*때리|미성년|"
    r"고문|상습\s*폭행|폭행.*(아동|아이|유치원)|(아동|아이|유치원).*폭행")
# 본문 전용(더 넓게 — 자기위해 표현 포함). 제목·베댓엔 안 떠도 본문에만 숨은 케이스 잡는다.
BODY_SENSITIVE = re.compile(
    r"자살|죽고\s*싶|살고\s*싶지\s*않|사라지(고\s*싶|면\s*좋)|없어지(고\s*싶|면\s*좋)|"
    r"목숨|목매|극단적\s*선택|자해|성폭|강간|아동\s*학대|미성년")


def produced_ids():
    ids = set()
    for p in glob.glob(os.path.join(PROD, "*", "00_meta.json")):
        try:
            ids.add(str(json.load(open(p, encoding="utf-8")).get("post_id")))
        except Exception:
            pass
    return ids


def main():
    ap = argparse.ArgumentParser(description="사연 선택 — CVDE + 베스트댓글 감성 스크리닝")
    ap.add_argument("--min-cvde", type=int, default=70)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--category")
    ap.add_argument("--claim", metavar="POST_ID",
                    help="선택한 사연을 is_used=1로 클레임(중복 제작 방지). "
                         "이전엔 production마다 sqlite 한 줄을 손으로 쳐야 했다(2026-06-24 박제).")
    ap.add_argument("--sync-used", action="store_true",
                    help="productions/*/00_meta.json 의 post_id 를 전부 is_used=1 로 동기화하고 종료 "
                         "(재발방지 self-heal — production 때 --claim 빠뜨려도 DB가 진실해진다, "
                         "명언 wisdom_render.py --sync-used 와 동일 관용구, 2026-06-27 박제).")
    a = ap.parse_args()

    if a.claim:
        c = sqlite3.connect(DB)
        cur = c.execute("update stories set is_used=1 where post_id=?", (a.claim,))
        c.commit()
        c.close()
        if cur.rowcount:
            print(f"✅ claim: post_id={a.claim} → is_used=1 ({cur.rowcount}건). 다음 pick에서 제외됨.")
        else:
            print(f"⚠️ post_id={a.claim} 를 stories에서 못 찾음 — 오타 확인.")
        return

    if a.sync_used:
        c = sqlite3.connect(DB)
        synced = 0
        for pid in produced_ids():
            if pid in (None, "None", ""):
                continue
            cur = c.execute("update stories set is_used=1 where post_id=? and is_used=0", (pid,))
            synced += cur.rowcount
        c.commit()
        c.close()
        print(f"✅ sync-used: production 폴더 post_id 기준 {synced}건 새로 is_used=1 보정 (재발방지 동기화 완료).")
        return

    done = produced_ids()
    c = sqlite3.connect(DB)
    q = ("select post_id,cvde_score,category,emotion,title,best_comments,body "
         "from stories where is_used=0 and cvde_score>=? ")
    args = [a.min_cvde]
    if a.category:
        q += "and category=? "
        args.append(a.category)
    q += "order by cvde_score desc limit ?"
    args.append(a.limit * 3)  # 여유있게 뽑고 필터

    rows, shown = [], 0
    for pid, sc, cat, emo, title, bc, body in c.execute(q, args):
        spid = str(pid)
        try:
            cm = json.loads(bc) if bc else []
        except Exception:
            cm = []
        joined = " ".join(cm)
        neg = len(NEG.findall(joined))
        pos = len(POS.findall(joined))
        produced = spid in done
        sensitive = bool(SENSITIVE.search((title or "") + " " + joined))
        # ★본문(body) 민감어는 따로 본다 — 제목·베댓엔 안 떠도 본문에 자기위해·학대가
        #   숨어있는 케이스(엄마8천만 <글번호>: "살고싶지않다·사라지고싶다"가 본문에만)를
        #   감독이 놓치지 않게. 단 하드 제외는 안 함(사이다 각색으로 들어낼 여지 보존)
        #   → ⚠️본문민감 경고만 표시. (2026-06-27 박제, body-scan gap fix)
        body_sensitive = bool(BODY_SENSITIVE.search(body or ""))
        if neg >= 2 and neg > pos:
            tag = "🔴혹평"
        elif pos >= 2 and pos >= neg:
            tag = "🟢호응"
        else:
            tag = "⚪중립"
        verdict = "✅추천" if (not produced and not sensitive and tag != "🔴혹평") else \
                  ("⏭️제작됨" if produced else ("⚠️민감" if sensitive else "🚫혹평"))
        rows.append((sc, tag, verdict, cat, emo, (title or "")[:42], spid, neg, pos, cm[:2], body_sensitive))
        shown += 1
        if shown >= a.limit:
            break

    print(f"미사용 cvde>={a.min_cvde} 상위 {len(rows)}건  (제작됨 {len(done)} 제외대상 표시)\n")
    print(f"{'점수':>3} {'감성':<5} {'판정':<7} 카테고리/감정 | 제목  (id)")
    for sc, tag, verdict, cat, emo, title, pid, neg, pos, sample, bsens in rows:
        bwarn = "  ⚠️본문민감(각색필요)" if bsens else ""
        print(f"  [{sc:>2}] {tag:<4} {verdict:<6} {cat}/{emo} | {title}  ({pid})  neg{neg}/pos{pos}{bwarn}")
        for s in sample:
            print(f"        · {s[:58]}")
    rec = [r for r in rows if r[2] == "✅추천"]
    print(f"\n👉 추천(미제작·비민감·非혹평) {len(rec)}건 — 점수+호응 우선 선택. 최상위:")
    if rec:
        r = rec[0]
        print(f"   [{r[0]}] {r[1]} {r[3]}/{r[4]} | {r[5]}  (id {r[6]})")
    c.close()


if __name__ == "__main__":
    main()
