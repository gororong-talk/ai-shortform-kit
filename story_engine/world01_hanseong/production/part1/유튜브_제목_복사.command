#!/bin/bash
cat <<'__PREP_UPLOAD_EOF__' | pbcopy
돈 때문에 병원 문 앞에서 쫓겨나 죽은 노인｜한성의료원 1997 EP.1 [오리지널 드라마]
__PREP_UPLOAD_EOF__
echo "✅ 유튜브 제목이 클립보드에 복사됐습니다. 업로드 칸에 Cmd+V 로 붙여넣으세요."
nohup bash -c 'sleep 0.6; osascript -e "tell application \"Terminal\" to close front window"' >/dev/null 2>&1 &
