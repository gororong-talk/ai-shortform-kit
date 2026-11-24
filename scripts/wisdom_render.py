#!/usr/bin/env python3
"""
wisdom_render.py — 명언 한 건을 "아주 간단한 텍스트인데 흡입력 있고 오래 보게 되는"
                   미니멀 타이포 결과물로 렌더.

산출:
  1) 정적 텍스트 카드 PNG  — card_9x16.png (Shorts/Reels/TikTok), card_4x5.png (IG 피드/캐러셀)
     → "영상이 아닌, 텍스트로만 이루어진 것"
  2) 미니멀 텍스트 영상 MP4 — 검은 화면에서 명언이 떠오르고(페이드인) → 머무름(읽고 음미)
     → 저자가 뒤늦게 드러남(누가 한 말일까, 흡입력) → 아주 느린 줌 + 비네트로 오래 보게 됨
  3) 컴필레이션 MP4 — 여러 명언을 검은 전환으로 이어 1~3분 명상형(가장 "오래 보는" 포맷)

비용 0원 (로컬 Pillow + ffmpeg, 외부 API 없음).

사용:
  python scripts/wisdom_render.py --id bud_001
  python scripts/wisdom_render.py --id sto_002 --no-video         # 카드만
  python scripts/wisdom_render.py --random 3 --tradition 스토아
  python scripts/wisdom_render.py --compile 5 --mood 평온 --out wisdom_out/_calm5.mp4
  python scripts/wisdom_render.py --id fig_001 --bgm path/to/ambient.mp3
"""
import argparse
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import wisdom_db  # noqa: E402

OUT_ROOT = os.path.join(ROOT, "wisdom_out")

# 명언 채널 (게시 대상) — 게시 도구/_pubmeta 가 읽는 채널 좌표. ID는 2026-06-15 라이브 확인.
WISDOM_CHANNEL = {"name": "명언 채널", "handle": "@your_wisdom_channel", "id": "UC_YOUR_CHANNEL_ID"}

SERIF = "/System/Library/Fonts/Supplemental/AppleMyungjo.ttf"
GOTHIC = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
GOTHIC_MED, GOTHIC_LIGHT = 2, 8  # ttc face index

# mood → 팔레트 (top/bottom 그라데이션, 본문, 강조, 비네트 강도)
PALETTE = {
    "평온": {"top": (17, 24, 27), "bot": (10, 14, 16), "text": (236, 242, 239), "accent": (137, 176, 160), "vig": 0.55},
    "각성": {"top": (15, 16, 20), "bot": (8, 8, 11), "text": (243, 239, 232), "accent": (201, 160, 78), "vig": 0.60},
    "단호": {"top": (16, 12, 13), "bot": (8, 7, 8), "text": (245, 244, 245), "accent": (184, 76, 66), "vig": 0.62},
    "위안": {"top": (24, 18, 13), "bot": (13, 10, 7), "text": (244, 237, 226), "accent": (216, 163, 115), "vig": 0.52},
    "경건": {"top": (15, 18, 34), "bot": (8, 10, 20), "text": (238, 240, 247), "accent": (154, 166, 212), "vig": 0.58},
}
W, H = 1080, 1920
MARGIN = 112
TEXT_W = W - 2 * MARGIN


def load_quote(qid):
    con = wisdom_db.connect()
    rows = wisdom_db._rows_to_dicts(con.execute("SELECT * FROM quotes WHERE id=?", (qid,)))
    con.close()
    if not rows:
        sys.exit(f"(없음) id={qid}")
    return rows[0]


def query_quotes(n, tradition=None, mood=None, theme=None, unused_only=False):
    con = wisdom_db.connect()
    wisdom_db._migrate(con)  # is_used/published 컬럼 보장
    q = "SELECT * FROM quotes WHERE 1=1"
    p = []
    if unused_only:
        q += " AND is_used=0"
    if tradition:
        q += " AND tradition=?"; p.append(tradition)
    if mood:
        q += " AND mood=?"; p.append(mood)
    if theme:
        q += " AND theme LIKE ?"; p.append(f"%{theme}%")
    # 게시-바운드 선택자: 출처 미검증(verified=0)은 자동 게시 후보에 절대 넣지 않는다 (오귀속 차단).
    # --id 단건 수동 렌더는 load_quote 경로라 이 필터를 우회 → 검수 후 의도적 사용 가능.
    q += " AND verified=1"
    # 미사용 우선이면 verified 높은 것부터, 아니면 무작위
    q += (" ORDER BY verified DESC, RANDOM() LIMIT ?" if unused_only else " ORDER BY RANDOM() LIMIT ?")
    p.append(n)
    rows = wisdom_db._rows_to_dicts(con.execute(q, p))
    con.close()
    return rows


