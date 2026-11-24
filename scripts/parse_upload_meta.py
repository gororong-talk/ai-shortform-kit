#!/usr/bin/env python3
"""parse_upload_meta.py — 07_upload_meta.md(사람 친화 Markdown) → _pubmeta.json(기계 구조화).

업로드 자동화의 선결 과제: 메타가 Markdown에만 있어 어떤 자동화(userscript/Claude DOM구동)든
영상별로 사람이 다시 붙여넣어야 했다. 이 파서가 md → JSON으로 구조화하면 그 의존이 사라진다.
00_meta.json으로 아동용·채널을 교차검증해 신뢰도를 높이고, YT 채널 핸들/ID(URL 직행용)도 채운다.

사용:
  .venv/bin/python scripts/parse_upload_meta.py productions/<예시_production>
  .venv/bin/python scripts/parse_upload_meta.py --all            # 전 production 일괄
  .venv/bin/python scripts/parse_upload_meta.py <slug> --print   # 파일 안 쓰고 stdout만
  .venv/bin/python scripts/parse_upload_meta.py --next-episode   # 사연 채널(사연) 다음 회차번호만 출력

★전환장치(2026-07-09, 사용자 지침 — 구독 전환 개선 시도): _pubmeta.json에
episode_number(사연 채널 자동 회차번호)·pinned_comment(고정댓글 문구) 필드 추가.
"""
import os, re, sys, json, glob, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROD = os.path.join(ROOT, "productions")

# 채널명/핸들 → (handle, channel_id). ID는 2026-06-15 라이브 확인.
CHANNELS = [
    ("키즈 채널", "@your_kids_channel",     "UC_YOUR_CHANNEL_ID"),
    ("명언 채널",   "@your_wisdom_channel",   "UC_YOUR_CHANNEL_ID"),
    ("사연 채널",    "@your_story_channel","UC_YOUR_CHANNEL_ID"),
    ("키즈 채널",    "@your_kids_channel",     "UC_YOUR_CHANNEL_ID"),  # 초기 키즈 서브명
]
PLATFORM_KEYS = [("youtube", ("youtube", "유튜브")), ("tiktok", ("tiktok", "틱톡")),
                 ("instagram", ("instagram", "인스타"))]
TRUE_WORDS = ("on", "켜기", "예", "✅", "true")
HASHTAG_RE = re.compile(r"#\w+", re.UNICODE)
MAX_TAGS = 8  # 정책(2026-06-22 완화): 니치 우선·플랫폼당 최대 8개. 초과/broad 필러 시 _warnings.
# 도달 기여 ~0(2026-06-22 팩트체크) — 니치 태그로 대체 권장.
BROAD_TAGS = {"#fyp", "#fypシ", "#foryou", "#foryoupage", "#추천", "#viral",
              "#viralvideo", "#explore", "#explorepage", "#trending"}


def _platform_hashtags(v):
    """플랫폼 캡션(title+description+caption)의 해시태그 목록 (대소문자 무시 dedup)."""
    seen, uniq = set(), []
    for f in ("title", "description", "caption"):
        for t in HASHTAG_RE.findall(v.get(f) or ""):
            k = t.lower()
            if k not in seen:
                seen.add(k); uniq.append(t)
    return uniq


def hashtag_warnings(out):
    """플랫폼당 해시태그 > MAX_TAGS 또는 broad 필러 포함 시 경고 (정책 백스톱 — FC-029)."""
    w = []
    for k, v in (out.get("platforms") or {}).items():
        tags = _platform_hashtags(v)
        if k != "youtube" and len(tags) > MAX_TAGS:   # YT 태그=SEO → 개수 제외(≤8은 IG/TikTok만)
            w.append(f"{k}: 해시태그 {len(tags)}개 > 정책 {MAX_TAGS}개 ({' '.join(tags)})")
        broad = [t for t in tags if t.lower() in BROAD_TAGS]
        if broad:
            w.append(f"{k}: broad 필러 {' '.join(broad)} — 도달 기여 ~0(팩트체크), 니치 태그로 교체 권장")
    return w


SAYEON_HANDLE = "@your_story_channel"


