---
name: synthesize-sayeon
description: CVDE 미달 저점수 사연 여러 건의 갈등 조각을 기승전결로 합성해 하나의 새 창작 사연으로 재창조·풀 제작 — 소스 4건 스크리닝→병렬 각색 3안→judge panel 완주율 심사→최종 대본→이미지(축소)→TTS→렌더→업로드 메타까지. produce-sayeon과 달리 사연 1건을 그대로 각색하지 않고 여러 미달 사연의 조각을 재배치한다. 사용자가 "저점수 사연 합성", "사연 재창조", "미달 사연 모아서 만들어줘", "합성 사연" 같은 표현 사용 시 호출. broken_lock(2026-07-02)에서 1차 검증. 후행=**게시(별도 게시 프로그램 또는 수동)**(3플랫폼 완전자동 게시; 실패 시에만 게시(수동) 폴백).
---

# /synthesize-sayeon — 저점수 사연 합성 재창조

## 언제 쓰나
CVDE 미달(대략 15~58점)이라 단독으로는 못 쓰지만, 베스트댓글을 보면 갈등 자체는 쓸만한 조각이
섞인 사연들이 있다. 그런 조각 4개를 기승전결에 하나씩 배치해 **완전히 새로운 사연**으로 재창조한다.
단일 사연 각색은 `/produce-sayeon`을 그대로 써라 — 이 스킬은 "여러 소스를 하나로 합성"할 때만.

## 1. 소스 4건 스크리닝
```sql
SELECT post_id, title, cvde_score, category, body, best_comments
FROM stories
WHERE cvde_score BETWEEN 15 AND 58 AND is_used=0
  AND category IN ('가족갈등','시댁갈등','부부갈등','이혼','육아갈등','금전갈등','직장갈등')
  AND best_comments != '[]' AND length(body) > 150
ORDER BY cvde_score DESC;
```
연예/정치는 노이즈(대부분 미달 사연이 여기 몰림) — 제외. 60건 정도 뽑아서 사람(감독)이 직접
4개를 고른다. **각 조각마다 "이 조각에서 뭘 가져올지" 한 줄로 명시**(그대로 베끼지 않고 재료로만
사용). 기(트랩/설정) · 승(심화) · 전(반전/폭로) · 결(사이다) 각 1개씩.

## 2. 병렬 각색 3안 → judge panel
[[role-shorts-director]] 패턴 그대로: 서브에이전트 3개에 같은 4조각 + **다른 구조 지시**(예:
정공법/콜드오픈+플래시백/냉소→통쾌)로 각색안(22~26줄 나레이션) 작성 위임 → 독립 judge 2인에게
**눈가림으로**(Draft 1/2/3, 서로 참고 금지) 6기준(첫3초훅·인과개연성·막장강도·사이다임팩트·
길이속도·TTS자연스러움) 1~5점 채점 시킴 → 최고안 채택 + 판정 근거로 지목된 베스트비트를 이식.

## 3. 소스간 디테일 충돌 검사 (★필수, 실패 사례 있음)
서로 다른 소스 원문의 디테일을 한 인물/장소로 합치면 **개연성 구멍**이 잘 생긴다(broken_lock:
"시댁 집으로 들어감"이라 써놓고 다른 소스의 "아파트 전단지 보고 새 집으로 이사"를 그대로
가져와 앞뒤가 안 맞았음 — 사용자가 지적한 후 발견). 최종 대본을 한 번 통독하며 **"이 디테일이
지금 설정(누구 집, 새 집인지 기존 집인지, 관계 등)과 모순되지 않는가"**를 체크할 것. 이미지
프롬프트에도 같은 모순이 들어가므로 대본에서 먼저 잡아야 한다.

## 4. 다운스트림 = produce-sayeon과 동일, 단 시각 정책만 변경
`00_meta.json`/`02_step3_narration.txt`/`08_image_prompts.md`/`_beat_map.json` 작성부터
fal 이미지·Fish TTS·`compose_narration.py --kenburns`·업로드 메타까지는 **produce-sayeon §2~5
그대로** — 자세한 건 그쪽 참조. 이 스킬이 다른 점은 딱 하나:

- **캐릭터 축소**: 주인공(화자) 1 + 가해자 1~3 (순수 부부갈등처럼 악역이 1명뿐인 합성도 정상 —
  가해자 수는 소재가 정하는 것이지 억지로 2명 이상 채울 필요 없음. 이미지 축소와 직결).