def mark_used(qid):
    """렌더 성공한 명언을 is_used=1 로 — 다음 --fresh 가 다시 안 뽑게 (중복 방지)."""
    con = wisdom_db.connect()
    con.execute("UPDATE quotes SET is_used=1 WHERE id=?", (qid,))
    con.commit()
    con.close()


def count_ready_orphans():
    """게시 안 한 '바로 올릴 수 있는' 재고 = 렌더 완료(is_used=1)인데 게시기록 없음(published=0).
    --fresh 백로그 가드의 카운터. build_queue.py orphans 와 동일 정의로 맞춘다(진실원 일치)."""
    con = wisdom_db.connect()
    wisdom_db._migrate(con)  # published 컬럼 보장
    n = con.execute(
        "SELECT COUNT(*) FROM quotes WHERE is_used=1 AND (published=0 OR published IS NULL)"
    ).fetchone()[0]
    con.close()
    return n


def _htag(s):
    return "#" + "".join((s or "").split())


def build_pubmeta(rec, outdir):
    """렌더된 명언에 게시용 _pubmeta.json 자동 생성 → 게시 도구가 그대로 읽음(수동작성 불요).
    명언=타이포라 AI라벨 OFF·FB OFF. 캡션=문구+저자+니치 해시태그(플랫폼당 ≤8·broad #fyp류 금지, 2026-06-22 플레이북)."""
    author, trad = rec.get("author", ""), rec.get("tradition", "")
    q = f'"{rec["text"].strip()}" — {author}' if author else f'"{rec["text"].strip()}"'
    base = ["#명언"] + ([_htag(author)] if author else []) + ([_htag(trad)] if trad else []) + ["#명언채널"]
    base = base[:4]
    # 명언 채널 YouTube 표준 태그(2026-06-22 사용자 지정). YT는 SEO라 니치 ≤8 정책 제외.
    yt_tags = "#shorts #좋은글 #동양고전 #명언 #자기계발 #문학 #동기부여 #행복 #인생조언 #인생 #지혜"
    pub = {
        "slug": f"wisdom_{rec['id']}", "video": "video.mp4",
        "channel": WISDOM_CHANNEL["name"], "channel_handle": WISDOM_CHANNEL["handle"],
        "channel_id": WISDOM_CHANNEL["id"],
        "made_for_kids": False, "ai_label": False, "visibility": "public", "facebook_crosspost": False,
        "quote": q,
        "platforms": {
            "tiktok": {"na": "명언 TikTok 중단(2026-06-22 사용자 결정 — 앞으로 미게시)"},
            "instagram": {"na": "명언 Instagram 중단(2026-07-08 사용자 결정 — 앞으로 미게시)"},
            "youtube": {"title": (rec["text"].strip()[:80] + " #shorts"),
                        "description": q + "\n\n명언 채널 — 매일 한 문장.\n" + yt_tags},
        },
        "_status": "ok", "_warnings": [], "_source": "wisdom_render auto",
        "_note": "명언=타이포→AI라벨 OFF·FB OFF. 채널=명언 채널(@your_wisdom_channel). 게시 도구 소스.",
    }
    with open(os.path.join(outdir, "_pubmeta.json"), "w", encoding="utf-8") as f:
        json.dump(pub, f, ensure_ascii=False, indent=2)
    return pub


def sync_used_from_disk():
    """디스크에 이미 렌더된(wisdom_out/<id>/video.mp4) 명언을 전부 is_used=1 로 동기화.
    --random·수동 렌더 등으로 DB 표시가 누락돼도 --fresh 가 그걸 다시 안 뽑게 하는 self-heal.
    매 --fresh 실행 앞에서 자동 호출 → '중복 재생성' 영구 차단. 반환=새로 표시한 수."""
    if not os.path.isdir(OUT_ROOT):
        return 0
    con = wisdom_db.connect()
    wisdom_db._migrate(con)
    valid = {r[0] for r in con.execute("SELECT id FROM quotes")}
    n = 0
    for name in os.listdir(OUT_ROOT):
        if name in valid and os.path.exists(os.path.join(OUT_ROOT, name, "video.mp4")):
            cur = con.execute("UPDATE quotes SET is_used=1 WHERE id=? AND is_used=0", (name,))
            n += cur.rowcount
    con.commit()
    con.close()
    return n


