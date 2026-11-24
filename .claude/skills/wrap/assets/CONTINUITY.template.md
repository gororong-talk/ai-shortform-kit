# 🔄 CONTINUITY — 세션 인계 / handoff

> 이 문서만 보면 다음 세션이 이어받을 수 있게 유지한다.
> 체크포인트 훅(`.claude/hooks/session_checkpoint.py`)이 아래 **"## Pending"** 섹션을
> 자동 추출해 `/clear`·재시작 후 새 컨텍스트에 주입한다.

## Pending / 다음 명령 (Next actions)

<!-- 다음 세션이 가장 먼저 할 일. 가장 위 = 가장 급함. /wrap이 이 섹션을 갱신한다. -->

- [ ] (다음 작업을 여기에 한 줄로 — 파일경로·명령까지 적어 cold-start가 바로 실행 가능하게)
