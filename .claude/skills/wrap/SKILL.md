---
name: wrap
description: 작업/세션을 디스크에 안전하게 남겨 다음 fresh 컨텍스트(/clear·새 세션)가 손실 없이 이어받게 하는 핸드오프 마무리. CONTINUITY.md "## Pending"(다음 액션 최상단) 갱신 + 커밋·push + 체크포인트 갱신. 어느 프로젝트에서나 쓸 수 있는 전역 스킬 — 셋업 안 된 프로젝트면 먼저 부트스트랩(체크포인트 훅·CONTINUITY 자동 설치)을 제안한다. 사용자가 "/wrap", "정리하고 클리어", "clear 준비", "세션 마무리", "핸드오프", "이거 끝, 다음", "마무리하고 비우자" 같은 표현 사용 시 호출.
---

# /wrap — `/clear` 전 핸드오프 마무리 (전역, 자동 셋업 포함)

## 왜
대화형 에이전트 비용의 큰 부분이 **컨텍스트 재읽기**(세션이 길수록 매 턴 비싸짐). 그래서 **작업 1건 = 1 컨텍스트, 끝나면 `/clear`로 비우기**가 토큰 최대 절감. 단 `/clear`는 대화 맥락을 지우므로, **지우기 전에 "한 일 + 다음 할 일"을 디스크(git + CONTINUITY)에 남겨야** 다음 fresh 컨텍스트가 이어받는다. SessionStart 훅이 `/clear` 후 체크포인트(git 상태 + CONTINUITY Pending)를 자동 주입 — 이 둘만 최신이면 손실 0.

## 0. 부트스트랩 — 셋업 안 된 프로젝트 첫 사용 시 (전역 스킬 핵심)
먼저 이 프로젝트가 continuity 셋업돼 있는지 확인:
```bash
ls .claude/hooks/session_checkpoint.py CONTINUITY.md 2>/dev/null
```
**둘 중 하나라도 없으면** — 사용자에게 "이 프로젝트에 /wrap·자동복원 셋업을 설치할까요?" 확인 후:
```bash
python3 ~/.claude/skills/wrap/assets/setup_continuity.py
```
→ `.claude/hooks/session_checkpoint.py` + `.claude/settings.json` 훅(PreCompact·SessionStart) + `CONTINUITY.md` 템플릿을 **있는 것만 건너뛰고** 설치(멱등). git 저장소 아니면 `git init` 권장.
**둘 다 있으면** 부트스트랩 건너뛰고 1번부터.

## 1~9. 마무리 절차 (이 순서대로)
1. **이번 세션 한 일 1~3줄 요약** (사용자에게 보고).
2. **스킬 검토 — 이번 세션(직전 `/clear` 이후 ~ 지금)에서 스킬로 남길 것이 있는지 판정.** 아래 네 트리거를 하나씩 훑고 각각 "해당 / 없음"을 답한다:
   - **같은 수동 절차를 2회 이상 반복**했다 → 신규 스킬 후보(이름 + 트리거 한 줄).
   - **기존 스킬을 따라갔는데 빠진 단계·틀린 경로·낡은 내용이 있었다** → 그 스킬 수정 후보(`~/.claude/skills/<name>/SKILL.md` + 고칠 지점).
   - **새 함정을 해결**했다 → 재사용 범위 판정(WORKSTYLE §6): 이 프로젝트만=CONTINUITY / 플랫폼 전반=전역 스킬 / 나에 대한 것=메모리. **같은 실수가 2번 났다면 기록 위치가 틀린 것 → 더 넓은 범위로 승격.** 판정 전에 CONTINUITY·HISTORY·메모리를 함정 키워드로 grep해 이전 기록이 있는지 확인한다(대화 맥락만으론 '2번째'를 알 수 없다).
   - **도구 한계가 공식 에러·문서로 확정**됐다 → 해당 스킬에 "불가"로 박제(다음 세션이 재시도하지 않게).
   판정은 하고 **스킬·SKILL.md 편집은 wrap 안에서 하지 않는다**(wrap = 마무리 전용). 단 함정 한 줄을 CONTINUITY/HISTORY/메모리에 기록하는 것은 wrap 범위다. 제안은 사용자 확인을 기다리지 않고 3번 Pending **최상단**에 다음 액션으로 적는다. 사용자가 "지금 고쳐"라고 하면 그때 `superpowers:writing-skills`로 진입.