# ── 주제(테마) 인덱스 ───────────────────────────────────────────────────
# 제작 단위 = 주제. 한 주제에 맞는 글을 코퍼스에서 "모두" 끌어와 한 영상으로.
TRAD_ORDER = ["위인", "스토아", "서양철학", "동양고전", "불교", "성경", "문학"]
THEMES_PATH = os.path.join(ROOT, "data", "wisdom", "themes.json")


def load_themes():
    with open(THEMES_PATH, encoding="utf-8") as f:
        return json.load(f)


def find_theme(theme_id):
    for t in load_themes():
        if t["id"] == theme_id:
            return t
    return None


def resolve_theme(theme):
    """주제에 맞는 글을 코퍼스에서 모두 추출 (태그 OR 키워드 매칭) → 흐름순 정렬·중복제거."""
    m = theme.get("match", {})
    tags = set(m.get("themes", []))
    kws = [k for k in m.get("keywords", []) if k]
    con = wisdom_db.connect()
    allq = wisdom_db._rows_to_dicts(con.execute("SELECT * FROM quotes"))
    con.close()
    hit = []
    for q in allq:
        # 출처 미검증(verified=0)은 게시 영상(주제 컴필레이션)에 넣지 않는다 (오귀속 차단).
        if q.get("verified", 0) != 1:
            continue
        qtags = set(q.get("theme") or [])
        blob = " ".join([q.get("text", ""), q.get("source", ""), q.get("orig", "")])
        if (tags & qtags) or any(k in blob for k in kws):
            hit.append(q)
    hit.sort(key=lambda q: (TRAD_ORDER.index(q["tradition"]) if q.get("tradition") in TRAD_ORDER else 99, q["id"]))
    return hit


def _resolve_bgm(theme, args):
    """--bgm 명시가 우선, 없으면 --auto-bgm 시 mood별 data/wisdom/bgm/<mood>.mp3 자동."""
    if args.bgm:
        return args.bgm
    if getattr(args, "auto_bgm", False):
        p = os.path.join(ROOT, "data", "wisdom", "bgm", f"{theme.get('mood', '평온')}.mp3")
        return p if os.path.exists(p) else None
    return None


# ── 그라데이션 + 비네트 배경 ─────────────────────────────────────────────
def make_background(w, h, pal):
    top, bot = pal["top"], pal["bot"]
    # 세로 그라데이션은 행마다만 변하므로 1×H 로 그린 뒤 가로로 확대 (픽셀 이중루프 회피)
    col = Image.new("RGB", (1, h))
    cp = col.load()
    for y in range(h):
        t = y / (h - 1)
        cp[0, y] = (
            int(top[0] + (bot[0] - top[0]) * t),
            int(top[1] + (bot[1] - top[1]) * t),
            int(top[2] + (bot[2] - top[2]) * t),
        )
    bg = col.resize((w, h))
    # 라디얼 비네트: 가운데 밝게, 가장자리 어둡게
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([-w * 0.25, -h * 0.12, w * 1.25, h * 1.12], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(280))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    edge = Image.blend(bg, dark, pal["vig"])
    return Image.composite(bg, edge, mask)


# ── 텍스트 줄바꿈 (한글: 어절 단위 greedy + 줄 수 유지 균형) ──────────────
def _hard_split(token, font, max_w):
    out, cur = [], ""
    for ch in token:
        if font.getlength(cur + ch) <= max_w or not cur:
            cur += ch
        else:
            out.append(cur); cur = ch
    if cur:
        out.append(cur)
    return out


def _greedy(words, font, max_w):
    lines, cur = [], ""
    for w in words:
        if not cur and font.getlength(w) > max_w:
            lines += _hard_split(w, font, max_w)
            continue
        t = (cur + " " + w).strip()
        if font.getlength(t) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def wrap_balanced(text, font, max_w):
    words = text.split(" ")
    lines = _greedy(words, font, max_w)
    n = len(lines)
    if n >= 2:
        best = lines
        target = int(max_w)
        while target > max_w * 0.45:
            target -= 18
            cand = _greedy(words, font, target)
            if len(cand) == n:
                best = cand
            else:
                break
        lines = best
    return lines


def fit_serif(text, max_w, max_h, max_size=96, min_size=46):
    for size in range(max_size, min_size - 1, -2):
        font = ImageFont.truetype(SERIF, size)
        lines = wrap_balanced(text, font, max_w)
        lh = int(size * 1.5)
        block_h = lh * len(lines)
        if block_h <= max_h and all(font.getlength(l) <= max_w for l in lines):
            return font, lines, lh
    font = ImageFont.truetype(SERIF, min_size)
    return font, wrap_balanced(text, font, max_w), int(min_size * 1.5)


