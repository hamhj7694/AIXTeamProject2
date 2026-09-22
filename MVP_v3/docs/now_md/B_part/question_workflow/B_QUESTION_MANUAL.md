# B Part — CSR 확인 질문 매뉴얼

작성일: 2026-09-21
상태: **IN_PROGRESS / 최종 검토 대기**

## 1. 목적과 적용 범위

이 문서는 CSR에서 고객에게 무엇을 확인할지, 같은 Target을 언제 생략하거나 보완할지를 정한다. 질문 문장 목록이나 금융회사 내부 상담 절차가 아니다.

아래 기준은 금융위원회·금융감독원, 경찰청, KISA의 공개된 보이스피싱 예방·피해 대응자료를 참고한 **CSR 확인 기준**이다. 자료는 실제 송금·이체, 개인정보·금융정보 제공, 악성앱·원격제어, 기관 사칭, 자금 요구 명목, 전화·메신저 등 복수 접촉수단을 위험·대응 맥락으로 다룬다. 이를 질문 순서의 공식 규정이나 개별 금융회사의 공식 업무 절차로 해석하지 않는다.

| 참고 범위 | 확인한 공개 자료 |
| --- | --- |
| 금융위·금감원 | [악성앱·개인정보·송금 피해 예방 안내](https://www.fsc.go.kr/po010106/74163?curPage=181&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=), [개인정보·금융정보 요구와 악성앱 피해 소비자경보](https://www.fsc.go.kr/po010103/84947?curPage=3&srchBeginDt=&srchCtgry=&srchEndDt=&srchKey=&srchText=) |
| 경찰청 | [공공기관·금융기관 사칭, 대출·예탁금·공탁금 명목 사례](https://www.police.go.kr/user/bbs/BD_selectBbs.do?q_bbsCode=1007&q_bbscttSn=20230831175858950) |
| KISA | [행정기관 사칭, 원격제어 앱 설치, 전화·카카오톡 결합 사례](https://www.kisa.or.kr/402/form?page=1&postSeq=2588) |

## 2. 공통 원칙

- `ANSWERED != SUFFICIENT`: 답변 저장은 lifecycle 완료일 뿐, 답변의 명확성·근거 수준을 뜻하지 않는다.
- `CUSTOMER_STATEMENT != VERIFIED`, `PROPOSED != CONFIRMED`, `UNKNOWN != FALSE`를 유지한다.
- `CLEAR_CUSTOMER_STATEMENT`는 같은 기본 질문의 재질문을 생략할 근거가 될 수 있지만 `VERIFIED`는 아니다. `STAFF_CONFIRMED`도 별도 Verification 없이 `VERIFIED`로 승격하지 않는다.
- `PROPOSED` Fact, AI 추출값, Case의 값만으로 고객 질문을 생략하지 않는다. source·status와 Target 연결을 확인한다.
- 추천 질문은 담당자가 검토·수정·선택한 뒤에만 고객에게 전달한다. 현 등록 API는 첫 `PENDING`을 즉시 `ASKED`로 전환하므로, 자동 준비 기능에서 이를 곧바로 호출하면 안 된다.
- 현재 추천 경로는 diagnosis, 질문·답변, Fact, Verification, Action 중심이다. `QUESTION_PLAN`은 최근 MESSAGE와 검색 결과도 사용하지만 STT 원문·별도 FDS 입력이 직접 연결됐다고 가정하지 않는다.
- 단계와 매뉴얼 세부항목은 현재 DB 컬럼이나 enum이 아니다. 이번 문서는 코드·Contract·DB·migration을 바꾸지 않는다.

## 3. 현재 Target 대응

`manual_target`은 가능한 한 현재 AI `TargetField`와 동일한 값을 쓴다. `target_field`는 저장값이며 `qf1:<scope>:<parent_question_id>`의 canonical scope는 `canonical_question_scope()`로 읽는다. 의미가 비슷해도 코드 alias로 확정하지 않는다.

| manual_target | 고정 후보 `target_field` | AI `TargetField` / 기본 질문 | 대응 |
| --- | --- | --- | --- |
| `transfer_status` | `victim_transfer_status` | `transfer_status` | 명시적 별칭으로 정규화됨. |
| `authentication_information_exposure` | 동일 | 동일 | 직접 대응. `credential_exposure`는 별칭 아님. |
| `personal_information_exposure` | 동일 | 동일 | 직접 대응. |
| `remote_control_app` | 동일 | enum 있음, AI 기본 질문 사양 없음 | 직접 대응. 앱 설치 요구와 실제 설치의 의미는 분리 필요. |
| `transfer_purpose` | 없음 | 동일 | AI 기본 질문만 있음. |
| `claimed_organization` | `impersonated_institution` | `claimed_organization` | 의미상 관련되지만 alias 아님. |
| `incident_claim` | 없음 | 동일 | AI 기본 질문만 있음. |

고정 후보는 5개, AI 기본 질문 사양은 6개, AI `TargetField` enum은 7개다. 현재 명시적 별칭은 `victim_transfer_status → transfer_status`뿐이다.

## 4. 확정된 4단계

단계는 추천·검토 순서의 기준이다. 현 `customer_questions`에는 단계·category 저장 필드가 없으며 단계별 자동 실행도 구현되지 않았다.

| 단계 | 확인 범위 | 현재 Target과의 관계 |
| --- | --- | --- |
| 1단계 — 즉시 피해 확대 여부 확인 | 실제 송금, 인증정보 제공, 개인정보 제공, 원격제어/앱 설치 관련, 현재 접촉 지속 여부(조건부) | `transfer_status`, `authentication_information_exposure`, `personal_information_exposure`, `remote_control_app`; `ongoing_contact`은 UNMAPPED 후보 |
| 2단계 — 피해 범위와 행동 구체화 | 송금 세부사항, 개인정보·인증정보 노출 범위, 앱·기기 세부사항, 송금 명목 | 기존 1단계 Target의 보완 정보와 `transfer_purpose`. 새 기본 enum/DB Target을 만들지 않는다. |
| 3단계 — 사칭·접촉·사건 맥락 확인 | 상대방 소속·사칭, 주장한 사건·문제, 접촉 방식, 확인 가능한 기록, 기타 맥락 | `claimed_organization`, `incident_claim`; 접촉 방식·Evidence는 UNMAPPED 후보 |
| 4단계 — Verification 및 후속 확인 | 불확실 답변 보완, `qf1`, 상충 정보, 기존 Verification 결과 | 새 기본 질문 Target 단계가 아니다. 앞 단계의 scope와 기존 Verification 구조를 사용한다. |

P0/P1은 현재 코드에 있는 우선순위다. 1단계의 P0 질문을 먼저 검토하되, Case 근거와 활성 질문 상태를 무시하고 고정 개수를 채우지 않는다.

## 5. 의미 상태와 재질문

`QuestionStateEvaluator`는 같은 semantic scope에 이미 연결된 질문·답변·Fact·Verification을 평가한다. 원문 전체에서 Target을 자동 추출하지 않는다.

| 상태 | 기본 질문 | 후속 확인 |
| --- | --- | --- |
| `UNRESOLVED` | 활성 질문과 충분한 근거가 없으면 후보가 된다. | 기본 질문을 담당자가 검토한다. |
| `WAITING` | `PENDING`/`ASKED` 답변 대기이므로 재추천하지 않는다. | 기존 질문의 답을 기다린다. |
| `UNCERTAIN` | 불확실 답은 충분하지 않지만 동일 기본 질문을 반복하지 않는다. | 근거 확인형 보완을 검토한다. |
| `CLEAR_CUSTOMER_STATEMENT` | 명확한 고객 진술이면 재질문을 생략할 수 있다. | 검증 필요 여부는 별도 판단한다. |
| `STAFF_CONFIRMED` | 근거와 함께 담당자가 확인한 Fact면 기본 질문을 생략할 수 있다. | `VERIFIED`로 자동 승격하지 않는다. |
| `VERIFIED` | scope가 연결된 완료 Verification과 결과가 있으면 생략할 수 있다. | 검증 범위 밖 정보는 별도 검토한다. |
| `CONFLICT` | 해결된 사실로 취급하지 않는다. | 상충 근거를 확인한다. |
| `SKIPPED` | 즉시 재추천하지 않는다. | 생략 이유와 재개 필요성을 담당자가 검토한다. |

현재 evaluator는 scope에 연결된 비어 있지 않은 답을 `CLEAR_CUSTOMER_STATEMENT`로 본다. `모르겠어요` 등은 `UNCERTAIN`이고, 모호한 자유입력은 자동으로 충분하다고 가정하지 않는다. 실제 `qf1` 등록은 답변된 기본 parent, 동일 scope, 활성·중복 질문 없음 등의 구조 조건을 통과해야 한다.

## 6. Target별 기준

카드의 “관련 공식 근거”는 공개 대응자료가 해당 위험·수법을 다룬다는 뜻이다. 해당 Target을 반드시 질문해야 한다는 공식 절차를 뜻하지 않는다.

### `transfer_status`

- **현재 target_field 대응:** `victim_transfer_status`(정규화 시 `transfer_status`), `transfer_status`.
- **단계 / 우선순위:** 1단계 / P0.
- **확인 목적:** 실제 송금·이체가 있었는지와 상대방의 요구를 구분한다. 금액·횟수·거래 증빙은 2단계에서 구체화한다.
- **ask_when:** 실제 수행 여부에 대한 충분한 scope 연결 근거가 없고 활성 질문도 없을 때.
- **skip_when:** source와 status를 확인한 `CLEAR_CUSTOMER_STATEMENT`, `STAFF_CONFIRMED`, `VERIFIED`가 있을 때만 고려한다. Case 값이 `YES`/`NO`이거나 `PROPOSED`/AI 추출값이라는 이유만으로 생략하지 않는다. `WAITING`이면 보류한다.
- **sufficient_answer:** “실제로 송금했다/하지 않았다”처럼 수행 여부가 분명한 고객 진술은 재질문 억제 근거다. “송금하라고 했다”는 실제 수행의 답이 아니다.
- **기본 질문 예시:** “상대방의 요구대로 실제로 송금하거나 이체하셨나요?”
- **follow_up:** `UNCERTAIN`이면 거래내역·거래 알림의 확인 가능 여부를 묻는 보완을 담당자가 검토한다. 금전 행동을 지시하지 않는다.
- **관련 공식 근거:** 공개자료의 송금·이체 피해 및 피해 발생 시 대응 맥락.

### `authentication_information_exposure`

- **현재 target_field 대응:** 고정 후보·AI `TargetField`와 동일.
- **단계 / 우선순위:** 1단계 / P0.
- **확인 목적:** 인증번호·비밀번호·OTP 등의 제공 여부를 확인한다. 실제 값은 수집하지 않는다.
- **ask_when / skip_when:** 제공 여부가 미확인이고 활성 질문이 없으면 묻는다. 명확한 고객 진술, 직원 확인 Fact, scope 연결 Verification이 있으면 생략을 검토하며 `WAITING`이면 기다린다.
- **sufficient_answer:** 제공/미제공과 대상 범위가 구분되는 진술. 요구받았다는 사실은 제공했다는 사실이 아니다.
- **기본 질문 예시:** “인증번호, 비밀번호 또는 OTP를 제공하셨나요?”
- **follow_up:** `UNCERTAIN`이면 실제 값을 묻지 않고 읽어주거나 전송한 행동·기록의 확인 가능 여부를 검토한다.
- **관련 공식 근거:** 공개자료의 금융정보 요구·탈취 예방 맥락.

### `personal_information_exposure`

- **현재 target_field 대응:** 고정 후보·AI `TargetField`와 동일.
- **단계 / 우선순위:** 1단계 / P0. 제공 여부를 먼저 확인하고 범위는 2단계에서 구체화한다.
- **확인 목적:** 개인정보·신분증 정보의 제공 여부를 확인한다. 실제 주민등록번호·계좌번호 등 값은 수집하지 않는다.
- **ask_when / skip_when:** 제공 여부가 미확인이고 활성 질문이 없으면 묻는다. 명확한 제공/미제공 진술, 직원 확인 Fact, scope 연결 Verification이 있으면 생략을 검토한다.
- **sufficient_answer:** 제공 여부가 명확한 진술. “일부 제공”은 제공 여부에는 충분할 수 있으나 정보 종류·노출 범위에는 2단계 보완이 필요하다.
- **기본 질문 예시:** “주민등록번호나 계좌번호 등 개인정보를 제공하셨나요?”
- **follow_up:** 불확실 답변 또는 일부 제공이면 실제 값을 재수집하지 않고 당시 전달 행동·기록, 노출 범위를 확인할 필요를 담당자가 검토한다. 현 `qf1`은 `UNCERTAIN` 보완에 한정됨을 유지한다.
- **관련 공식 근거:** 공개자료의 신분증·개인정보 요구와 정보 유출 예방 맥락.

### `remote_control_app`

- **현재 target_field 대응:** 고정 후보·AI enum과 동일. AI 기본 질문 사양에는 없음.
- **단계 / 우선순위:** 1단계 / 현 고정 후보 P0. 실제 설치·기기 영향의 세부는 2단계에서 다룬다.
- **확인 목적:** “설치 요구 또는 안내를 받음”과 “실제로 설치함”을 별개의 사실로 다룬다. 현재 enum과 DB를 추가하지 않는다.
- **초기 구현 기준:** 현 `remote_control_app` scope 안에서 두 사실을 문서상 구분해 검토한다. 설치 요구를 받은 사실만으로 실제 설치 사실을 만들거나, 실제 설치 답으로 설치 요구 여부를 역추론하지 않는다.
- **ask_when / skip_when:** 묻고자 하는 사실이 미확인이고 활성 질문이 없을 때 묻는다. 설치 요구를 받은 사실만으로 실제 설치 질문을 생략하지 않으며, 반대도 같다.
- **sufficient_answer:** 질문이 대상으로 삼은 한 사실에 대한 명확한 진술. 현재 문장(설치 안내)과 선택지(설치함)의 의미가 달라 자동 충분성 판단에 쓰지 않는다.
- **기본 질문 예시:** 현 고정 문장 “휴대폰에 원격 제어 또는 화면 공유 앱을 설치하라는 안내를 받으셨나요?”
- **follow_up:** `UNCERTAIN`이면 설치 앱 목록·설치 기록을 확인할 수 있는지 묻는 보완을 검토한다. 앱 설치를 지시하지 않는다. 문장·선택지·사실 상태를 분리해 저장·추천하는 구현은 **추가 구현 검토 필요**다.
- **관련 공식 근거:** 공개자료의 악성앱·원격제어 앱 설치 요구와 실제 설치 피해 맥락.

### `transfer_purpose`

- **현재 target_field 대응:** AI `TargetField`만 있음.
- **단계 / 우선순위:** 2단계 / P1.
- **확인 목적:** 상대방이 제시한 송금·자금 이동 명목을 기록한다. 실제 송금 여부와 분리한다.
- **ask_when / skip_when:** 자금 요구는 있으나 명목이 미확인일 때 묻고, 명확한 주장 기록·확인 근거 또는 `WAITING`이면 생략·보류한다.
- **sufficient_answer:** 상대방이 든 이유를 다른 주장과 구별할 수 있는 진술. “돈을 보내라 했다”만으로는 명목이 충분하지 않다.
- **기본 질문 예시:** “상대방은 어떤 이유로 송금이나 자금 이동을 요구했나요?”
- **follow_up:** `UNCERTAIN`이면 대화·문자 기록에서 명목을 확인할 수 있는지 검토한다.
- **관련 공식 근거:** 공개 경찰 사례의 대출·예탁금·공탁금 등 자금 요구 명목.

### `claimed_organization`

- **현재 target_field 대응:** AI `claimed_organization`; 고정 후보의 `impersonated_institution`은 별도 문자열이며 alias가 아니다.
- **단계 / 우선순위:** 3단계 / P1.
- **확인 목적:** 상대방이 주장한 기관·회사 소속을 기록하고 Verification 대상을 정리한다. 실제 소속을 확정하지 않는다.
- **ask_when / skip_when:** 기관·회사 사칭 주장 신호가 있고 내용이 미확인일 때 묻는다. 같은 scope의 명확한 주장 기록·활성 질문이 있으면 생략·보류한다. `impersonated_institution`과 동일하거나 매우 유사한 사칭 대상 정보를 묻는 초안은 **conceptual duplicate**로 검토해 중복 추천하지 않는 것을 목표로 한다.
- **sufficient_answer:** 상대방이 말한 기관·회사명이 식별 가능한 고객 진술. 이는 기관의 실제 연락·검증 결과가 아니다.
- **기본 질문 예시:** “상대방은 어느 기관이나 회사 소속이라고 말했나요?”
- **follow_up:** 이름을 기억하지 못하면 메시지·통화 기록에서 주장 명칭을 확인할 수 있는지 검토한다. conceptual duplicate 판단은 코드 alias나 저장값 통합을 뜻하지 않으며, 실제 중복 제거 구현은 1번 작업에서 별도 검토한다.
- **관련 공식 근거:** 공개자료의 정부·금융기관·수사기관 사칭 사례.

### `incident_claim`

- **현재 target_field 대응:** AI `TargetField`만 있음.
- **단계 / 우선순위:** 3단계 / P1.
- **확인 목적:** 상대방이 주장한 사건·문제를 기록한다. 주장 내용을 실제 사건으로 확정하지 않는다.
- **ask_when / skip_when:** 사건·문제 주장 신호가 있고 내용이 미확인일 때 묻는다. 명확한 주장 기록이나 `WAITING`이면 생략·보류한다.
- **sufficient_answer:** 상대방이 주장한 사건·문제를 구별 가능한 수준으로 설명한 진술. 진위는 Verification으로 확인한다.
- **기본 질문 예시:** “상대방은 어떤 사건이나 문제가 발생했다고 말했나요?”
- **follow_up:** `UNCERTAIN`이면 대화·메시지 기록에서 주장 내용을 확인할 수 있는지 검토한다.
- **관련 공식 근거:** 공개자료의 계좌 연루 조사, 지원·대출 관련 사칭 등 사건·문제 주장 사례.

## 7. UNMAPPED 및 추가 검토

아래 UNMAPPED 항목은 매뉴얼상의 확인 후보로 유지한다. 다만 현재 `target_field`에 안전하게 대응되지 않으므로 1차 자동 추천 구현에서 직접 사용하지 않는다.

```text
UNMAPPED
→ 매뉴얼상 후보 유지
→ 자동 추천 직접 사용 금지
→ 별도 mapping / 설계 결정 후 연결
```

| manual_target 후보 | 단계 | 현재 상태 | 사용 원칙 |
| --- | --- | --- | --- |
| `ongoing_contact` | 1단계 조건부 | **UNMAPPED** | 현재도 상대방과 연락 중인지 확인하는 후보. 새 enum·DB Target으로 추가하지 않는다. 공개자료의 전화·메신저 결합 수법을 참고하되 필수 공식 질문으로 단정하지 않는다. |
| `credential_exposure` | 1·2단계 | **UNMAPPED** | `authentication_information_exposure`와 개념상 겹치며 새 alias로 확정하지 않는다. |
| `device_compromise` | 1·2단계 | **UNMAPPED** | `remote_control_app`는 앱 설치 관련 일부만 다룬다. 기기 침해 전체와 동일시하지 않는다. |
| `impersonated_entity` | 3단계 | **UNMAPPED** | 기관 외 인물·직책·가족·지인 사칭까지 포함할 수 있는 넓은 개념 후보. `claimed_organization`·`impersonated_institution`의 alias로 확정하지 않는다. |
| `contact_method` / `evidence_available` | 3단계 | **UNMAPPED** | 전화·문자·메신저 등 접촉 수단과 보유 기록 확인 후보. 기존 MESSAGE·첨부·Context를 쓸지 별도 검토한다. |
| `verification_outcome` | 4단계 | **고객 기본 질문 Target 아님** | UNMAPPED 자동 추천 후보가 아니며 기존 Verification 구조에서 관리한다. 고객 진술로 공식 검증 결과를 대체하지 않는다. |

4단계는 새 기본 질문을 추가하지 않는다. `UNCERTAIN` 답변의 근거 확인형 `qf1`, `CONFLICT`의 상충 근거 검토, scope가 연결된 기존 Verification 결과 검토를 담당자 검토 아래 처리한다. 동적 `qf1`은 자동 고객 전송 권한이 아니다.

## 8. 현재 구조에서 재사용할 지점과 남은 충돌

- 재사용: `TargetField`, `_QUESTION_SPECS`, `build_customer_question_candidates()`, `normalize_target_field()`, `canonical_question_scope()`, `QuestionStateEvaluator`, `question_policy`, 기존 질문 등록의 target·문장 중복 보호, `customer_questions`와 `case_facts`의 질문·근거 연결.
- 남은 의미 충돌: `remote_control_app`의 질문 문장은 설치 요구, 선택지는 실제 설치를 뜻한다. `claimed_organization`과 `impersonated_institution`은 현재 alias가 아니다. `victim_transfer_status`의 Case 값은 매뉴얼상 단독 skip 근거가 아니지만 현 후보 함수는 값이 `UNKNOWN`이 아니면 고정 후보를 제외한다.
- 매뉴얼의 단계·세부 범위·공개 근거 상태를 영속하는 DB 필드는 없다. 구현 단계에서 필요한 mapping·검증은 별도 결정하며, 이번 문서는 새 enum·DB 구조를 만들지 않는다.

이 문서는 최종 사용자 검토 전까지 `IN_PROGRESS`다. 코드, Contract, DB schema, migration의 변경 또는 구현 완료를 선언하지 않는다.
