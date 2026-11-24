#!/bin/bash
cat <<'__PREP_UPLOAD_EOF__' | pbcopy
이사장 아들에겐 침대가 있었다｜한성의료원 1997 EP.2 [오리지널 드라마]
__PREP_UPLOAD_EOF__
echo "✅ 유튜브 제목이 클립보드에 복사됐습니다. 업로드 칸에 Cmd+V 로 붙여넣으세요."
nohup bash -c 'sleep 0.6; osascript -e "tell application \"Terminal\" to close front window"' >/dev/null 2>&1 &