def _draw_centered(draw, lines, font, top_y, lh, fill, w=W):
    y = top_y
    for line in lines:
        lw = font.getlength(line)
        draw.text(((w - lw) / 2, y), line, font=font, fill=fill)
        y += lh
    return y


def _draw_tracked_center(draw, text, font, y, fill, tracking, w=W):
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = (w - total) / 2
    for ch, cw in zip(text, widths):
        draw.text((x, y), ch, font=font, fill=fill)
        x += cw + tracking


# ── 카드 한 장 ───────────────────────────────────────────────────────────
def make_card(rec, ratio="9x16", with_author=True):
    """ratio: '9x16'(1080x1920) | '4x5'(1080x1350). with_author=False → 명언만(영상 1단계)."""
    pal = PALETTE.get(rec.get("mood", "평온"), PALETTE["평온"])
    w = W
    h = 1920 if ratio == "9x16" else 1350
    bg = make_background(w, h, pal)
    draw = ImageDraw.Draw(bg)

    # 본문 폰트 자동 맞춤
    max_h = int(h * 0.46)
    font, lines, lh = fit_serif(rec["text"], TEXT_W, max_h)
    quote_h = lh * len(lines)

    author_font = ImageFont.truetype(GOTHIC, 40, index=GOTHIC_MED)
    src_font = ImageFont.truetype(GOTHIC, 27, index=GOTHIC_LIGHT)
    rule_gap, author_gap, src_gap = int(h * 0.045), 56, 40
    author_block = rule_gap + author_gap + src_gap + 40

    # 명언+저자 합성 블록을 살짝 위(0.46H 중심)에 배치 → 명언 위치는 저자 유무와 무관(영상 reveal 안정)
    total = quote_h + author_block
    top_y = int(h * 0.46 - total / 2)
    if top_y < int(h * 0.10):
        top_y = int(h * 0.10)

    quote_fill = pal["text"]
    end_y = _draw_centered(draw, lines, font, top_y, lh, quote_fill, w)

    if with_author:
        ry = end_y + rule_gap
        rule_w = 64
        draw.line([(w / 2 - rule_w / 2, ry), (w / 2 + rule_w / 2, ry)], fill=pal["accent"], width=3)
        ay = ry + author_gap
        author = rec.get("author", "").strip()
        _draw_tracked_center(draw, author, author_font, ay, pal["accent"], 6, w)
        src = rec.get("source", "").strip()
        if src:
            sy = ay + src_gap + 14
            dim = tuple(int(c * 0.62 + 90 * 0.0) for c in pal["text"])
            _draw_tracked_center(draw, src, src_font, sy, (150, 150, 150), 3, w)
    return bg


def save_cards(rec, outdir):
    os.makedirs(outdir, exist_ok=True)
    paths = {}
    for ratio in ("9x16", "4x5"):
        img = make_card(rec, ratio=ratio, with_author=True)
        p = os.path.join(outdir, f"card_{ratio}.png")
        img.save(p)
        paths[ratio] = p
    return paths


# ── 영상 ─────────────────────────────────────────────────────────────────
def _read_time(text):
    n = len(text)
    return max(4.0, min(9.0, 2.4 + n * 0.135))


MAX_VIDEO_SEC = 15.0  # 명언 영상 길이 상한 — 1편=1명언, 짧게(TikTok/Shorts 흡입력). render_video가 여운을 깎아 강제.