3. **CONTINUITY.md `## Pending` 갱신** — ★가장 중요(다음 fresh 컨텍스트가 읽는 곳).
   - **다음 구체적 액션을 맨 위에** (명령·파일경로·결정까지 적어 cold-start가 바로 실행 가능하게).
   - **완료된 항목(`[x]`)은 언제 끝났든 Pending에 남기지 말고 그 자리에서 HISTORY.md로 옮긴다**(6번에서 쓰는
     같은 항목이면 HISTORY에 쓰고 Pending에서는 지운다). Pending은 **다음에 할 일만** 담는다 — `[x]`가 쌓이면
     세션시작 주입(체크포인트 훅)이 그만큼 커진다. 실측 2026-11-10: `[x]` 누적이 Pending 발췌를 4.5 KB로 키웠다.
   - "마지막 갱신: YYYY-MM-DD" 갱신.
4. **묵힌 기록 정리 — 3일 규칙** (CONTINUITY가 쓰레기통이 되는 것 방지):
   ```bash
   python3 ~/.claude/skills/wrap/assets/stale_pending.py --today <오늘YYYY-MM-DD>
   # Pending이 다른 파일에 있는 프로젝트: --file RESTART_PROTOCOL.md (blockquote `> 1. …` 항목도 인식)
   ```
   읽기 전용 — 이 스크립트는 한 줄도 쓰거나 지우지 않는다. 기준일은 `--days N`(기본 3).
   - **묵은 항목 0건이면 그대로 넘어간다**(단 출력이 `총 0 항목`이면 `## Pending` 헤딩 형식이 스크립트와 맞는지 먼저 확인 — 헤딩 불일치는 조용히 0건이 된다). 1건 이상이면 **한 번에 묶어서 사용자에게 묻는다**(항목별 질문 난사 금지):
     - 미완료 `[ ]` 묵은 항목 → **유지(줄 앞에 오늘 날짜 기입) / 재작성(지금 유효한 다음 액션으로) / 삭제** 3택.
     - 완료 `[x]` 묵은 항목 → 3번대로라면 애초에 없어야 한다. 남아 있으면 **HISTORY.md에 그 내용이 있는지 확인**하고,
       없으면 6번 HISTORY 항목으로 옮긴 뒤 삭제한다(이건 3일을 기다릴 일이 아니다 — 3일 규칙은 **미완료 항목용**이다).
     - 서술형(체크박스 없는) 줄 묶음 → "HISTORY로 옮기고 Pending에서 뺄까요?"를 **한 건으로** 묻는다.
   - **미완료·서술형 항목은 사용자 승인 없이 한 줄도 지우지 않는다.** 묵었다는 것은 삭제 사유가 아니라 질문 사유다. `[x]`는 HISTORY에 내용이 있음을 확인한 경우에만 지우고, 지운 목록을 묶어 보고한다.
5. **로드맵·마일스톤 갱신 — `ROADMAP.md`가 있을 때만** (큰 그림 + 현재 위치):
   - 먼저 **이번 세션 도달분 + HISTORY/git log에 완료 근거가 있는데 `[ ]`로 남은 항목의 체크박스를 `[x]`로 바꾼다**(완료 근거가 있는 것만 — 추측 금지). 새로 생긴 일은 해당 마일스톤에 `- [ ]`로 추가.
   - 그다음 현재 위치 줄을 체크박스에서 재계산:
     ```bash
     python3 ~/.claude/skills/wrap/assets/roadmap_status.py --sync
     ```
     `> **현재 위치:** M<n> <이름> · done/total 완료 · 다음: <첫 미완료 항목>` **한 줄만** 고친다(문서의 나머지는 건드리지 않음). sync가 '신규 삽입'을 출력하면 옛 형식의 현재 위치 줄(`**현재 위치**: …` 등)이 남았는지 확인해 지운다. exit 2(헤딩 형식 불일치)면 출력의 로드맵 줄에 '형식 불일치'라고 쓰고 넘어간다. 마일스톤이 전부 `[x]`면 다음 마일스톤으로 자동 이동한다. 헤딩 앞 상태 기호(`## ✅ M0 —`, `## ▶ M9 —`)는 인식한다. 현재 위치를 **헤딩**(`## 📍 현재 위치: …`)으로 손관리하는 프로젝트는 `--sync`를 쓰지 않는다(중복 줄 삽입) — 읽기 전용 실행 결과만 참고.
   - **ROADMAP.md가 없으면 만들지 않는다** — 전역 규칙상 3단계 이상 장기 프로젝트만 ROADMAP을 유지하고, 그 외 프로젝트의 진실원은 CONTINUITY `## Pending`이다. 필요해 보이면 **제안만** 한다.
