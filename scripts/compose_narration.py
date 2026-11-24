#!/usr/bin/env python3
"""compose_narration.py — 나레이션/하이브리드 최종 합성

uncle_car(#13)에서 검증. compose_flow_clips.py(옛 19클립/130s 하드코딩)가 못 다루는
가변 비트 + 혼합미디어(mp4+png) + 나레이션 케이스를 처리.
- 입력: productions/<slug>/04_timing.json  (beats[file,start,end] + subtitles[text,start,end])
        productions/<slug>/flow_images/B##.{png,mp4}  (1080×1920, normalize_flow_assets 산출)
        productions/<slug>/03_audio_narration_only.mp3
- 처리: 비트별 세그먼트 빌드(png=정지 loop / mp4=trim 또는 last-frame hold) → concat
        → ASS 자막 burn(한국어 폰트, 세이프영역, 밴드 위) → 나레이션 mux
        ★첫 자막 줄(훅)은 인스타툰식 제목카드처럼 --hook-scale배 크게(기본 1.5×, 2026-07-07 표준)
        ★00_meta.json의 thumbnail_title이 있으면 오프닝 --title-card-sec초(기본 1.8s) 동안 화면
          상단에 압축된 '막장 제목'을 큰 박스체로 겹쳐 노출(썸네일 문구 표준, 2026-07-09). 필드
          없으면 조용히 생략(하위호환) — thumbnail_title은 나레이션 원문과 별개로 짧게 새로 지을 것.
        ★00_meta.json의 next_preview_lines(기본 0=off)가 N이면 마지막 N개 자막(=다음편 떡밥)을
          이미지 위에 겹치지 않고 화면을 완전 블랙으로 덮은 뒤 그 위에 중앙 정렬로 크게 띄운다
          (다음 이야기 예고 카드, 2026-07-09 사용자 지침 — "이미지 위 겹침이 혼잡"). 사연 표준=1.
          off면 기존처럼 마지막 이미지 위에 자막. --next-preview-lines 로 CLI 오버라이드.
        ★00_meta.json의 info_card_text가 있으면 info_card_after_line(0-based 자막 인덱스)의
          자막이 끝난 직후부터 info_card_sec초(기본 6.0) 동안 화면 상단에 오버레이로
          정보카드(기관명/전화번호 등 실생활 대처 정보, WebSearch 검증 필수)를 띄운다.
          하단에 info_card_disclaimer(기본 "⚠ 참고용 정보 · 법률 자문 아님")를 함께 표시.
          TitleCard와 동일하게 독립 레이어라 비디오 세그먼트 타임라인은 건드리지 않는다.
          필드 없으면 조용히 생략(하위호환) — `docs/PRACTICAL_INFO_FORMAT.md` 참조.
- 출력: productions/<slug>/06_render_v1.mp4  (1080×1920 · 30fps · h264+aac)

사용:  python scripts/compose_narration.py <slug> [--out 06_render_v1.mp4] [--marginv 420] [--fontsize 58] [--hook-scale 1.5] [--title-card-sec 1.8] [--next-preview-lines N]
"""
import os, sys, re, json, glob, argparse, subprocess
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF="/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"; FP="/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
if not os.path.exists(FF): FF="ffmpeg"
if not os.path.exists(FP): FP="ffprobe"
W,H,FPS=1080,1920,30

def dur(f):
    return float(subprocess.run([FP,"-v","error","-show_entries","format=duration","-of","csv=p=0",f],
                                capture_output=True,text=True).stdout.strip() or 0)

def korean_font():
    fcl=subprocess.run(["fc-list",":lang=ko","family"],capture_output=True,text=True).stdout
    cands=[x.strip().split(",")[0] for x in fcl.splitlines() if x.strip()]
    for pref in ["Apple SD Gothic Neo","AppleSDGothicNeo","NanumGothic","Noto Sans CJK KR","Nanum Gothic","Malgun Gothic"]:
        if any(pref in c for c in cands): return pref
    return cands[0] if cands else "Apple SD Gothic Neo"

