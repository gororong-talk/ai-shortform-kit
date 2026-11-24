---
name: checkpoint
description: >-
  세션 상태를 손실 없이 스냅샷하고 compact 후 자동 복원 (Claude Code session continuity).
  PreCompact 훅이 git/프로세스/pending/최근파일을 .claude/checkpoints/latest.md 로 저장하고,
  SessionStart 훅이 그걸 다시 컨텍스트로 주입한다. 대화상 현재 초점·미결 결정은 Claude가 덧붙인다.
  "체크포인트", "compact 전 저장", "세션 상태 저장", "compact 후 이어가기", "다른 프로젝트에 이식"
  시 사용. Set up / repair / port compact-survival; keywords compact, checkpoint, handoff,
  resume, continuity, PreCompact, SessionStart.
---

# 세션 체크포인트 (compact 손실 방지 + 이식 가능 도구셋)

compact(`/compact`, auto-compact, resume) 후에도 **누락 없이 자연스럽게 재개**하게 한다.
훅 두 개가 핵심:

1. **PreCompact** → `session_checkpoint.py --write` : 요약 직전 운영 상태를
   `.claude/checkpoints/latest.md` 에 스냅샷 (git/프로세스/handoff pending/최근 변경 파일).
2. **SessionStart**(`compact|resume`) → `session_checkpoint.py --session-start` : 그 파일을
   `hookSpecificOutput.additionalContext` 로 출력 → Claude Code가 새 세션 컨텍스트에 주입.

스크립트가 못 잡는 **지금 머릿속의 흐름**(진행 중 결정, 미결 질문, 다음 한 수)은
`CONTINUITY.md`(또는 기존 `RESTART_PROTOCOL.md`)의 **## Pending** 섹션에 적으면 자동 추출된다.

## 두 가지 용법

### A) 지금 이 세션을 수동 체크포인트 (compact 직전)
1. 디스크 사실 캡처: `python3 .claude/hooks/session_checkpoint.py --write`
   → `.claude/checkpoints/latest.md` 생성.
2. **대화 초점 덧붙이기** — `latest.md` 끝에 이번 대화에서만 아는 것을 3~8줄로 Edit/append:
   ```markdown
   ## 🧠 현재 초점 (Claude 수기 — {시각})
   - 지금 하던 일: <한 줄>
   - 미결 결정/대기: <사용자 답 기다리는 질문, 선택지>
   - 다음 한 수: <compact 후 첫 행동 — 구체 명령/파일>
   - 주의/함정: <비자명한 제약>
   ```
3. "체크포인트 저장 완료 — compact 진행해도 안전" 1줄 보고.

### B) 이 시스템을 설치 / 다른 프로젝트로 이식
```bash
# 현재 프로젝트에 설치 (idempotent, 기존 훅 보존)
python3 .claude/skills/checkpoint/scripts/install.py --target . --with-config
# 미리보기
python3 .claude/skills/checkpoint/scripts/install.py --target . --dry-run
# 다른 프로젝트로 이식
python3 .claude/skills/checkpoint/scripts/install.py --target /path/to/other --with-config
# 제거
python3 .claude/skills/checkpoint/scripts/install.py --target . --uninstall
```
설치 후 검증:
```bash
python3 .claude/skills/checkpoint/tests/test_checkpoint.py   # 25 passed
python3 .claude/hooks/session_checkpoint.py                  # 체크포인트 출력
```

## 파일 구성

```
checkpoint/
├── SKILL.md                              # 이 파일
├── README.md                            # 전체 문서 + 이식 가이드
├── scripts/
│   ├── session_checkpoint.py            # 핵심: --write(PreCompact) / --session-start(SessionStart)
│   ├── install.py                       # idempotent 설치/제거 (settings.json 병합)
│   └── continuity_config.example.json   # 선택 설정 (processes/handoff/timezone 등)
├── templates/
│   └── CONTINUITY.md.template           # handoff 문서 스타터
└── tests/
    └── test_checkpoint.py               # 25 stdlib 테스트 (standalone/pytest)
```

## 원칙
- **stdlib only, 훅은 절대 실패 안 함**(모든 단계 try/except → exit 0): 봇/세션 방해 X.
- **bounded**: 체크포인트는 짧게(스크립트 출력 + 수기 8줄). 길면 그 자체가 컨텍스트 bloat.
- **사실 우선**: commit 해시·경로·PID는 스크립트 값 그대로. 추측 X.
- **병합식 설치**: 기존 훅(예: 글로벌 RTK)을 덮지 않음. 재실행해도 중복 안 생김.
- `.claude/checkpoints/` 는 로컬 머신 상태 → git-ignore (이식 대상 아님).