def render_video(rec, outdir, fps=30, bgm=None, outro=2.0):
    """검은화면→명언 페이드인→머무름→저자 reveal(xfade)→**여운**(저자 카드 머무름 + 음악이 리버브로 울려 퍼지며 천천히 사라짐).
    outro = 마지막 문구가 끝난 뒤 여운 구간(초). 0이면 여운 없이 바로 마무리."""
    os.makedirs(outdir, exist_ok=True)
    stage_a = os.path.join(outdir, "_stageA.png")
    stage_b = os.path.join(outdir, "card_9x16.png")  # 최종 카드 = stage B
    make_card(rec, "9x16", with_author=False).save(stage_a)
    make_card(rec, "9x16", with_author=True).save(stage_b)
    # 4x5 카드도 같이
    make_card(rec, "4x5", with_author=True).save(os.path.join(outdir, "card_4x5.png"))

    dA = _read_time(rec["text"])
    dB = 3.2
    xf = 0.8
    hold_b = dB + max(0.0, outro)          # 저자 카드 = reveal 읽기 + 여운 머무름
    total = dA + hold_b - xf
    # 길이 상한 가드(재발방지): 1편=1명언·≤15s. dA는 _read_time에서 9.0s로 캡되어 현재 최대 13.4s지만,
    # 향후 outro/dB 상향이 조용히 15s를 넘기지 않도록 — 명언 읽는시간(dA)은 보존하고 여운(outro)만 깎아 강제.
    if total > MAX_VIDEO_SEC:
        outro = max(0.0, outro - (total - MAX_VIDEO_SEC))
        hold_b = dB + outro
        total = dA + hold_b - xf
        print(f"  (길이 상한 {MAX_VIDEO_SEC:.0f}s 가드: 여운 축소 → {total:.1f}s)", file=sys.stderr)
    fa, fb = round(dA * fps), round(hold_b * fps)
    out = os.path.join(outdir, "video.mp4")

    zp = "x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':s=%dx%d:fps=%d" % (W, H, fps)
    fc = (
        f"[0:v]scale={W}:{H},setsar=1,zoompan=z='min(1+on/{fa}*0.045,1.045)':d={fa}:{zp}[a];"
        f"[1:v]scale={W}:{H},setsar=1,zoompan=z='min(1.045+on/{fb}*0.04,1.09)':d={fb}:{zp}[b];"
        f"[a][b]xfade=transition=fade:duration={xf}:offset={dA - xf:.3f}[m];"
        f"[m]fade=t=in:st=0:d=0.9,fade=t=out:st={total - 1.6:.3f}:d=1.6,format=yuv420p[v]"
    )
    has_bgm = bool(bgm and os.path.exists(bgm))
    # 입력은 전부 -filter_complex/-map 앞에 (ffmpeg 인자 순서 규칙)
    cmd = ["ffmpeg", "-y", "-i", stage_a, "-i", stage_b]
    if has_bgm:
        cmd += ["-stream_loop", "-1", "-i", bgm]
    cmd += ["-filter_complex", fc, "-map", "[v]"]
    if has_bgm:
        # 여운: aecho 리버브로 공간감 + 마지막 문구 후 길고 부드러운 페이드로 울려 퍼지며 사라짐
        fade_tail = max(2.0, min(outro + 1.0, total - 0.5))
        cmd += ["-map", "2:a",
                "-af", ("volume=0.5,aecho=0.8:0.88:320|640:0.32|0.22,"
                        f"afade=t=in:st=0:d=1.5,afade=t=out:st={total - fade_tail:.3f}:d={fade_tail:.3f}"),
                "-shortest", "-c:a", "aac", "-b:a", "128k"]
    cmd += ["-r", str(fps), "-t", f"{total:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-crf", "18", "-movflags", "+faststart", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:], file=sys.stderr)
        sys.exit(f"❌ ffmpeg 실패 (id={rec['id']})")
    if os.path.exists(stage_a):
        os.remove(stage_a)
    return out, total


def render_compilation(recs, out_path, fps=30, bgm=None, hold=5.0):
    """여러 명언을 검은 전환으로 이어붙인 명상형 컴필레이션 (가장 오래 보는 포맷)."""
    tmpdir = os.path.join(OUT_ROOT, "_compile_tmp")
    os.makedirs(tmpdir, exist_ok=True)
    clips = []
    for i, rec in enumerate(recs):
        card = os.path.join(tmpdir, f"c{i:02d}.png")
        make_card(rec, "9x16", with_author=True).save(card)
        dur = max(hold, _read_time(rec["text"]) + 1.5)
        clip = os.path.join(tmpdir, f"c{i:02d}.mp4")
        zp = "x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':s=%dx%d:fps=%d" % (W, H, fps)
        fr = round(dur * fps)
        fc = (
            f"[0:v]scale={W}:{H},setsar=1,zoompan=z='min(1+on/{fr}*0.05,1.05)':d={fr}:{zp},"
            f"fade=t=in:st=0:d=1.0,fade=t=out:st={dur - 1.0:.3f}:d=1.0,format=yuv420p[v]"
        )
        cmd = ["ffmpeg", "-y", "-i", card, "-filter_complex", fc, "-map", "[v]",
               "-r", str(fps), "-t", f"{dur:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-crf", "18", clip]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-1200:], file=sys.stderr)
            sys.exit(f"❌ 컴필 클립 실패 (id={rec['id']})")
        clips.append(clip)

    listfile = os.path.join(tmpdir, "list.txt")
    with open(listfile, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile]
    if bgm and os.path.exists(bgm):
        cmd += ["-stream_loop", "-1", "-i", bgm, "-map", "0:v", "-map", "1:a",
                "-af", "volume=0.5", "-shortest", "-c:a", "aac", "-b:a", "128k"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1200:], file=sys.stderr)
        sys.exit("❌ concat 실패")
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)  # 중간 클립 정리
    return out_path