def fmt(t):
    h=int(t//3600); m=int((t%3600)//60); s=t%60; return f"{h}:{m:02d}:{s:05.2f}"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("slug")
    ap.add_argument("--out",default="06_render_v1.mp4"); ap.add_argument("--marginv",type=int,default=420)
    ap.add_argument("--fontsize",type=int,default=58)
    ap.add_argument("--hook-scale",type=float,default=1.5,help="훅(첫 자막 줄) 폰트 배율 — 인스타툰식 큰 제목카드 표준(2026-07-07)")
    ap.add_argument("--title-card-sec",type=float,default=1.8,help="오프닝 썸네일 제목카드 노출 초 — 0=비활성화(2026-07-09 표준)")
    ap.add_argument("--next-preview-lines",type=int,default=None,help="마지막 N개 자막(다음편 떡밥)을 블랙카드로 중앙에 띄움 — 미지정 시 00_meta.next_preview_lines(기본 0=off)")
    ap.add_argument("--text-card-lines",default=None,help="중간 타이포 카드로 뺄 자막 번호(1-based, 예 '11,12,17'). 미지정 시 00_meta.text_card_lines. 이미지가 부족할 때 빈 비트를 톤 붕괴 없이 메우는 용도로도 쓴다")
    ap.add_argument("--next-scale",type=float,default=2.0,help="블랙카드(예고·중간 타이포) 글자 배율 — 기본 2.0×fontsize. 화면 전체가 블랙이라 본문 자막보다 훨씬 커야 잘 보인다")
    ap.add_argument("--next-margin",type=int,default=70,help="블랙카드 좌우 여백(px) — 기본 70(작을수록 한 줄이 넓게 앉는다)")
    ap.add_argument("--info-card-sec",type=float,default=None,help="정보카드 노출 초 — 미지정 시 00_meta.info_card_sec(기본 6.0)")
    ap.add_argument("--kenburns",action="store_true",help="PNG 스틸에 Ken Burns(느린 줌인) 적용 — 롱폼/스틸 위주용. 첫 비트는 더 강한 푸시인.")
    a=ap.parse_args()
    prod=os.path.join(ROOT,"productions",a.slug); fdir=os.path.join(prod,"flow_images")
    tmp=os.path.join(prod,"_tmp_compose"); segd=os.path.join(tmp,"seg"); os.makedirs(segd,exist_ok=True)
    T=json.load(open(os.path.join(prod,"04_timing.json"),encoding="utf-8"))
    try:
        meta=json.load(open(os.path.join(prod,"00_meta.json"),encoding="utf-8"))
    except Exception:
        meta={}
    # 시간순 정렬 (비트번호 아님) — 비트 재사용(회상 컷)이 있으면 비트번호 정렬은 영상/오디오 어긋남
    beats=sorted(T["beats"],key=lambda x:x["start"]); subs=T["subtitles"]
    audio=os.path.join(prod,T.get("narration","03_audio_narration_only.mp3")); adur=dur(audio)
    # 연속으로 같은 비트/같은 파일인 세그먼트 병합 — _beat_map.json 으로 여러 라인이
    # 한 이미지에 묶여도 이전엔 라인마다 별도 세그먼트를 만들어 Ken Burns 줌이 라인
    # 경계마다 1.0으로 리셋됐다(한 이미지인데도 여러 번 빠르게 당겨지는 문제,
    # 2026-07 실사용 피드백). 자막(subs)은 그대로 라인 단위라 별개로 유지됨.
    merged=[]
    for b in beats:
        if merged and merged[-1]["beat"]==b["beat"] and merged[-1]["file"]==b["file"]:
            merged[-1]["end"]=b["end"]
        else:
            merged.append(dict(b))
    beats=merged
    # 마지막 비트를 오디오 끝까지 연장(트레일링 무음 동안 마지막 컷 hold)
    if beats: beats[-1]["end"]=round(max(beats[-1]["end"], adur)+0.1,3)
    video_end=beats[-1]["end"] if beats else round(adur+0.1,3)

    # ★다음 이야기 예고 블랙카드(2026-07-09): 마지막 N개 자막을 이미지 위에 겹치지 않고
    # 화면 전체를 블랙으로 덮은 뒤 중앙에 크게 띄운다("이미지 위 겹침이 혼잡"하다는 피드백).
    # black_start = 그 자막들 중 가장 이른 start. 그 시점부터 이미지 비트를 잘라내고 블랙 세그먼트로 대체.
    npl=a.next_preview_lines if a.next_preview_lines is not None else int(meta.get("next_preview_lines",0) or 0)
    teaser_ids=set(); black_start=None
    if npl>0 and len(subs)>=npl:
        teaser_ids=set(range(len(subs)-npl,len(subs)))
        black_start=round(min(subs[i]["start"] for i in teaser_ids),3)

    # ★중간 타이포 카드(2026-08-10): 00_meta.text_card_lines = [S번호…] 인 자막 구간을
    #   이미지 대신 **완전 블랙 + 중앙 큰 글씨**로 대체한다(예고 블랙카드와 같은 연출을 본문 중간에).
    #   용도 ①핵심 대사 강조 ②이미지가 부족할 때 빈 비트를 톤 붕괴 없이 메움(동물·무관 이미지 대신).
    #   비용 0원 — 명언 트랙이 검증한 "텍스트만으로 붙잡는" 포맷.
    tcl=a.text_card_lines if a.text_card_lines is not None else meta.get("text_card_lines") or []
    if isinstance(tcl,str): tcl=[x for x in re.split(r"[,\s]+",tcl) if x]
    card_ids={int(x)-1 for x in tcl if str(x).strip().lstrip("S").isdigit()}
    card_ids={i for i in card_ids if 0<=i<len(subs)}-teaser_ids

    # 블랙 구간 = 연속된 카드 자막을 병합 + 말미 예고 구간
    ranges=[]
    for i in sorted(card_ids):
        s,e=subs[i]["start"],subs[i]["end"]
        if ranges and s-ranges[-1][1]<0.06: ranges[-1][1]=e
        else: ranges.append([s,e])
    if black_start is not None: ranges.append([black_start,video_end])
    ranges=[(round(s,3),round(e,3)) for s,e in ranges if e-s>=1/FPS]

    if ranges:   # 블랙 구간과 겹치는 이미지 비트를 잘라낸다(겹친 부분은 어차피 안 보임)
        cut=[]
        for b in beats:
            pieces=[(b["start"],b["end"])]
            for rs,re_ in ranges:
                nxt=[]
                for ps,pe in pieces:
                    if pe<=rs or ps>=re_: nxt.append((ps,pe)); continue
                    if ps<rs: nxt.append((ps,min(pe,rs)))
                    if pe>re_: nxt.append((max(ps,re_),pe))
                pieces=nxt
            for ps,pe in pieces:
                if pe-ps>=1/FPS:
                    nb2=dict(b); nb2["start"]=round(ps,3); nb2["end"]=round(pe,3); cut.append(nb2)
        beats=cut
        if card_ids:
            print(f"  ✅ 중간 타이포 카드: {len(card_ids)}줄 → 블랙 구간 {len(ranges)-(1 if black_start is not None else 0)}개")

    base=f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p,setsar=1"
    listf=os.path.join(tmp,"list.txt"); L=[]
    # 콜드오픈 강줌 = 선두에서 첫 비트번호가 '연속'되는 세그먼트까지만 (후반 회상 컷 재등장은 일반 줌)
    lead=0
    while lead<len(beats) and beats[lead]["beat"]==beats[0]["beat"]: lead+=1
    if a.kenburns: print("  🎥 Ken Burns 모드 (PNG 스틸 줌인)")
    # ★타임라인 = 이미지 비트 + 블랙 구간을 **시간순으로 인터리브**(2026-08-10).
    #   예전엔 이미지 전부 → 말미 블랙 1개였다. 중간 타이포 카드가 생기면서 순서가 섞여야 한다.
    tl=[{"start":b["start"],"end":b["end"],"kind":"img","b":b} for b in beats] \
       +[{"start":s,"end":e,"kind":"black"} for s,e in ranges]
    tl.sort(key=lambda x:x["start"])
    print(f"▶ 세그먼트 {len(tl)}개 빌드 (이미지 {len(beats)} + 블랙 {len(ranges)})...")
    for idx,item in enumerate(tl):
        d=max(round(item["end"]-item["start"],3),round(1/FPS,3))
        seg=os.path.join(segd,f"seg{idx:03d}.mp4")
        if item["kind"]=="black":
            bc=subprocess.run([FF,"-y","-loglevel","error","-f","lavfi","-i",f"color=c=black:s={W}x{H}:r={FPS}",
                "-t",str(d),"-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p","-r",str(FPS),
                "-video_track_timescale","30000","-an",seg],capture_output=True,text=True)
            if bc.returncode!=0 or not os.path.exists(seg):
                raise SystemExit(f"❌ 블랙 세그먼트 seg{idx:03d}: {(bc.stderr or '')[:200]}")
            L.append(f"file '{seg}'"); continue
        b=item["b"]
        # seg 파일명 = 순번(idx). 비트번호로 하면 한 컷이 여러 라인에 걸칠 때(롱폼) 같은 비트가 덮어써짐.
        # d 최소 1프레임 보장 — '-t 0'은 ffmpeg가 무제한으로 해석해 hang
        f=os.path.join(fdir,b["file"])
        if not os.path.exists(f): raise SystemExit(f"❌ {b['file']} 없음 (normalize_flow_assets 먼저)")
        common=["-c:v","libx264","-preset","veryfast","-crf","20","-pix_fmt","yuv420p","-r",str(FPS),"-video_track_timescale","30000","-an",seg]
        if f.endswith(".png"):
            if a.kenburns:
                frames=max(1,int(round(d*FPS)))
                zmax=1.20 if idx<lead else 1.11   # 콜드오픈 선두 연속 구간만 강한 푸시인
                inc=round((zmax-1.0)/frames,6)
                kb=(f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
                    f"zoompan=z='min(zoom+{inc},{zmax})':d={frames}:"
                    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},format=yuv420p,setsar=1")
                cmd=[FF,"-y","-loglevel","error","-loop","1","-i",f,"-vf",kb,"-t",str(d)]+common
            else:
                cmd=[FF,"-y","-loglevel","error","-loop","1","-t",str(d),"-i",f,"-vf",base]+common
        else:
            cl=dur(f); pad=max(0.0,d-cl)
            vf=base+(f",tpad=stop_mode=clone:stop_duration={round(pad,3)}" if pad>0.05 else "")
            cmd=[FF,"-y","-loglevel","error","-i",f,"-vf",vf,"-t",str(d)]+common
        r=subprocess.run(cmd,capture_output=True,text=True)
        if r.returncode!=0 or not os.path.exists(seg):
            raise SystemExit(f"❌ seg{idx:03d}(beat {b['beat']}): {(r.stderr or '')[:200]}")
        L.append(f"file '{seg}'")
    if black_start is not None:
        print(f"  ✅ 다음이야기 예고 블랙카드: {npl}줄 · {round(video_end-black_start,1)}s (black_start={black_start:.1f}s)")
    open(listf,"w").write("\n".join(L)); print(f"  ✅ {len(L)} 세그먼트")

    fam=korean_font(); print(f"  자막 폰트: {fam}")
    ass=os.path.join(tmp,"subs.ass")
    hook_fontsize=round(a.fontsize*a.hook_scale)
    title_fontsize=round(a.fontsize*2.3)
    # ★2026-08-10: 블랙카드(예고·중간 타이포)는 화면 전체가 비어 있으므로 자막 크기 그대로면 작아 보인다
    #   ("텍스트 더 키워달라" 사용자 피드백). 기본 2.0배 + 좌우 여백 축소로 글자가 넓게 앉게 한다.
    next_fontsize=round(a.fontsize*a.next_scale)
    info_fontsize=round(a.fontsize*1.3); info_disc_fontsize=round(a.fontsize*0.55)
    # 정보카드 disclaimer 위치 조정: 다중 라인 info_card_text 지원
    # info_card_text에 \n이 포함되면 그 수만큼 레이아웃이 높아지므로, MarginV를 그에 맞춰 조정
    info_lines=max(1,(meta.get("info_card_text") or "").count("\n")+1)
    header=(f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 0\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Def,{fam},{a.fontsize},&H00FFFFFF,&H00000000,&H64000000,1,1,4,1,2,90,90,{a.marginv},1\n"
            f"Style: Hook,{fam},{hook_fontsize},&H00FFFFFF,&H00000000,&H64000000,1,1,5,1,2,60,60,{a.marginv},1\n"
            f"Style: TitleCard,{fam},{title_fontsize},&H00FFFFFF,&H00000000,&HB0000000,1,3,8,0,8,60,60,320,1\n"
            # NextCard: 블랙 화면 중앙(Alignment 5) 정렬 예고 카드 — 밴드 없음(배경이 이미 블랙), 얇은 외곽선만.
            f"Style: NextCard,{fam},{next_fontsize},&H00FFFFFF,&H00000000,&H00000000,1,1,3,0,5,{a.next_margin},{a.next_margin},0,1\n"
            f"Style: InfoCard,{fam},{info_fontsize},&H00FFFFFF,&H00000000,&HB0000000,1,3,8,0,8,60,60,320,1\n"
            f"Style: InfoDisclaimer,{fam},{info_disc_fontsize},&H00CCCCCC,&H00000000,&H00000000,1,1,2,0,8,60,60,{320+info_fontsize*info_lines+30},1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    def esc(t): return t.replace("\\","\\\\").replace("{","(").replace("}",")").replace("\n","\\N")
    # 예고(teaser) 라인은 NextCard(블랙 중앙) 스타일로, 나머지는 Hook(첫줄)/Def(본문).
    def _style(i):
        if i in teaser_ids or i in card_ids: return "NextCard"   # 블랙 위 중앙 큰 글씨
        return "Hook" if i==0 else "Def"
    ev=[f"Dialogue: 0,{fmt(s['start'])},{fmt(s['end'])},{_style(i)},,0,0,0,,{esc(s['text'])}" for i,s in enumerate(subs)]
    # 예고 카드는 마지막 자막 end 이후 트레일링(블랙 hold) 구간까지 글자를 유지 → end를 video_end로 연장.
    if teaser_ids:
        last_i=max(teaser_ids)
        s=subs[last_i]
        ev[last_i]=f"Dialogue: 0,{fmt(s['start'])},{fmt(video_end)},NextCard,,0,0,0,,{esc(s['text'])}"
    # ★썸네일 제목카드(2026-07-09): 00_meta.thumbnail_title 이 있으면 오프닝 --title-card-sec초 동안
    # 화면 상단에 압축된 '막장 제목'을 큰 박스체로 겹쳐 노출(나레이션 자막과 별개 레이어=Layer 10, 동시 노출).
    # 필드 없는 구버전 production은 조용히 생략(하위호환).
    title_text=(meta.get("thumbnail_title") or "").strip()
    if title_text and a.title_card_sec>0:
        ev.append(f"Dialogue: 10,{fmt(0)},{fmt(a.title_card_sec)},TitleCard,,0,0,0,,{esc(title_text)}")
        print(f"  ✅ 제목카드: \"{title_text}\" ({a.title_card_sec}s)")
    elif a.title_card_sec>0:
        print("  ⚠️ 00_meta.json에 thumbnail_title 없음 → 오프닝 제목카드 생략(구버전 production 정상)")
    # ★정보카드(정보형 사연 서브트랙, docs/PRACTICAL_INFO_FORMAT.md): info_card_text 있으면
    # info_card_after_line 자막이 끝난 시점부터 info_card_sec초 동안 오버레이 노출.
    info_text=(meta.get("info_card_text") or "").strip()
    info_after=meta.get("info_card_after_line")
    if info_text and type(info_after) is int and 0<=info_after<len(subs):
        info_sec=a.info_card_sec if a.info_card_sec is not None else float(meta.get("info_card_sec",6.0) or 6.0)
        ic_start=subs[info_after]["end"]
        cap = black_start if black_start is not None else video_end
        ic_end=min(round(ic_start+info_sec,3), cap)
        if ic_end>ic_start:
            ev.append(f"Dialogue: 10,{fmt(ic_start)},{fmt(ic_end)},InfoCard,,0,0,0,,{esc(info_text)}")
            info_disc=meta.get("info_card_disclaimer","⚠ 참고용 정보 · 법률 자문 아님")
            if info_disc:
                ev.append(f"Dialogue: 10,{fmt(ic_start)},{fmt(ic_end)},InfoDisclaimer,,0,0,0,,{esc(info_disc)}")
            print(f"  ✅ 정보카드: \"{info_text}\" ({ic_end-ic_start:.1f}s, 자막#{info_after} 이후)")
        else:
            print(f"  ⚠️ 정보카드 노출 구간이 0초 이하로 축소됨(info_card_after_line={info_after}) → 생략")
    elif meta.get("story_type")=="practical_info":
        print("  ⚠️ story_type=practical_info인데 info_card_text/info_card_after_line 없음 → 정보카드 생략")
    open(ass,"w",encoding="utf-8").write(header+"\n".join(ev)+"\n")
    print(f"  ✅ subs.ass ({len(subs)} 라인)")

    out=os.path.join(prod,a.out)
    print("▶ concat + 자막 burn + 오디오 mux...")
    r=subprocess.run([FF,"-y","-loglevel","error","-f","concat","-safe","0","-i",listf,"-i",audio,
        "-vf",f"ass='{ass}'","-map","0:v","-map","1:a","-c:v","libx264","-preset","medium","-crf","19",
        "-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",out],
        capture_output=True,text=True)
    if r.returncode!=0 or not os.path.exists(out):
        raise SystemExit(f"❌ compose: {(r.stderr or '')[-500:]}")
    print(f"✅ {a.out}  {dur(out):.1f}s  {os.path.getsize(out)//1024//1024}MB")

    # 키즈 표준(2026-06-17 사용자 지침): kids_edu 트랙은 큰 글자 교육 오버레이를 '무조건' 자동 적용.
    if meta.get("track")=="kids_edu":
        spec=os.path.join(prod,"_edu_overlay.json")
        ovs=os.path.join(os.path.dirname(os.path.abspath(__file__)),"overlay_kids_letters.py")
        if a.out!="06_render_v1.mp4":
            print(f"⚠️ [키즈 표준] --out 이 기본(06_render_v1.mp4)이 아니라 자동 오버레이 생략: {a.out}")
        elif not os.path.exists(spec):
            print("⚠️ [키즈 표준] _edu_overlay.json 없음 → 큰 글자 미적용! 키즈 영상은 자모/단어 사양(_edu_overlay.json)이 필수.")
        else:
            print("▶ [키즈 표준] 큰 글자 교육 오버레이 자동 적용...")
            rr=subprocess.run([sys.executable,ovs,a.slug,"--refresh"],capture_output=True,text=True)
            print(((rr.stdout or "")+(rr.stderr or "")).strip()[-400:])
            if rr.returncode!=0:
                print("⚠️ 오버레이 실패 — 위 로그 확인")

if __name__=="__main__":
    main()
