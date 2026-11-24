#!/bin/bash
cat <<'__PREP_UPLOAD_EOF__' | pbcopy
돈으로 사람을 문 앞에서 돌려보낸 자에게, 이번엔 칼이 돌아온다.

한성의료원 1997 · 완결편 [②/②]
돈이 사람을 돌려보내는 겨울은, 아직 끝나지 않았다.

🤖 AI로 만든 창작 드라마입니다. 가상의 인물·사건이며 실제와 무관합니다.
#막장드라마 #오리지널드라마 #IMF #웹툰드라마 #반전결말 #AI드라마 #릴스 #단편드라마
__PREP_UPLOAD_EOF__
echo "✅ 인스타 B편 캡션이 클립보드에 복사됐습니다. 업로드 칸에 Cmd+V 로 붙여넣으세요."
nohup bash -c 'sleep 0.6; osascript -e "tell application \"Terminal\" to close front window"' >/dev/null 2>&1 &