def _next_sayeon_episode_number():
    """사연 채널(사연) 회차 번호 — 이미 배정된 번호 중 최대값+1.
    아직 하나도 배정 안 된 부트스트랩 상태면 현재까지 게시완료(published 필드 존재)된
    편수+1부터 이어간다. 과거 캡션에 이미 박힌 #13~#15는 개별 production의 수동 표기라
    소급 재번호(1부터 다시 매김)하지 않는다 — 라이브 캡션과 어긋나는 걸 피하기 위함."""
    assigned, published_count = [], 0
    for p in glob.glob(os.path.join(PROD, "*", "_pubmeta.json")):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if d.get("channel_handle") != SAYEON_HANDLE:
            continue
        if isinstance(d.get("episode_number"), int):
            assigned.append(d["episode_number"])
        if "published" in d:
            published_count += 1
    return (max(assigned) + 1) if assigned else (published_count + 1)


def _resolve_channel(text):
    if not text:
        return None, None, None
    for name, handle, cid in CHANNELS:
        if name in text or handle in text:
            return name, handle, cid
    return text.strip(), None, None


def _field_after(line):
    """'**제목**: 값' 에서 콜론 뒤 값 (없으면 '')."""
    m = re.search(r":\s*(.*)$", line)
    return m.group(1).strip() if m else ""


def _collect_block(lines, i):
    """marker 줄 다음부터 본문 블록 수집. 코드펜스면 그 안, 아니면 다음 마커 전까지.
    반환 (text, next_index)."""
    n = len(lines)
    # skip blank
    while i < n and not lines[i].strip():
        i += 1
    if i < n and lines[i].strip().startswith("```"):
        i += 1
        buf = []
        while i < n and not lines[i].strip().startswith("```"):
            buf.append(lines[i]); i += 1
        i += 1  # closing fence
        return "\n".join(buf).strip(), i
    buf = []
    while i < n:
        s = lines[i].strip()
        if s.startswith(("**", "##", "---", "> ", "- [")) or re.match(r"^#{1,6}\s", s):
            break
        buf.append(lines[i]); i += 1
    return "\n".join(buf).strip(), i


def parse_md(md_path):
    raw = open(md_path, encoding="utf-8").read()
    lines = raw.splitlines()
    warnings = []

    # ── 헤더 메타 (상단 불릿 + "## ✅ 공통 설정" 섹션까지) ──
    # 표준 템플릿은 AI라벨/아동용/공개범위가 최상단 불릿이 아니라 "## 공통 설정" 아래
    # 있음 — 첫 "##" 에서 끊으면(구버전 버그) 그 섹션 전체가 통째로 날아가 값이 항상
    # null로 샌다. 첫 "플랫폼" 섹션(## ▶ YouTube/TikTok/Instagram) 직전까지로 확장.
    head_lines = []
    for line in lines:
        hm2 = re.match(r"^##\s+(.*)", line.strip())
        if hm2 and any(nd in hm2.group(1).lower() for _, needles in PLATFORM_KEYS for nd in needles):
            break
        head_lines.append(line)
    head = "\n".join(head_lines)
    def head_has(label):
        # 표준 헤더는 "label: **value**"(값이 볼드) 형식이 대부분이고 채널 줄만
        # "**채널**: value"(라벨이 볼드)라 둘 다 지원 — 콜론 뒤 텍스트를 그대로 반환.
        for line in head.splitlines():
            if label in line and ":" in line:
                return line.split(":", 1)[1].strip()
        m = re.search(rf"\*\*{label}\*\*\s*:?\s*(.*)", head)
        return m.group(1).strip() if m else ""
    ai_raw = head_has("AI 라벨") or head_has("AI 사용")
    kids_raw = head_has("아동용")
    vis_raw = head_has("공개범위") or head_has("공개")
    chan_raw = head_has("채널")
    pin_raw = head_has("댓글고정문구") or head_has("고정댓글")
    info_src_raw = head_has("정보검증출처")
    fb_off = ("OFF" in raw.upper() and ("facebook" in raw.lower() or "페이스북" in raw))

    # ── 플랫폼 섹션 ──
    platforms = {}
    cur = None
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        hm = re.match(r"^##\s+(.*)", s)
        if hm:
            title_txt = hm.group(1).lower()
            cur = None
            if not ("체크리스트" in title_txt or "checklist" in title_txt):
                for key, needles in PLATFORM_KEYS:
                    if any(nd in title_txt for nd in needles):
                        cur = key; platforms.setdefault(key, {}); break
            i += 1; continue
        if cur and "**" in s and ("제목" in s or "설명" in s or "캡션" in s):
            field = "title" if "제목" in s else ("description" if cur == "youtube" else "caption")
            v = _field_after(s)
            if v:                                    # 콜론 뒤 인라인 값 (제목 등)
                platforms[cur][field] = v
                i += 1; continue
            v, i = _collect_block(lines, i + 1)       # 다음 줄부터 블록 (i가 이미 전진됨)
            platforms[cur][field] = v
            continue                                  # ★ i+=1 하면 다음 ## 헤딩을 건너뜀 → continue
        i += 1

    # 영상 파일
    vids = sorted(glob.glob(os.path.join(os.path.dirname(md_path), "06_render*.mp4")))
    video = os.path.basename(vids[0]) if vids else None
    if not video:
        warnings.append("06_render*.mp4 없음")

    name, handle, cid = _resolve_channel(chan_raw)
    out = {
        "slug": os.path.basename(os.path.dirname(md_path)),
        "video": video,
        "channel": name, "channel_handle": handle, "channel_id": cid,
        "made_for_kids": any(w in kids_raw.lower() for w in TRUE_WORDS) if kids_raw else None,
        "ai_label": any(w in ai_raw.lower() for w in TRUE_WORDS) if ai_raw else None,
        "visibility": "public" if ("공개" in vis_raw and "비공개" not in vis_raw) else (vis_raw or None),
        "facebook_crosspost": False if fb_off else None,
        "pinned_comment": pin_raw or None,
        "info_source": info_src_raw or None,
        "platforms": platforms,
        "_source": os.path.basename(md_path),
        "_warnings": warnings,
    }
    return out, head_has, chan_raw


