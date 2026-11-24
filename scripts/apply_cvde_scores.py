#!/usr/bin/env python3
"""apply_cvde_scores.py — CVDE 채점 batch jsonl → stories.db UPDATE.

워크플로 산출 data/reservoir/scores/batch_*.jsonl (post_id,conflict,virality,detail,emotion,total,category,emotion_tag,reason)
→ stories.cvde_score(total) · score_detail(breakdown+reason) · category · emotion(=emotion_tag) UPDATE.
"""
import os, sys, json, glob, sqlite3
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "stories.db")
SCOREDIR = os.path.join(ROOT, "data", "reservoir", "scores")

def main():
    files = [f for f in glob.glob(os.path.join(SCOREDIR, "batch_*.jsonl"))]
    if not files:
        print("배치 파일 없음"); return
    c = sqlite3.connect(DB)
    applied = bad = 0; seen = set()
    for f in sorted(files):
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line: continue
            try:
                d = json.loads(line)
                pid = str(d["post_id"])
                if pid in seen: continue
                seen.add(pid)
                total = int(d.get("total", 0))
                detail = json.dumps({"conflict": d.get("conflict",0), "virality": d.get("virality",0),
                                     "detail": d.get("detail",0), "emotion": d.get("emotion",0),
                                     "reason": d.get("reason",""), "by": "claude-cvde"}, ensure_ascii=False)
                cur = c.execute("UPDATE stories SET cvde_score=?, score_detail=?, category=?, emotion=? WHERE post_id=?",
                                (total, detail, d.get("category","기타"), d.get("emotion_tag",""), pid))
                applied += cur.rowcount
            except Exception as e:
                bad += 1
    c.commit()
    # 요약
    tot = c.execute("SELECT COUNT(*) FROM stories").fetchone()[0]
    mi = c.execute("SELECT COUNT(*) FROM stories WHERE category='미분류'").fetchone()[0]
    print(f"✅ 적용 {applied}건 (배치 {len(files)}개, 파싱실패 {bad}) · 고유 {len(seen)}")
    print(f"   DB {tot}건, 남은 미분류 {mi}")
    print("\n=== 채점 후 카테고리 분포 TOP15 ===")
    for r in c.execute("SELECT category,COUNT(*) n,AVG(cvde_score) av FROM stories WHERE cvde_score>0 GROUP BY category ORDER BY n DESC LIMIT 15"):
        print(f"   {r[0]:12s} {r[1]:4d}건  평균 {r[2]:.0f}점")
    print("\n=== CVDE 최고 사연 TOP12 (막장 후보) ===")
    for r in c.execute("SELECT post_id,cvde_score,category,emotion,substr(title,1,34) t FROM stories WHERE cvde_score>0 ORDER BY cvde_score DESC LIMIT 12"):
        print(f"   {r[1]:3d}점 [{r[2][:8]:8s}/{r[3][:5]:5s}] {r[4]}")
    c.close()

if __name__ == "__main__":
    main()