- **이미지 대폭 축소**: 표준 8~18장 대신 **6장 안팎**. `_beat_map.json`(키=**줄번호** 문자열,
  값=`[이미지번호]`)으로 나레이션 3~5줄을 이미지 1장에 묶는다. 컷당 홀드는 `compose_narration.py
  --kenburns`가 자동으로 늘려서 커버(2026-07 스크립트 수정 이후, 같은 비트/파일 연속 세그먼트를
  자동 병합해 줌이 라인 경계마다 리셋되지 않음 — 별도 조치 불필요, 이미 스크립트에 반영됨).
- ★순서 권장(2026-07-03 2차 검증으로 확정): **`08_image_prompts.md`+`_beat_map.json`을 먼저 쓰고
  그다음 `generate_narration_fish.py`를 딱 한 번 돌려라.** 이 스크립트는 `_beat_map.json`을
  **TTS 생성 시점에** 읽으므로, beat_map 없이 먼저 돌리면 조용히 1:1 기본 매핑으로 남아 나중에
  **반드시 재실행**해야 하는 낭비가 생긴다(1차 검증 broken_lock에서 실제로 겪음). 순서만 지키면
  이 함정 자체가 발생하지 않는다(2차 검증 lunch_ledger에서 확인 — beat_map 재작업 0회).
- ★길이 트리밍은 대본 확정 후가 아니라 **TTS 실측 후**에 하라. 대본 단계에서 "짧게 써야지"라고
  아무리 신경 써도 실제 Fish 낭독 속도는 라인마다 다르다(생성 후 실측이 진실,
  [[narration-pace-natural-over-gate]]). 90s 초과하면 중복/부연 라인부터 정리 → beat_map도
  라인 수 변경분(삭제된 라인 번호) 맞춰 재작성 필요.
- ★가짜글자 함정(2026-07-03 실증): 가계부·수첩·문서 같은 소품은 "no readable text" negative
  프롬프트를 걸어도 **FLUX가 표지에 가짜 한자/글자를 그려 넣는 경우가 있다**(lunch_ledger B03).
  negative로 우회하려 하지 말고 **소품 자체를 프롬프트에서 빼는 게 가장 확실한 수정**(빈손으로
  구도만 유지). 통장/폴더처럼 이미 검증된 닫힌-표지 오브젝트(broken_lock B05)는 괜찮았음 — 열린
  페이지나 표지에 라벨이 강조되는 소품일수록 위험도가 높다.
- 부재-역할 오탐 가드([[flux-ref-role-token-absent-trap]])가 **두 인물 다 있는 멀티 비트에서도**
  "ROLE 토큰 근처에 no-계열 문구"가 있으면 경고를 띄울 수 있다(lunch_ledger B04, 실제 감지는
  정확했음 — false positive). 걱정할 필요는 없지만 경고가 뜨면 dry-run 결과(`multi:` 태그)로
  실제 배역 감지가 맞았는지 먼저 확인할 것.

- **그림 경로 2가지** — `00_meta.image_backend`에 어느 쪽인지 적는다.
  - **fal(웹툰)**: 위 `08_image_prompts.md` → `generate_images_fal`.
  - **손그림(₩0, fal 불필요)**: `08_image_prompts.md`를 쓰지 않는다. production 폴더에
    `doodle_scenes.py`(`SCENES = {"B01": page(bg, body_svg), ...}`, `scripts/doodle_kit.py`의
    `person/arm/glyph/page` 사용)를 쓰고 `.venv/bin/python scripts/doodle_kit.py <slug>` →
    `flow_images/B##.png`. 인물·소품은 화면 위 2/3 안(하단은 자막). `_beat_map.json`·TTS 순서
    규칙은 동일. 예시 = `productions/<예시_production>/doodle_scenes.py`.
- **다음편 예고 줄**(`next_preview_lines: 1`의 마지막 줄): 다음 편 내용은 아직 정해지지 않았으므로
  **구체 소재를 지어내지 않는다**. 형태 = "다음에도 이런 이야기로 찾아올게요."처럼 소재가 없는
  일반 문구 한 줄.

## 5. 소스 마킹
합성에 쓴 4건 전부 `python scripts/pick_story.py --claim <post_id>` (재사용 방지, 4번 반복).

## 참조
- 다운스트림 전체·업로드 메타·게시 = `/produce-sayeon` 그대로
- 각색-judge 패턴 = [[role-shorts-director]] 메모리
- 검증 production: `productions/<예시_production>/`(1차, 시댁갈등) ·
  `productions/<예시_production>/`(2차, 부부갈등·이중잣대 — 스킬 문서만 보고 재현 성공,
  절차 자체는 실사용 검증 완료. 완주율 데이터는 아직 대기)
- 완주율 판정 후 스킬 유지/폐기 결정 (아직 데이터 대기)
