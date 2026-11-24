#!/usr/bin/env python3
"""validate_skills.py — .claude/skills/* 정적 감사 (dogfood 자동화 일부)

검사 (안전·무실행):
  1. frontmatter — name/description 존재, name == 디렉토리명
  2. dead-ref — SKILL.md 가 참조하는 레포 파일(scripts/ docs/ productions/ analytics/
     references/ .claude/)이 실제로 존재하는가 (placeholder <...>/glob * 은 스킵)
  3. script syntax — 스킬이 구동하는 scripts/*.py 가 파싱(ast)되는가
  4. orphan — scripts/*.py 중 어떤 SKILL.md 도 참조 안 하는 것 (정보)

ERROR 있으면 exit 1. (스모크 실행·창작/HITL 검증은 /skill-audit 수동 패스에서.)
사용:  python scripts/validate_skills.py
"""
import os, re, ast, glob, sys
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(ROOT, ".claude", "skills")
REPO_PREFIXES = ("scripts/", "docs/", "productions/", "analytics/", "references/", ".claude/")
PATH_RE = re.compile(r'(?:scripts|docs|productions|analytics|references|\.claude)/[A-Za-z0-9_./<>*\-]+\.[A-Za-z0-9]+')

def front(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m: return {}
    fm = {}; key = None
    for line in m.group(1).splitlines():
        mm = re.match(r"^(\w+):\s*(.*)$", line)
        if mm:
            key = mm.group(1); fm[key] = mm.group(2).strip()
        elif key and line.strip():          # YAML 멀티라인 값 이어붙이기
            fm[key] += " " + line.strip()
    return fm

def main():
    skills = sorted(glob.glob(os.path.join(SKILLS_DIR, "*", "SKILL.md")))
    if not skills:
        print("스킬 없음:", SKILLS_DIR); return
    errors=[]; warns=[]; infos=[]
    referenced_scripts=set()
    print(f"🔍 {len(skills)}개 스킬 정적 감사\n")
    for sk in skills:
        d = os.path.basename(os.path.dirname(sk))
        text = open(sk, encoding="utf-8").read()
        fm = front(text)
        # 1. frontmatter — 진짜 YAML로도 파싱돼야 한다. 우리 front()는 관대해서 깨진 YAML도 통과시켰다
        #    (2026-11-15 publish-queue: description이 따옴표로 시작해 Claude Code가 설명을 통째로 무시).
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
        if m:
            try:
                y = yaml.safe_load(m.group(1))
                if not isinstance(y, dict) or not isinstance(y.get("description"), str):
                    errors.append(f"[{d}] frontmatter YAML 파싱 결과에 description 문자열 없음")
            except yaml.YAMLError as e:
                errors.append(f"[{d}] frontmatter YAML 파싱 실패: {str(e).splitlines()[0]}")
        if not fm.get("name"): errors.append(f"[{d}] frontmatter name 없음")
        elif fm["name"] != d: warns.append(f"[{d}] name '{fm['name']}' != 디렉토리명")
        if not fm.get("description"): errors.append(f"[{d}] frontmatter description 없음")
        elif len(fm["description"]) < 30: warns.append(f"[{d}] description 너무 짧음(트리거 약함)")
        # 2. dead-ref + 3. script syntax
        refs = set(PATH_RE.findall(text))
        for r in refs:
            if "<" in r or ">" in r or "*" in r: continue  # placeholder/glob
            p = os.path.join(ROOT, r)
            if not os.path.exists(p):
                warns.append(f"[{d}] dead-ref: {r}")
            elif r.startswith("scripts/") and r.endswith(".py"):
                referenced_scripts.add(os.path.normpath(p))
                try: ast.parse(open(p, encoding="utf-8").read())
                except SyntaxError as e: errors.append(f"[{d}] {r} 구문오류: {e}")
        ok = "✅" if fm.get("name") and fm.get("description") else "❌"
        print(f"  {ok} {d}  (refs {len(refs)})")
    # 4. orphan scripts
    all_scripts = {os.path.normpath(p) for p in glob.glob(os.path.join(ROOT,"scripts","*.py"))}
    orphans = sorted(os.path.basename(p) for p in all_scripts - referenced_scripts)
    # 결과
    print("\n── 결과 ──")
    for e in errors: print("❌ ERROR", e)
    for w in warns: print("⚠️  WARN ", w)
    if orphans: print("ℹ️  INFO  스킬 미참조 스크립트:", ", ".join(orphans))
    print(f"\n요약: 스킬 {len(skills)} · ERROR {len(errors)} · WARN {len(warns)}")
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
