> 🔔 생성 지시(먼저 읽기): 프롬프트대로 이미지를 하나씩 순차 생성. 인물은 CHARACTER_GUIDE 외형을 매 컷 동일하게(레퍼런스 잠금). 영상은 지정된 참조 이미지(B##.png)를 첫 프레임으로 생성. 파일명은 비트명(B01, B02…)과 동일하게 저장.

# 08 IMAGE PROMPTS — 한성의료원 1997 · 1부 「그 밤, 한 사람이 쫓겨났다」

> 트랙: 인물-구동 롱폼 드라마(가상 인물). **얼굴 O + 캐릭터 일관성 필수**(사연 트랙의 "얼굴 금지" 미적용). 이미지 엔진 = fal.ai FLUX + kontext --ref 레퍼런스 잠금 전제.
> 비트: B01~B15 (**장면 단위 통합** — 1 비트가 여러 나레이션 라인을 받고 **켄번즈 줌·팬**으로 훑는다). 🎬 태그 = 모션 클립 지정(스틸을 첫 프레임으로 image-to-video → 08_clip_prompts.md).
> ⚙️ 통합: 기존 41비트(B01~B41) → 15 스틸로 병합. 라인-비트 매핑은 _beat_map.json 참조. 여러 라인을 받는 컷은 **구도에 여백**을 둬 켄번즈 팬에 여유를 준다.

---

## COMMON_BASE (모든 프롬프트 말미에 이미 포함됨 — 스타일 잠금)
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920

## NEGATIVE (모든 컷 공통 — 생성 시 negative로)
Storybook, any text, caption, title, letters, numbers, signage, brand logo, watermark, signature, modern technology, EMR monitor, flat-screen, smartphone, digital display, LED, western faces, deformed hands, extra fingers, extra limbs, fused fingers, blurry, lowres, jpeg artifacts, oversaturated

시대고증: 1997 지방 종합병원 — 수기 차트·형광등·낡은 미색 복도·연탄난로 겨울·삐삐/시티폰 과도기. **후대 기술(모니터·스마트폰·평판 디스플레이) 금지.** 독촉 쪽지·서류는 **글자 없는 구겨진 종이**로만 표현.

---

## CHARACTER_GUIDE (인물별 잠금 외형 — 매 컷 동일 유지)

- **DOHYEON (이도현, 31세 남·응급실 레지던트)**: 178cm 마른 체형, 각진 턱, 짙은 눈썹, 쌍꺼풀 없는 강한 인상, 짙은 다크서클, 이틀 지난 거뭇한 수염 자국, 충혈된 눈. 목깃·소매가 누렇게 전 흰 가운(왼쪽 가슴 볼펜 잉크+커피 얼룩), 회색 반팔 티, 구겨진 슬랙스, 목에 청진기. 지치고 고집스러운 소신파.
- **MANSU (강만수, 52세 남·원무과장)**: 168cm, 팔다리 가늘고 아랫배만 나온 중년형, 어깨가 앞으로 말린 굽신 실루엣. 광대 도드라진 각진 얼굴, 볼 패임, 짙은 눈밑, 벗어진 이마에 옆·뒤 머리를 넘긴 바코드 헤어. 소매 반질반질한 회색·감색 기성복 양복, 누런 와이셔츠 깃, 굵고 짧은 넥타이 매듭, 도수 높은 뿔테 안경. 냉혈해 보이는 사무적 표정.
- **JUNGHYE (서정혜, 38세 여·수간호사)**: 162cm 마른 편, 어깨가 앞으로 말림, 단단한 광대·턱선의 야무진 얼굴, 옅은 다크서클·잔주름. 트고 갈라진 손. 어깨 안 닿는 단발을 뒤로 묶거나 실핀 고정(관자놀이 흰머리 몇 올). 흰 간호복 원피스+흰 카디건(겨울엔 위에 남색 가디건), 왼쪽 가슴 명찰. 좀처럼 안 웃는 차가운 인상.
- **SUNDEOK (박순덕, 58세 여·장례식장 염습 도우미)**: 154~156cm 작고 다부짐, 굵은 팔뚝, 살짝 굽은 등. 마디 굵고 손톱 짧은 손(겨울 튼 손등에 반창고, 오른손 엄지 아래 오래된 화상 흉터). 깊은 주름·검버섯, 처졌지만 바닥까지 보는 눈빛, 앞니 하나 없음. 희끗한 머리를 바짝 묶고 흰 무명 두건. 고무 앞치마+팔토시+검정 장화, 감색 몸뻬, 목 늘어난 회색 카디건, 목엔 무명 마스크.
- **JAEHO (윤재호, 29세 남·이사장 아들)**: [신규 정의] ~180cm 잘 먹고 자란 체격, 매끈한 창백한 피부, 무스로 넘긴 부드러운 파마머리(90년대 부잣집 아들 스타일), 말끔히 면도한 둥근 듯 부드러운 턱, 턱을 치켜든 거만한 냉소. 낙타색/차콜 롱 울코트 안에 짙은 터틀넥, 금장 손목시계, 가죽장갑, 값비싼 가죽구두. 한 손을 주머니에 꽂은 오만한 자세.
- **TAESEOP (윤태섭, 60세 남·재단 이사장)**: [신규 정의] ~170cm 다부지고 위압적인 풍채, 은회색 단정히 빗어넘긴 머리, 금테 안경, 깊고 권위적인 주름, 굳게 다문 입. 값비싼 차콜 더블브레스트 정장, 실크 넥타이, 금 넥타이핀, 두꺼운 오버코트. 차갑고 명령적인 존재감. 5층 이사장실 큰 책상 뒤.
- **MANBOK (오만복, 63세 남·전직 공단 노동자 노인)**: [신규 정의] ~165cm 매우 야윈 앙상한 몸, 움푹 팬 광대·볼, 깊은 주름, 햇볕에 그은 거친 피부, 성긴 백발, 희끗한 수염. 겨울에 얇고 남루한 옷차림(빛바랜 낡은 점퍼, 해진 바지, 닳은 고무신). 굳은살 박이고 때 낀 노동자의 거친 손. 떨리고 쇠약함. 추위/사망 장면에선 입술이 파랗게 질림.

---

## 비트 시트 (B01~B15 · 장면 통합)

## B01 (cold-open · 정류장의 언 노인)
Exterior bus stop at snowy dawn, blizzard, cold-open. MANBOK (63, very thin gaunt old man, hollow cheeks, sparse white hair and stubble, faded shabby old padded jacket, threadbare trousers, worn rubber shoes, blue-tinged frozen lips) sits frozen and motionless on the bench, snow piling on his shoulders and lap, head slightly bowed. Empty deserted street, pale grey-blue winter light, heavy falling snow. Composition leaves generous empty space around and above the bench so a Ken Burns slow pan can drift from the wider street down onto the still figure. Somber, still, tragic, ominous.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B02 (언 손의 쪽지)
Extreme close-up of MANBOK's weathered calloused old hand (rough laborer's hand, grime under nails, pale cold skin, a dusting of snow on the knuckles) gently clutching a single wordless crumpled paper. Snowflakes settling on the fingers. Shallow depth, cold desaturated palette, sorrowful stillness. Slight negative space at edges for a gentle Ken Burns zoom onto the paper.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B03 (눈길 건너 병원 불빛 · 외경)
Wide desolate exterior at snowy night, blizzard: in the foreground MANBOK (63, thin gaunt old man, shabby thin padded jacket, snow-dusted, hunched and still, small on the bus stop bench) faces away; across the snow-swept street far behind him rises the 1997 four-story regional hospital, a tall old concrete building with rows of warm fluorescent windows glowing, faded worn facade, bare winter trees, coal-brazier haze. No signage. Wide framing with deep empty snowfield between the old man and the distant warm building so a Ken Burns push can travel from the frozen figure across the snow toward the unreachable hospital lights. Cold blue night, single point of warm light distant, tragic and indignant undertone.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B04 (야간 응급실 아수라장 · 도현 당직)
Interior busy 1997 emergency room at night, extremely crowded and hectic: gurneys, IV poles, curtained bays, harsh fluorescent light, hurried staff spread across a wide floor. DOHYEON (31, 178cm lean, angular jaw, thick eyebrows, monolid sharp eyes, dark circles, faint stubble, yellowed white coat with ink and coffee stains on left chest, gray tee, stethoscope round neck) stands mid-frame amid the chaos, exhausted but sharp, sleeves pushed up. Wide layered composition with room on both sides for a Ken Burns pan across the crowded ER. Cold clinical light, tense energy.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B05 (재호의 새치기 · 거만한 지시)
Interior ER entrance, night. JAEHO (29, ~180cm well-fed, slicked soft permed hair, clean-shaven arrogant sneering face, chin raised, camel long wool overcoat over dark turtleneck, gold wristwatch, leather gloves, one hand in coat pocket) strides in imperiously leading a well-dressed guest behind him, his other arm pointing commandingly toward a treatment room, mouth open giving an entitled order. A cowed nurse and turning staff around him. DOHYEON (yellowed white coat, stethoscope, dark circles) visible in background looking on. Low angle emphasizing Jaeho's dominance, cold fluorescent light. Framing keeps space toward the treatment room he points at, for a Ken Burns move following his gesture. Arrogant intrusion, restrained tension, indignant undertone.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B06 (처치실·간호사 손님에게 · 도현 밀려남)
Interior ER, night. The single treatment room, the equipment cart and two nurses all diverted toward JAEHO's well-dressed guest being ushered into the best bay; DOHYEON (31, yellowed white coat, stethoscope, dark circles) pushed to the side of frame, sidelined and frustrated, empty-handed. Wide composition contrasting the crowded VIP bay on one side with the isolated doctor on the other, leaving pan room between them. Cold clinical light, sense of resources drained away from where they are needed. Restrained anger.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B07 (오만복 쓰러짐 · 애원)
Interior ER floor, night. MANBOK (63, very thin gaunt old man, hollow cheeks, sparse white hair and stubble, shabby thin padded jacket, worn shoes, blue-tinged lips, trembling) has sunk weakly to his knees on the cold linoleum floor, one frail hand pressed to his chest, the other trembling calloused hand reaching weakly upward, tears in his eyes, mouth open pleading desperately. Bystanders looking on helplessly. Low angle near floor level. Pale cold floor. Framing leaves headroom above his reaching hand for a Ken Burns rise. Harsh fluorescent light, shocking, urgent, heart-wrenching, tragic.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B08 (재호 저지 · 경멸 "치워" · 도현 붙들림)
Interior ER, night. DOHYEON (31, lean, yellowed white coat, stethoscope, dark circles, urgent straining expression) reaching toward the unwell kneeling old man but held back by the arm by JAEHO's well-dressed VIP guest, unable to move forward. JAEHO (29, slicked permed hair, clean-shaven, camel wool overcoat over dark turtleneck, gold watch, leather gloves) steps in front to block the path, chin raised, lip curled in a cold disdainful expression, glancing down dismissively at the kneeling MANBOK, his gloved hand making a small dismissive shooing wave. Three-figure staging (blocked doctor, sneering Jaeho, fallen old man) spread across the frame with pan room. Cold fluorescent light, class-contempt villainy, confrontational, suppressed fury.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B09 (접수처 만수 · 쪽지 쥐여줌 · 과거 그림자)
Interior 1997 hospital admissions desk, night, harsh fluorescent light. MANSU (52, forward-rolled obsequious shoulders, gaunt angular cheekbones, heavy eye bags, barcode comb-over, thick horn-rimmed glasses, worn shiny gray suit, yellowed shirt collar, thick short tie knot) seated behind the beige counter, eyes down on a handwritten ledger (blank ruled lines, no legible text), deliberately not making eye contact, mechanically pressing a wordless crumpled paper into the trembling calloused hand of MANBOK (63, gaunt old man, shabby thin jacket, blue-tinged lips) reaching over the counter — his own face blank and turned slightly away, like a machine, yet a faint flicker of buried ominous memory tightening his brow. Wide counter composition with space on both sides for a Ken Burns pan from the two meeting hands up to Mansu's haunted face. Cold light, muted palette, bureaucratic and mechanical cruelty, foreboding.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B10 (정혜 병동 · 떨리는 손, 수화기)
Interior 1997 third-floor internal-medicine ward nurses' station at night, old beige corridor, handwritten charts, an old rotary desk telephone. JUNGHYE (38, 162cm thin, firm cheekbones and jaw, bob tied back with a few grey hairs at the temple, white nurse dress with navy cardigan, nameplate, chapped cracked hands, wedding ring) standing at the station, head slightly bowed and shoulders drawn in, cowed and troubled as if just reprimanded — a stern authority figure's shadow looming at the edge of frame; she holds the old telephone receiver near her ear with a face torn by guilt and conflict, her chapped hand visibly trembling as it hovers over the cradle. Composition includes both the looming shadow and the phone with pan room between them, dim ward night light, muted cold palette. Anguished, restrained sorrow, guilt made physical.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B11 (경비 축출 · 병원 돌아봄 · 정류장 동사)
Exterior hospital entrance to snowy street, night blizzard, sequential-feeling wide composition. A uniformed security guard's hands shove MANBOK (63, frail gaunt old man, shabby thin snow-dusted jacket, blue-tinged frozen lips, clutching a wordless crumpled paper in one fist) out through the doorway into the driving snowstorm; warm light spills from the doorway behind while cold blue snow lies ahead. The old man stumbles forward, then turns his head back over his shoulder to look longingly at the warm-lit hospital windows, hope and fear in his eyes, before the far side of the frame shows the empty bus stop bench where he will sit and freeze. Wide deep-space framing with the doorway on one side and the distant bench on the other, generous snowfield between them for a long Ken Burns pan from expulsion to the freezing bench. Cruel, indignant, heartbreaking, desolate.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B12 (청소부 발견 · 병원의 은폐 · 태섭 "조용히 해")
Interior the imposing 1997 fifth-floor chairman's office at morning, wood-paneled walls, a large executive desk, heavy curtains, old rotary phone on the desk. TAESEOP (60, stout authoritative imposing build, silver-grey combed-back hair, gold-rimmed glasses, deep stern wrinkles, charcoal double-breasted suit, silk tie with gold clip) stands behind the big desk delivering a cold suppressing command, hard closed mouth, one sharp downward hand gesture, dominating the room, while two or three younger hushed white-coated staff stand before him with bowed heads, complicit and afraid in a cover-up. Single dominant authoritative old man clearly the powerful chairman; the others are clearly younger subordinates. Wide framing with pan room toward Taeseop. Cold institutional light, grim, menacing, corrupt authority.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B13 (지하 영안실 순덕 · 바늘자국 없음 · 쪽지)
Interior dim quiet basement preparation room of the 1997 hospital, cold concrete walls, a single bare bulb, a steel table, faint incense haze. SUNDEOK (58, small sturdy woman, deeply wrinkled face with age spots, drooping but piercing eyes, grey hair tied back under a white cotton kerchief, rubber apron, arm sleeves, black rubber boots, thick-knuckled bandaged hands) tends a still figure respectfully covered head to toe by a clean white cloth on the steel table, with twenty years of careful ritual: the figure's face, head and whole body are entirely concealed under the white sheet (the face NOT visible at all, fully covered), and only one thin pale elderly forearm extends out from under the cloth — the skin utterly pristine and smooth, completely unmarked, without a single mark from any care — her drooping eyes narrowing in ominous realization; in her other hand she holds a single wordless crumpled paper she has carefully unfolded. Tight waist-up composition on Sundeok, the exposed forearm and the crumpled paper only; the covered figure's head and upper body extend beyond the top edge of the frame and are NOT shown — only the sheet-covered torso and the single bare forearm are visible, no face anywhere in frame. Ken Burns move from the evidence to her expression. Cold underground blue light, solemn, foreboding, quiet mystery.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B14 (순덕이 도현 부름 · 쪽지 보임 · 도현 질림)
Interior dim basement preparation room. SUNDEOK (58, deeply wrinkled face, drooping but unwavering piercing eyes, white cotton kerchief, rubber apron, arm sleeves) stands firm across the steel table, one hand resting protectively on the white-cloth-covered figure between them, the other holding out the wordless crumpled paper, looking DOHYEON straight in the eye with quiet iron conviction. DOHYEON (31, yellowed white coat, stethoscope, angular jaw, stubble, dark circles) stands over the steel table looking down at a still form entirely covered by a clean white sheet (the head and face fully hidden under the cloth, NOT shown at all), only one pale bare elderly hand resting exposed at the edge of the sheet — and in this moment realizing, with dawning horror, that this is the very old man he had turned away in the ER — his own face draining of color, going pale and stricken, eyes widening, one trembling hand half-raised, utterly broken. Two living figures across the white-sheet-covered form with pan room between Sundeok's outheld paper and Dohyeon's devastated face; the covered figure's face and head stay fully hidden under the white sheet, no still face visible anywhere. Cold underground light carving the shock, crushing realization, grief and self-reckoning.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

## B15 (도현 얼굴 · cliffhanger 여운)
Interior dim empty ER corridor at night, after everything. DOHYEON (31, yellowed white coat, stethoscope, exhausted stubbled face, haunted) standing alone at a crossroads in the corridor, torn — on one side the warm glow of a curtained 1997 VIP room where an unseen figure lies (only a shadowed silhouette and a hand resting on the blanket visible, identity hidden, a single warm lamp and heavy shadows), on the other the cold dark direction of the entrance where the old man was turned away. He looks between them, conflicted and haunted. Cold-and-warm split lighting with deep space toward the shadowed VIP bed, pan room to drift from his face toward the hidden silhouette. Contemplative moral weight, foreboding cliffhanger, mysterious unresolved tension.
Korean Webtoon Illustration, clean flat cel-shaded, soft pastel watercolor, cinematic winter mood, 9:16 vertical 1080x1920. no text, no caption, no title, no letters or numbers anywhere, wordless illustration.

---

**비트 요약**: 15 스틸(B01~B15, 41라인 통합) / 🎬 클립 지정 6개 (B01·B05·B07·B08·B11·B14) → 08_clip_prompts.md 참조. 라인-비트 매핑 = _beat_map.json (41 라인 → 15 비트).