6. **HISTORY.md에 이번 세션 항목 추가** — append-only 작업 로그(회고·영상·감사용). CONTINUITY(다음 할 일·짧게·세션시작 주입)와 **반대 방향** = 절대 편집·삭제 없이 쌓기만 하는 유일한 영구 연대기(완료항목처럼 덮어써지지 않음). 커밋 전에 넣어 같은 wrap 커밋에 포함:
   ```bash
   python3 ~/.claude/skills/wrap/assets/append_history.py --date <오늘YYYY-MM-DD> --title "<한 줄 제목>" <<'EOF'
   - 한 일: <핵심 산출물>
   - 결정/이유: <왜 이렇게 했나 — 코드로 안 남는 판단>
   - 함정→해법: <부딪힌 것과 해결. 없으면 생략>
   - 산출물/링크: <파일·아티팩트·PR>
   EOF
   ```
   없으면 헤더와 함께 자동 생성. `--commit <hash>`는 선택(직전 커밋 참조 시). **요약을 말로만 하고 버리지 말 것 — 여기 박제.**
7. **커밋 + push** (가능하면 분할 — system/기능별). CONTINUITY + HISTORY 변경 포함. `/wrap` 호출 = 커밋 위임으로 간주. working tree clean 확인. (git 저장소 아니면 스킵하고 사용자에게 고지.)
8. **체크포인트 갱신**: `python3 .claude/hooks/session_checkpoint.py --write` (SessionStart도 자동 재생성하지만 명시적으로 최신화).
9. **검증 + 안내**: `git rev-parse --short HEAD` = `origin/<branch>` 확인 → **"이제 `/clear` 해도 안전. 다음 세션은 [다음 액션]부터."**

## 출력 형식
```
✅ wrap 완료
- 이번 세션: <1~3줄>
- 묵힌 기록(3일+): <없음 | 체크박스 N건·서술형 M줄 → 삭제 a / 유지 b / HISTORY이전 c>
- 스킬 검토: <T1반복 o/x · T2스킬결함 o/x · T3함정 o/x · T4도구한계 o/x | 제안: <신규 스킬명 또는 수정할 SKILL.md> (Pending에 기록)>
- 로드맵: <없음(ROADMAP.md 미보유) | M<n> <이름> d/t · 다음: <한 줄>>
- 커밋: <hash> push됨 (tree clean)   ← git 없으면 "커밋 스킵(비 git)"
- 다음 액션(CONTINUITY 최상단): <한 줄>
→ /clear 안전. 새 컨텍스트가 체크포인트로 자동 복원됨.
```
**"묵힌 기록"·"스킬 검토"·"로드맵" 세 줄은 항상 출력한다** — 해당 없으면 `없음`이라고 쓴다. 줄 자체를 빼지 않는다.

## 주의
- CONTINUITY Pending엔 **추측 금지** — 실제 다음 액션만. 모르면 "다음 결정 필요: X".
- **CONTINUITY ≠ HISTORY.** CONTINUITY는 앞(다음 할 일)·짧게·계속 덮어씀·세션시작 주입. HISTORY는 뒤(한 일)·계속 쌓기·절대 편집삭제·주입 안 함. **둘을 한 파일로 합치지 말 것**(합치면 cold-start 읽기 비용↑ → 토큰절감 붕괴).
- 재사용 교훈(함정·표준)은 프로젝트 메모리/문서에도 박제.
- 커밋할 게 없으면 7번(커밋) 스킵하고 CONTINUITY/HISTORY만 갱신. 이 스킬은 **마무리 전용** — 새 작업 시작 안 함.
- **프로젝트 전용 버전이 있으면 그게 우선**(프로젝트 `.claude/skills/wrap/`가 이 전역본을 덮어씀) — 프로젝트별 맞춤 절차 가능.

## 참조
- 번들: `~/.claude/skills/wrap/assets/` (session_checkpoint.py · setup_continuity.py · CONTINUITY.template.md · append_history.py · stale_pending.py · roadmap_status.py).
- HISTORY.md: append-only 작업 연대기. `append_history.py`가 없으면 자동 생성(헤더 포함)·항상 파일 끝에만 추가(`open(...,'a')`) — 기존 항목 절대 안 건드림.
- `stale_pending.py`: `## Pending` 섹션만 읽어 항목별 나이 판정(줄 안의 `YYYY-MM-DD` → 없으면 `git blame` author-time → 둘 다 없으면 `age=?`로 두고 **묵음 판정 안 함**). 체크박스 항목은 줄별로, 서술형은 묶음 1줄로 보고.
- `roadmap_status.py`: `## M<n> <이름>` 헤딩 + 그 아래 체크박스로 마일스톤 진행률 표(막대·done/total·완료/진행중/대기)를 뽑고, `--sync`일 때만 `> **현재 위치:**` 줄 하나를 재작성. 진행률의 진실원은 **체크박스**이며 현재 위치 줄은 파생값이다(손으로 고치면 다음 wrap이 덮어씀).
- 훅 동작: PreCompact `--write` / SessionStart 모든 source(`matcher:""`)에서 `--write`→`--session-start` 주입.
