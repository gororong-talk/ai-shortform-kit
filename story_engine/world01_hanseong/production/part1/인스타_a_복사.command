#!/bin/bash
cat <<'__PREP_UPLOAD_EOF__' | pbcopy
IMF 그해 겨울, 치료비 512만원 때문에 병원 문 앞에서 쫓겨난 노인.
그런데 이사장 아들의 손님에겐, 침대가 있었다.

한성의료원 1997 · 1부 [①/②]
▶ 그가 왜 죽었는지, ②편에서 밝혀집니다.

🤖 AI로 만든 창작 드라마입니다. 가상의 인물·사건이며 실제와 무관합니다.
#막장드라마 #오리지널드라마 #IMF #웹툰드라마 #반전결말 #AI드라마 #릴스 #단편드라마
__PREP_UPLOAD_EOF__
echo "✅ 인스타 A편 캡션이 클립보드에 복사됐습니다. 업로드 칸에 Cmd+V 로 붙여넣으세요."
nohup bash -c 'sleep 0.6; osascript -e "tell application \"Terminal\" to close front window"' >/dev/null 2>&1 &