# ── 주제 카드(오프닝/클로징) + 주제 영상 ──────────────────────────────────
def make_theme_card(theme, count=None, closing=False):
    """주제 영상의 오프닝(타이틀)·클로징 카드."""
    pal = PALETTE.get(theme.get("mood", "평온"), PALETTE["평온"])
    bg = make_background(W, H, pal)
    draw = ImageDraw.Draw(bg)
    title = theme["title"]
    sub = theme.get("subtitle", "")

    title_font, tlines, tlh = fit_serif(title, TEXT_W, int(H * 0.28), max_size=132, min_size=64)
    title_h = tlh * len(tlines)
    sub_font = ImageFont.truetype(GOTHIC, 40, index=GOTHIC_MED)
    foot_font = ImageFont.truetype(GOTHIC, 28, index=GOTHIC_LIGHT)

    rule_gap, sub_gap, foot_gap = 40, 58, 66
    block_h = title_h + rule_gap + (sub_gap + 46 if sub else 0) + foot_gap + 36
    top_y = int(H * 0.43 - block_h / 2)
    if top_y < int(H * 0.12):
        top_y = int(H * 0.12)

    # 작은 상단 키커
    kicker = "오 늘 의 주 제" if not closing else "마 음 에 새 기 며"
    kf = ImageFont.truetype(GOTHIC, 27, index=GOTHIC_LIGHT)
    _draw_tracked_center(draw, kicker, kf, top_y - 78, (150, 150, 150), 7)

    end_y = _draw_centered(draw, tlines, title_font, top_y, tlh, pal["text"])
    ry = end_y + rule_gap
    draw.line([(W / 2 - 52, ry), (W / 2 + 52, ry)], fill=pal["accent"], width=3)
    if sub:
        _draw_tracked_center(draw, sub, sub_font, ry + sub_gap, pal["accent"], 5)
    foot_y = ry + sub_gap + (46 if sub else 0) + foot_gap
    if closing:
        _draw_tracked_center(draw, "—", foot_font, foot_y, (150, 150, 150), 0)
    elif count is not None:
        _draw_tracked_center(draw, f"{count}편의 글", foot_font, foot_y, (150, 150, 150), 4)
    return bg


def _build_clip(png, dur, out, fps=30, z_from=1.0, z_to=1.05, fade=1.0):
    """정지 PNG → 페이드인·느린줌·페이드아웃 단일 클립."""
    fr = round(dur * fps)
    span = z_to - z_from
    zp = "x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':s=%dx%d:fps=%d" % (W, H, fps)
    fc = (
        f"[0:v]scale={W}:{H},setsar=1,"
        f"zoompan=z='min({z_from}+on/{fr}*{span:.5f},{z_to})':d={fr}:{zp},"
        f"fade=t=in:st=0:d={fade},fade=t=out:st={dur - fade:.3f}:d={fade},format=yuv420p[v]"
    )
    cmd = ["ffmpeg", "-y", "-i", png, "-filter_complex", fc, "-map", "[v]", "-r", str(fps),
           "-t", f"{dur:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1200:], file=sys.stderr)
        sys.exit(f"❌ 클립 실패 {out}")


def render_theme_video(theme, recs, out_path, fps=30, bgm=None):
    """주제 오프닝 → 매칭된 글 전부 → 클로징 을 검은 전환으로 이어붙임."""
    import shutil
    tmp = os.path.join(OUT_ROOT, "_theme_tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    clips = []

    op = os.path.join(tmp, "00_opener.png")
    make_theme_card(theme, count=len(recs)).save(op)
    oc = os.path.join(tmp, "00_opener.mp4")
    _build_clip(op, 3.8, oc, fps, 1.0, 1.05)
    clips.append(oc)

    for i, rec in enumerate(recs):
        card = os.path.join(tmp, f"q{i:02d}.png")
        make_card(rec, "9x16", with_author=True).save(card)
        dur = max(5.0, _read_time(rec["text"]) + 2.0)
        clip = os.path.join(tmp, f"q{i:02d}.mp4")
        _build_clip(card, dur, clip, fps, 1.0, 1.06)
        clips.append(clip)

    cp = os.path.join(tmp, "zz_close.png")
    make_theme_card(theme, closing=True).save(cp)
    cc = os.path.join(tmp, "zz_close.mp4")
    _build_clip(cp, 3.2, cc, fps, 1.0, 1.04)
    clips.append(cc)

    listf = os.path.join(tmp, "list.txt")
    with open(listf, "w") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listf]
    if bgm and os.path.exists(bgm):
        cmd += ["-stream_loop", "-1", "-i", bgm, "-map", "0:v", "-map", "1:a",
                "-af", "volume=0.5", "-shortest", "-c:a", "aac", "-b:a", "128k"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1200:], file=sys.stderr)
        sys.exit("❌ 주제 영상 concat 실패")
    shutil.rmtree(tmp, ignore_errors=True)
    return out_path


