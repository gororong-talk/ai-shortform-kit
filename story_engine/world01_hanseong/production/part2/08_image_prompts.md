> 🔔 생성 지시(먼저 읽기): 프롬프트대로 이미지를 하나씩 순차 생성. 인물은 CHARACTER_GUIDE 외형을 매 컷 동일하게(레퍼런스 잠금). 영상은 지정된 참조 이미지(B##.png)를 첫 프레임으로 생성. 파일명은 비트명(B01, B02…)과 동일하게 저장.

# 08 IMAGE PROMPTS — 한성의료원 1997 · 2부 「침대는, 있었다」

> 트랙: 인물-구동 롱폼 드라마(가상 인물). **얼굴 O + 캐릭터 일관성 필수**(사연 트랙의 "얼굴 금지" 미적용). 이미지 엔진 = fal.ai FLUX + kontext --ref 레퍼런스 잠금 전제. 1부와 동일 스타일·캐릭터 유지.
> 비트: B01~B13 (**장면 단위 통합** — 1 비트가 여러 나레이션 라인을 받고 **켄번즈 줌·팬**으로 훑는다). 라인-비트 매핑은 _beat_map.json 참조. 여러 라인을 받는 컷은 **구도에 여백**을 둬 켄번즈 팬에 여유를 준다.
> ⚠️ 고인·시신은 **얼굴 프레임 밖 또는 흰 천으로 완전히 덮어 안 보이게**. 특실 손님·과거 인물은 실루엣/정체 숨김.

---

## COMMON_BASE (모든 프롬프트 말미에 이미 포함됨 — 스타일 잠금)
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920

## NEGATIVE (모든 컷 공통 — 생성 시 negative로)
Storybook, any text, caption, title, letters, numbers, signage, brand logo, watermark, signature, modern technology, EMR monitor, flat-screen, smartphone, digital display, LED, western faces, deformed hands, extra fingers, extra limbs, fused fingers, blurry, lowres, jpeg artifacts, oversaturated

시대고증: 1997 지방 종합병원 — 수기 차트·형광등·낡은 미색 복도·연탄난로 겨울·삐삐/시티폰 과도기. **후대 기술(모니터·스마트폰·평판 디스플레이) 금지.** 독촉 쪽지·서류·장부는 **글자 없는 구겨진 종이/괘선만 있는 장부**로만 표현.

---

## CHARACTER_GUIDE (인물별 잠금 외형 — 매 컷 동일 유지)

- **DOHYEON (이도현, 31세 남·응급실 레지던트)**: 178cm 마른 체형, 각진 턱, 짙은 눈썹, 쌍꺼풀 없는 강한 인상, 짙은 다크서클, 이틀 지난 거뭇한 수염 자국, 충혈된 눈. 목깃·소매가 누렇게 전 흰 가운(왼쪽 가슴 볼펜 잉크+커피 얼룩), 회색 반팔 티, 구겨진 슬랙스, 목에 청진기. 지치고 고집스러운 소신파.
- **MANSU (강만수, 52세 남·원무과장)**: 168cm, 팔다리 가늘고 아랫배만 나온 중년형, 어깨가 앞으로 말린 굽신 실루엣. 광대 도드라진 각진 얼굴, 볼 패임, 짙은 눈밑, 벗어진 이마에 옆·뒤 머리를 넘긴 바코드 헤어. 소매 반질반질한 회색·감색 기성복 양복, 누런 와이셔츠 깃, 굵고 짧은 넥타이 매듭, 도수 높은 뿔테 안경. 냉혈해 보이는 사무적 표정.
- **JUNGHYE (서정혜, 38세 여·수간호사)**: 162cm 마른 편, 어깨가 앞으로 말림, 단단한 광대·턱선의 야무진 얼굴, 옅은 다크서클·잔주름. 트고 갈라진 손. 어깨 안 닿는 단발을 뒤로 묶거나 실핀 고정(관자놀이 흰머리 몇 올). 흰 간호복 원피스+흰 카디건(겨울엔 위에 남색 가디건), 왼쪽 가슴 명찰. 좀처럼 안 웃는 차가운 인상.
- **SUNDEOK (박순덕, 58세 여·장례식장 염습 도우미)**: 154~156cm 작고 다부짐, 굵은 팔뚝, 살짝 굽은 등. 마디 굵고 손톱 짧은 손(겨울 튼 손등에 반창고, 오른손 엄지 아래 오래된 화상 흉터). 깊은 주름·검버섯, 처졌지만 바닥까지 보는 눈빛, 앞니 하나 없음. 희끗한 머리를 바짝 묶고 흰 무명 두건. 고무 앞치마+팔토시+검정 장화, 감색 몸뻬, 목 늘어난 회색 카디건, 목엔 무명 마스크.
- **JAEHO (윤재호, 29세 남·이사장 아들)**: ~180cm 잘 먹고 자란 체격, 매끈한 창백한 피부, 무스로 넘긴 부드러운 파마머리(90년대 부잣집 아들 스타일), 말끔히 면도한 둥근 듯 부드러운 턱, 턱을 치켜든 거만한 냉소. 낙타색/차콜 롱 울코트 안에 짙은 터틀넥, 금장 손목시계, 가죽장갑, 값비싼 가죽구두. 한 손을 주머니에 꽂은 오만한 자세.
- **TAESEOP (윤태섭, 60세 남·재단 이사장)**: ~170cm 다부지고 위압적인 풍채, 은회색 단정히 빗어넘긴 머리, 금테 안경, 깊고 권위적인 주름, 굳게 다문 입. 값비싼 차콜 더블브레스트 정장, 실크 넥타이, 금 넥타이핀, 두꺼운 오버코트. 차갑고 명령적인 존재감. 5층 이사장실 큰 책상 뒤.
- **MANBOK (오만복, 63세 남·전직 공단 노동자 노인)**: ~165cm 매우 야윈 앙상한 몸, 움푹 팬 광대·볼, 깊은 주름, 햇볕에 그은 거친 피부, 성긴 백발, 희끗한 수염. 겨울에 얇고 남루한 옷차림(빛바랜 낡은 점퍼, 해진 바지, 닳은 고무신). 굳은살 박이고 때 낀 노동자의 거친 손. 떨리고 쇠약함. **고인·시신 장면에선 얼굴 절대 안 보이게(흰 천 완전히 덮음).**

---

## 비트 시트 (B01~B13 · 장면 통합)

## B01 (S01~S03 · 대비: 빈 정류장 vs 특실의 특권)
Split-screen class-contrast composition, snowy night. On the left, cold desolate exterior: an empty snow-piled bus stop bench under a blizzard, a single wordless crumpled paper resting on the snowed-over seat where an old man once sat, cold blue desaturated light, deep quiet emptiness, no person. On the right, warm interior of a spacious 1997 VIP hospital suite: a well-dressed guest sleeps comfortably in a wide clean bed, kept only as a shadowed silhouette under a single warm lamp, identity fully hidden, heavy soft shadows, cozy amber light, an empty second bed nearby. Vertical seam between cold neglect and warm privilege, generous space on both halves for a Ken Burns pan from the frozen empty bench to the warm suite. Bitter irony, injustice, quiet indignation.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

## B02 (S04~S07 · 도현 각성·망설임)
Interior dim 1997 hospital on-call room at deep night, single desk lamp, handwritten charts and two wordless crumpled reprimand papers on the desk, an old rotary phone. DOHYEON (31, 178cm lean, angular jaw, thick eyebrows, monolid sharp eyes, heavy dark circles, faint stubble, yellowed white coat with ink and coffee stains, gray tee, stethoscope round neck) sits sleepless on the edge of a narrow bunk, elbows on knees, one hand gripping his hair, his white coat half slipped off one shoulder as if torn between keeping it and shedding it, staring at the crumpled papers with a conflicted anguished face. Cold blue night through a small window on one side, warm lamp on the other, pan room across the desk. Restrained inner conflict, moral hesitation, exhaustion.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

## B03 (S08~S09 · 순덕이 이름 전함·정혜 주저앉음)
Interior dim 1997 hospital corridor at night, old beige walls, flickering fluorescent light. SUNDEOK (58, small sturdy woman, deeply wrinkled face with age spots, drooping but piercing eyes, grey hair tied back under a white cotton kerchief, rubber apron, arm sleeves, thick-knuckled bandaged hands) stands gravely speaking low, one weathered hand gently extended. Before her JUNGHYE (38, 162cm thin, firm cheekbones and jaw, bob tied back with a few grey hairs at the temple, white nurse dress with navy cardigan, nameplate, chapped cracked hands) has just heard a name and her strength leaves her — leaning back against the wall and sliding down to sit on the floor, one trembling hand over her mouth, eyes wide and stricken, face draining with dawning sorrow. Two-figure staging with pan room between the standing old woman and the overwhelmed seated nurse, cold muted palette. Shock, grief surfacing, foreboding.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

## B04 (S10~S13 · 정혜의 비밀 간병·겁·되돌려보냄)
Interior 1997 internal-medicine ward at soft night, memory-tinged, old beige walls, handwritten charts, an iron bed frame. JUNGHYE (38, thin, firm jaw, bob tied back, white nurse dress with navy cardigan, nameplate, chapped cracked hands) tends MANBOK (63, very thin gaunt old man, hollow cheeks, sparse white hair and stubble, sitting up frail under a thin blanket) with quiet tender care, tucking the blanket and secretly slipping a handwritten chart (blank ruled lines, no legible text) out of sight behind her back to hide him from an audit — but her expression is torn and fearful, glancing anxiously over her shoulder at a looming stern shadow at the ward doorway. Warm bedside lamp against cold shadow at the door, pan room from the tender care to the fearful glance. Compassion turning to guilt and fear, tragic tenderness.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

## B05 (S14~S15 · 아들이 온다던 마지막 거짓말)
Interior 1997 ward bed at night, memory-tinged, dim warm lamp. MANBOK (63, very thin gaunt old man, hollow cheeks, deep wrinkles, sparse white hair and stubble, shabby, sitting propped weakly against a pillow under a thin blanket) wears a faint fragile hopeful smile, his trembling calloused hand gesturing gently toward the door as if telling someone a loved one is coming tomorrow. Beside the bed an empty wooden visitor's chair sits conspicuously vacant, no one there, an untouched space where a son should be. Soft warm bedside light fading into cold empty shadow around the empty chair, deep pan room from the old man's hopeful face to the empty chair. Heartbreaking hope, quiet loneliness, the ache of a lie told by someone who did not want to be alone at the end.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

## B06 (S16~S18 · 정혜 오열·아버지의 죽음이 겹침)
Interior dim quiet ward side room at night. JUNGHYE (38, thin, firm cheekbones, bob tied back with grey hairs at temple, white nurse dress with navy cardigan, nameplate, chapped cracked hands) has crumpled against the wall onto the floor, both hands pressed over her face, shoulders heaving in uncontrollable weeping, utterly broken with guilt. Behind her, a faint ghostly muted memory-vignette bleeds into the wall: a lonely elderly man (her late father, thin and frail, seen only from behind and in shadow, face turned away and not visible) sitting alone in a shabby dim home, abandoned. Cold desaturated palette, the memory rendered as a pale washed overlay, pan room from the weeping nurse to the faded memory. Devastating grief, self-blame, tragic parallel.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

## B07 (S19~S21 · 도현·정혜 서랍 파고듦)
Interior dim 1997 hospital admissions office at deep night, empty and quiet, old beige counter, handwritten ledgers, an old rotary phone, a desk with drawers. DOHYEON (31, lean, yellowed white coat, stethoscope, dark circles, tense focused) crouches pulling open a wooden desk drawer, while JUNGHYE (38, thin, bob tied back, white nurse dress with navy cardigan, nameplate) leans in beside him holding a small flashlight beam, both peering intently into the drawer with wary investigative expressions, glancing toward the dark doorway for anyone watching. Single desk lamp glow in surrounding darkness, pan room across the desk to the drawer. Secretive tension, discovery, suspense.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

## B08 (S22~S23 · 두 개의 장부·가짜)
Interior a dim 1997 office at night, a single desk lamp glowing. On a worn wooden desk lie two open old-fashioned handwritten account books side by side, both showing only blank ruled grid lines with no legible text or numbers anywhere, one book newer and cleaner, the other worn and older, clearly mismatched. DOHYEON (31, yellowed white coat, glasses, tired eyes) and JUNGHYE (38, nurse dress, navy cardigan, chapped hands) stand leaning over the desk together, studying and comparing the two books with tense concern, one finger pointing between them. Cold lamp light, deep shadow around the edges, slight pan room from one book to the other, tense quiet.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

## B09 (S24~S25 · 태섭의 횡령·환자를 짜낸 규칙)
Interior the imposing 1997 fifth-floor chairman's office, night, wood-paneled walls, heavy curtains, a large executive desk, old rotary phone. TAESEOP (60, stout authoritative imposing build, silver-grey combed-back hair, gold-rimmed glasses, deep stern wrinkles, charcoal double-breasted suit, silk tie with gold clip) stands alone behind the big desk, coldly and greedily gathering thick bundles of old cash into an open drawer, a small satisfied cold curl to his hard mouth, dominating the room. In the cold shadowed foreground, faint faceless silhouettes of frail powerless patients recede into darkness, drained. Single dominant powerful old chairman, no other named figure. Cold institutional light, pan room from the money to his cold face. Corrupt greed, cold heartlessness, menace.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

## B10 (S26~S27 · 만수의 어두운 얼굴·떨리는 손)
Interior dim quiet basement preparation room of the 1997 hospital, cold concrete walls, a single bare bulb, a steel table, faint incense haze. MANSU (52, forward-rolled obsequious shoulders, gaunt angular cheekbones, heavy eye bags, barcode comb-over, thick horn-rimmed glasses, worn shiny gray suit, yellowed shirt collar, thick short tie knot) stands alone before the steel table where a still figure lies entirely covered head to toe by a clean white cloth (the face, head and whole body fully concealed under the white sheet, NOT visible at all), his usually cold face now dark, shaken and haunted, both hands visibly trembling as he looks down, unable to steady them, a crack of buried guilt breaking through. Tight composition on Mansu and the sheet-covered form only, the covered figure's head extends beyond the top edge of frame and is not shown, no face anywhere in frame. Cold underground blue light, pan room from his trembling hands up to his troubled face. Buried remorse surfacing, foreboding.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

## B11 (S28~S29 · 순덕이 만수를 부름·18년 된 종이)
Interior dim basement preparation room, cold concrete walls, single bare bulb, steel table, faint incense haze. SUNDEOK (58, small sturdy woman, deeply wrinkled face with age spots, drooping but piercing unwavering eyes, grey hair under a white cotton kerchief, rubber apron, arm sleeves, black rubber boots, thick-knuckled bandaged hands with an old burn scar) stands firm on one side, quietly and gravely summoning MANSU forward, holding out an old yellowed carefully-folded wordless paper worn soft with eighteen years of age. MANSU (52, barcode comb-over, thick horn-rimmed glasses, worn gray suit, yellowed collar) steps hesitantly toward her, uneasy and wary. Two figures across the dim room with the aged folded paper between them, pan room from the old paper to Mansu's face. Cold underground light, solemn confrontation, mounting dread.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

## B12 (S30~S33 · 두 쪽지 나란히·똑같은 글씨·만수 굳음)
Interior dim basement preparation room, steel table under a single bare bulb. On the cold steel table two wordless papers lie placed side by side — one a fresh crumpled note, the other an old soft yellowed eighteen-year-old note — both blank of legible text yet unmistakably matching in the same handwriting strokes and the same folded layout, laid parallel for comparison. SUNDEOK's weathered bandaged hand rests beside them, having just set them down. MANSU (52, forward-rolled shoulders, barcode comb-over, thick horn-rimmed glasses, worn gray suit, yellowed collar) stares down at the two papers, his face going utterly white and rigid with shock, eyes wide, lips parted, frozen in stricken recognition. Composition splits between the two matching papers and Mansu's whitened stunned face, pan room from the evidence to his reaction. Cold underground light, crushing revelation, suspense.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

## B13 (S34~S35 · cliffhanger · 18년 전 그 문 앞)
Interior dim basement doorway blending into a snowy memory, night. In the foreground MANSU (52, barcode comb-over, thick horn-rimmed glasses, worn gray suit, yellowed collar) stands utterly broken and hollow, shoulders sagging, staring down at the old yellowed wordless paper trembling in his hand, his face stricken and hollow. Behind and above him a pale faded memory-vignette bleeds through the wall: the exterior 1997 hospital entrance doorway in a heavy winter blizzard eighteen years ago, warm light spilling out onto cold blue snow, and at the threshold the faint shadowed outline of another figure being turned away at the door into the storm (seen only as a dim washed-out silhouette, face not visible, identity hidden). Cold-and-warm split, the memory rendered as a pale faded overlay, deep pan room from Mansu's stricken face into the faded doorway. Somber cliffhanger, unresolved mystery, ominous quiet.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no letters or numbers anywhere, wordless illustration.

---

**비트 요약**: 13 스틸(B01~B13, S01~S35 통합). 라인-비트 매핑 = _beat_map.json (35 라인 → 13 비트). 고인·시신은 전 컷 흰 천 완전 덮음(얼굴 프레임 밖), 특실 손님·18년 전 인물은 실루엣/정체 숨김. 태섭은 단독 노인 권력자로 명확화(다른 노인 동시등장 회피).