def cross_check(prod_dir, out):
    """00_meta.json 으로 아동용·채널 교차검증·보강."""
    mp = os.path.join(prod_dir, "00_meta.json")
    if not os.path.exists(mp):
        return
    try:
        m = json.load(open(mp, encoding="utf-8"))
    except Exception:
        return
    if out["made_for_kids"] is None and "made_for_kids" in m:
        out["made_for_kids"] = bool(m["made_for_kids"])
    elif "made_for_kids" in m and out["made_for_kids"] is not None and out["made_for_kids"] != bool(m["made_for_kids"]):
        out["_warnings"].append(f"아동용 불일치: md={out['made_for_kids']} vs 00_meta={m['made_for_kids']}")
    if not out.get("channel") and m.get("channel"):
        name, handle, cid = _resolve_channel(m["channel"])
        out["channel"], out["channel_handle"], out["channel_id"] = name, handle, cid
    if "story_type" in m:
        out["story_type"] = m["story_type"]


def process(prod_dir, write=True):
    md = os.path.join(prod_dir, "07_upload_meta.md")
    if not os.path.exists(md):
        return None
    out, _, _ = parse_md(md)
    cross_check(prod_dir, out)
    # 신뢰도: 플랫폼별 제목/캡션이 비었으면 경고
    for k, v in out["platforms"].items():
        if not (v.get("title") or v.get("description") or v.get("caption")):
            out["_warnings"].append(f"{k}: 본문 추출 실패")
    # ★전환장치(2026-07-09): 사연(사연 채널) 회차번호 — 기존 _pubmeta.json에 이미 배정돼
    # 있으면 그대로 유지(재실행 시 번호가 밀리면 안 됨), 없으면 새로 배정.
    if out.get("channel_handle") == SAYEON_HANDLE:
        prior_num = None
        existing_path = os.path.join(prod_dir, "_pubmeta.json")
        if os.path.exists(existing_path):
            try:
                prior_num = json.load(open(existing_path, encoding="utf-8")).get("episode_number")
            except Exception:
                pass
        out["episode_number"] = prior_num if isinstance(prior_num, int) else _next_sayeon_episode_number()
    # ★전환장치: 고정댓글 문구 누락 경고(사연·명언만 — 키즈는 댓글 비활성이라 해당없음)
    if not out.get("pinned_comment") and out.get("channel_handle") in (SAYEON_HANDLE, "@your_wisdom_channel"):
        out["_warnings"].append("pinned_comment 없음 — 07_upload_meta.md에 **댓글고정문구**: 추가 필요")
    # ★정보형 사연 안전게이트(docs/PRACTICAL_INFO_FORMAT.md): 미검증 법률/금전 정보 게시 금지.
    if out.get("story_type") == "practical_info":
        if not out.get("info_source"):
            out["_warnings"].append(
                "정보형 사연(story_type=practical_info)인데 info_source 없음 — "
                "WebSearch로 검증한 기관/근거를 07_upload_meta.md에 **정보검증출처**: 로 기록 필요 "
                "(미검증 정보 게시 금지)")
        disclaimer_words = ("법률 자문", "참고용")
        has_disclaimer = any(w in (out.get("pinned_comment") or "") for w in disclaimer_words) or any(
            w in ((v.get("caption") or "") + (v.get("description") or ""))
            for v in out.get("platforms", {}).values() for w in disclaimer_words)
        if not has_disclaimer:
            out["_warnings"].append(
                "정보형 사연인데 '참고용'/'법률 자문' 고지 문구가 고정댓글·캡션 어디에도 없음 — 안전고지 추가 필요")
    # 재발방지: ai_label/made_for_kids/visibility 헤더 파싱 실패는 null로 조용히
    # 새면 안 됨 — 게시 도구 가 이 null 을 그대로 읽어 AI라벨 토글을 놓칠 수 있음.
    for field in ("ai_label", "made_for_kids", "visibility"):
        if out.get(field) is None:
            out["_warnings"].append(f"{field} 파싱 실패 — 07_upload_meta.md 헤더 형식 확인 필요")
    out["_warnings"].extend(hashtag_warnings(out))   # 해시태그 초과(>8)/broad 필러 백스톱
    if not out.get("channel"):
        out["_warnings"].append("채널 미지정 (07 헤더·00_meta에 채널 없음) — 업로더가 채널 지정 필요")
    # _status: 현행 포맷(## 플랫폼 + **제목/설명/캡션**)이면 ok, 구포맷이면 legacy_unparsed
    clean = bool(out["platforms"]) and all(
        (v.get("title") or v.get("description") or v.get("caption")) for v in out["platforms"].values())
    out["_status"] = "ok" if clean else "legacy_unparsed"
    if write:
        with open(os.path.join(prod_dir, "_pubmeta.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    return out


def main():
    ap = argparse.ArgumentParser(description="07_upload_meta.md → _pubmeta.json")
    ap.add_argument("target", nargs="?", help="production 경로 또는 slug")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--print", dest="show", action="store_true", help="파일 안 쓰고 stdout")
    ap.add_argument("--lint", action="store_true",
                    help="기존 _pubmeta.json(파싱·수동 둘 다) 해시태그 초과(>8)·broad 필러 감사 — 재생성 안 함")
    ap.add_argument("--next-episode", action="store_true",
                    help="사연 채널(사연) 다음 회차번호만 출력하고 종료 (upload-meta 작성 전 캡션에 박아넣을 때 사용)")
    args = ap.parse_args()

    if args.next_episode:
        print(_next_sayeon_episode_number())
        return

    if args.lint:
        pats = [os.path.join(PROD, "*", "_pubmeta.json"),
                os.path.join(ROOT, "wisdom_out", "*", "_pubmeta.json")]
        files = sorted(f for p in pats for f in glob.glob(p))
        bad = 0
        for f in files:
            try:
                out = json.load(open(f, encoding="utf-8"))
            except Exception:
                continue
            ws = hashtag_warnings(out)
            if ws:
                bad += 1
                print(f"🚨 {os.path.relpath(f, ROOT)}")
                for w in ws:
                    print(f"    {w}")
        print(f"\n해시태그 위반(>{MAX_TAGS}개 또는 broad 필러) {bad}건 / 검사 {len(files)}건")
        return

    dirs = []
    if args.all:
        dirs = sorted(d for d in glob.glob(os.path.join(PROD, "*")) if os.path.isdir(d))
    elif args.target:
        p = args.target if os.path.isdir(args.target) else os.path.join(PROD, args.target)
        dirs = [p]
    else:
        ap.error("target 또는 --all 필요")

    ok = miss = legacy = 0
    for d in dirs:
        out = process(d, write=not args.show)
        if out is None:
            miss += 1; continue
        if out["_status"] == "ok":
            ok += 1
        else:
            legacy += 1
        if args.show or not args.all:
            print(json.dumps(out, ensure_ascii=False, indent=2))
        if args.all:
            mark = "✓" if out["_status"] == "ok" else "·"
            tag = "" if out["_status"] == "ok" else "  (구포맷 — 수동)"
            print(f"  {mark} {out['slug']:34s} ch={out['channel_handle'] or '?':16s} kids={out['made_for_kids']} ai={out['ai_label']} plat={list(out['platforms'])}{tag}")
    if args.all:
        print(f"\n현행포맷 ok {ok} · 구포맷 legacy {legacy} · 07없음 {miss}  (모두 _pubmeta.json 생성, _status로 구분)")


if __name__ == "__main__":
    main()