def main():
    ap = argparse.ArgumentParser(description="명언 미니멀 타이포 카드/영상 렌더")
    ap.add_argument("--id", help="단일 명언 id")
    ap.add_argument("--random", type=int, metavar="N", help="무작위 N건 렌더 (중복 가능)")
    ap.add_argument("--fresh", type=int, metavar="N", help="미사용(is_used=0) N건만 렌더 후 사용표시 — 중복 방지")
    ap.add_argument("--max-backlog", type=int, default=3, metavar="N",
                    help="게시대기 재고(렌더O·게시X)가 N건 이상이면 --fresh 생성을 건너뜀 (재고 쌓임 방지). 기본 3, 0=무제한")
    ap.add_argument("--force", action="store_true", help="--max-backlog 백로그 가드를 무시하고 강제로 --fresh 생성")
    ap.add_argument("--sync-used", action="store_true", help="디스크에 렌더된 명언을 is_used로 동기화하고 종료 (재발방지 self-heal)")
    ap.add_argument("--compile", type=int, metavar="N", help="N건 컴필레이션 영상")
    ap.add_argument("--theme-id", help="주제 영상 1편 — 해당 주제에 맞는 글 전부 (data/wisdom/themes.json)")
    ap.add_argument("--all-themes", action="store_true", help="모든 주제 영상 일괄 생성 (주제 인덱스 팩토리)")
    ap.add_argument("--list-themes", action="store_true", help="주제 레지스트리 + 매칭 글 수 미리보기")
    ap.add_argument("--tradition"); ap.add_argument("--mood"); ap.add_argument("--theme")
    ap.add_argument("--no-video", action="store_true", help="카드 PNG만 (영상 생략)")
    ap.add_argument("--bgm", help="배경음 mp3 경로 (선택)")
    ap.add_argument("--auto-bgm", action="store_true", help="주제 mood별 BGM 자동 입힘 (data/wisdom/bgm/<mood>.mp3)")
    ap.add_argument("--out", help="출력 경로 (compile/theme-id)")
    args = ap.parse_args()

    if args.sync_used:
        n = sync_used_from_disk()
        print(f"✅ sync-used: 디스크 렌더분 {n}건 새로 is_used 표시 (재발방지 동기화 완료)")
        return

    if args.list_themes:
        print(f"{'id':16}{'주제':14}글수   저자(미리보기)")
        print("─" * 70)
        empty = 0
        for t in load_themes():
            recs = resolve_theme(t)
            if not recs:
                empty += 1
            who = ", ".join(dict.fromkeys(r["author"] for r in recs))
            print(f"{t['id']:16}{t['title']:12}{len(recs):>3}   {who[:42]}")
        print(f"\n주제 {len(load_themes())}개 (매칭 0 = {empty}개). 데이터가 늘면 자동으로 채워짐.")
        return

    if args.all_themes:
        themes = load_themes()
        made = 0
        for t in themes:
            recs = resolve_theme(t)
            if not recs:
                print(f"  (건너뜀) {t['id']} — 매칭 0")
                continue
            out = os.path.join(OUT_ROOT, "themes", f"{t['id']}.mp4")
            render_theme_video(t, recs, out, bgm=_resolve_bgm(t, args))
            made += 1
            print(f"  ✅ {t['title']} ({len(recs)}편) → {out}  (미리보기 — 게시 대상 아님)")
        print(f"\n총 {made}개 주제 영상 생성 → {os.path.join(OUT_ROOT, 'themes')}/")
        return

    if args.theme_id:
        t = find_theme(args.theme_id)
        if not t:
            sys.exit(f"(없는 주제) {args.theme_id} — --list-themes 로 확인")
        recs = resolve_theme(t)
        if not recs:
            sys.exit(f"'{t['title']}' 에 매칭된 글이 아직 없습니다 (데이터 추가 필요).")
        out = args.out or os.path.join(OUT_ROOT, "themes", f"{t['id']}.mp4")
        print(f"▶ 주제 '{t['title']}' — {len(recs)}편: " + ", ".join(r["author"] for r in recs))
        render_theme_video(t, recs, out, bgm=_resolve_bgm(t, args))
        print(f"✅ {out}")
        # ⚠️ 주제 컴필레이션은 명언 채널 게시 대상이 아니다(채널 표준 = 영상 1편=명언 1개·≤15초).
        #    미리보기/실험용일 뿐 — 게시는 단건 렌더(--id/--fresh)로만. wisdom_publish_guard 가 비표준 게시를 차단.
        return

    if args.compile:
        recs = query_quotes(args.compile, args.tradition, args.mood, args.theme)
        if not recs:
            sys.exit("조건에 맞는 명언이 없습니다.")
        out = args.out or os.path.join(OUT_ROOT, "_compilation.mp4")
        print(f"▶ 컴필레이션 {len(recs)}건 → {out}")
        render_compilation(recs, out, bgm=args.bgm)
        print(f"✅ {out}")
        return

    do_mark = False
    if args.id:
        # ★ --id도 렌더=소비이므로 is_used 마킹 필요(2026-07-25 fig_006, 2026-07-29 sto_004
        #   둘 다 --fresh가 아닌 수동 --id 선택이라 마킹이 빠져 사람이 매번 수동으로 mark해야
        #   했던 재발 버그 수정). --fresh만 마킹하던 예전 가정이 틀렸음 — 실제 워크플로우는
        #   에이전트가 다양성 판단 후 --id로 특정 명언을 고르는 경로가 표준.
        recs = [load_quote(args.id)]
        do_mark = True
    elif args.fresh:
        synced = sync_used_from_disk()  # 실행 전 디스크↔DB 자동 동기화 → 이미 렌더된 건 절대 재선택 안 함
        if synced:
            print(f"  (sync-used: 디스크 렌더분 {synced}건 is_used 보정)")
        # ♻️ 백로그 가드(재발방지 · 2026-06-26 사용자 지침): 게시 안 한 재고(렌더O·게시X)가
        #    --max-backlog 이상 쌓여 있으면 그날 생성을 건너뛴다. 재고를 게시해 소진하면 자동 재개
        #    → 사람이 launchd "정지/재가동"을 기억할 필요가 없다(daily 켜둬도 안 쌓임). --force 로 우회.
        if args.max_backlog and not args.force:
            backlog = count_ready_orphans()
            if backlog >= args.max_backlog:
                print(f"⏸️ 게시대기 재고 {backlog}건(≥{args.max_backlog}) — 오늘 명언 생성 건너뜀. "
                      f"재고를 게시(publish_ledger.py mark)해 {args.max_backlog}건 미만이 되면 자동 재개. "
                      f"강제 생성=--force · 진단=build_queue.py orphans")
                return
        recs = query_quotes(args.fresh, args.tradition, args.mood, args.theme, unused_only=True)
        do_mark = True
        if not recs:
            print("⚠️ 미사용(fresh) 명언이 없습니다 — data/wisdom 시드를 늘리거나 "
                  "`wisdom_db.py mark <id> --unused` 로 리셋하세요. (중복 방지를 위해 생성 안 함)")
            return
    elif args.random:
        recs = query_quotes(args.random, args.tradition, args.mood, args.theme)
    else:
        ap.error("--id / --fresh / --random / --compile 중 하나는 필요합니다.")

    for rec in recs:
        outdir = os.path.join(OUT_ROOT, rec["id"])
        if args.no_video:
            paths = save_cards(rec, outdir)
            print(f"✅ {rec['id']} 카드: {paths['9x16']}")
        else:
            out, dur = render_video(rec, outdir, bgm=_resolve_bgm(rec, args))
            print(f"✅ {rec['id']} 영상({dur:.1f}s): {out}  | 카드: {outdir}/card_9x16.png")
        build_pubmeta(rec, outdir)   # 게시용 _pubmeta.json 자동 → 게시 도구 데이터구동(수동작성 불요)
        if do_mark:
            mark_used(rec["id"])


if __name__ == "__main__":
    main()
