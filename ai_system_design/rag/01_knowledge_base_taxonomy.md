# CONTEXT-FIRST CASE RAG Knowledge Base Taxonomy — STEP 1

## 1. STEP 1의 단일 목표

이 문서는 CONTEXT-FIRST CASE에서 후속 RAG가 **어떤 지식을 어떤 업무 맥락으로 조사·검색·해석해야 하는지**를 구분하는 Taxonomy 초안이다. 구현 명세나 운영 절차서는 아니다.

RAG의 역할은 보이스피싱 여부를 단독 판정하거나 거래를 실행하는 것이 아니다. 현재 Case의 Evidence, Structured Case Facts, Runtime Case State를 읽고, 부족한 외부 공식 지식이 필요한 때에만 검색 근거를 제공하여 담당자의 확인·설명·다음 업무를 지원한다.

## 2. 현재 설계의 전제

### 2.1 Chat 중심으로 바뀌는 서비스

MVP는 다수의 Page·Panel·Card 중심 구조에서 Chat 중심 인터페이스로 단순화 중이다. Chat 화면 구조, Chat Router 구현, Backend Chat API, Agent 호출 순서 및 특정 UI 구성은 아직 확정하지 않는다. Knowledge Base는 UI가 아니라 업무 목적, Case State, Structured Case Facts를 기준으로 독립 설계한다.

### 2.2 Agent 구분

현재 Runtime Agent는 `CaseSupportAgent`, `CustomerVerificationAgent`, `CaseUpdateAgent`, `AgentRouter`다. 이들은 명시적으로 역할을 나눈 facade이며 자율적으로 상호 대화하는 Autonomous Multi-Agent 구조가 아니다.

향후의 Bank Agent, Verification Agent, Case Orchestrator는 구현 완료 Agent가 아닌 개념 후보이다. Knowledge metadata는 현재·향후 Agent 클래스명에 고정 결합하지 않는다.

### 2.3 Structured Case Facts와 실제 상태

Structured Case Facts의 현 위치는 원본 Evidence에 연결된 `AI_EXTRACTED` 추출 제안이다. 추출되었다는 사실은 검증되었다는 뜻이 아니며 canonical Case truth로 취급하지 않는다.

예를 들어 “500만 원을 보내라 했지만 송금하지 않았다”는 다음 두 층을 동시에 가진다.

| 층 | 의미 |
|---|---|
| Structured Case Facts | 상대방의 500만 원 송금 요구(`BANK_TRANSFER`)가 있었다는 Evidence-linked AI extraction proposal |
| Customer Answer / Runtime | 고객이 실제 송금하지 않았다고 진술한 상태. 다만 고객 진술의 존재와 기관·시스템을 통해 외부적으로 검증된 사실은 동일하지 않음 |

따라서 `TRANSFER_REQUEST`와 `TRANSFER_COMPLETED`는 같지 않으며, 고객의 미송금 진술도 VERIFIED 사실과 같지 않다. 향후 Runtime State와 verification/confirmation status는 별도 경계에서 관리될 수 있으나, 이 문서에서 Contract나 Enum을 확정하지 않는다.

`APP_INSTALLATION_REQUEST`와 `APP_INSTALLED`, `CREDENTIAL_REQUEST`와 `CREDENTIAL_EXPOSURE`, `PERSONAL_INFORMATION_REQUEST`와 `PERSONAL_INFORMATION_EXPOSURE`도 같은 방식으로 분리한다.

본 문서에서 사용하는 claim, demand, pressure, isolation 등의 명칭은 RAG Taxonomy의 개념 축을 설명하기 위한 용어다. 이는 현재 Runtime StructuredCaseFacts의 실제 필드명과 1:1 Contract를 의미하지 않으며, 실제 구현 Contract의 Source of Truth는 현재 코드와 테스트를 기준으로 확인한다.

### 2.4 RAG 사용 경계

Case Evidence만으로 가능한 업무에는 RAG를 강제하지 않는다. 예: “현재 상담 내용을 정리해줘.” 반대로 사칭 주체의 실제 공식 절차, 지급정지·피해구제 절차, 기관 공식 확인 방법처럼 외부의 공식 지식이 필요한 요청은 RAG 후보이다.

## 3. Knowledge Base 전체 구조

| 영역 | 질문 | 역할 |
|---|---|---|
| Operational Knowledge | 지금 무엇을 확인하고 어떤 업무를 검토할까? | PREVENT/RECOVERY 모듈의 업무 지원 |
| Fraud Type Knowledge | 어떤 사칭·주장·요구 패턴인가? | 시나리오 분류와 추가 확인의 문맥 |
| Official Procedure / Verification Knowledge | 주장과 공식 절차가 일치하는가? | 기관·제도·공식 채널 확인 |
| Action / Exposure Signal Knowledge | 어떤 행동 요구·노출 상태에 어떤 공식 확인·대응 지식이 필요한가? | 현재 Case의 Request Signal 또는 Actual Runtime State를 조건으로 재사용 가능한 공식 확인·대응 지식을 제공 |
| Source / Governance | 이 내용은 어디서 왔고 지금도 유효한가? | 출처·최신성·용도 관리 |

Operational Knowledge는 PREVENT(P01~P06)와 RECOVERY(R01~R06)를 기본 모듈로 사용한다. Official Procedure Knowledge는 특정 모듈의 하위 Workflow가 아니라 여러 모듈에서 재사용 가능한 근거 지식으로 둔다.

## 4. PREVENT Taxonomy (P01~P06)

| Module | 목적 | 적용 Trigger / 상담 Knowledge 범위 | 관련 Facts / Runtime State | Knowledge Purpose | 중복·주의 및 STEP 2 검토 |
|---|---|---|---|---|---|
| P01 송금·이체 중단 및 추가 확인 | 추가 자금 이동을 막고 현재 거래 관련 사실을 확인 | 송금·현금·상품권·가상자산 이동 요구, 이체 시도·예정 | `demand_type`; 실제 `transaction_status` | PREVENTION_ACTION_SUPPORT, STAFF_DECISION_SUPPORT | 요구와 실제 송금을 합치지 않는다. P01의 상태별 업무 경계를 검토한다. |
| P02 사칭 주체·요구사항 진위 확인 | 상대방 주장과 공식 절차의 비교를 지원 | 기관·금융회사·가족 등 사칭, 확인 채널 요청 | `impersonated_entity`, `claim`, `demand`; 확인 결과 Runtime State | VERIFICATION_SUPPORT, CUSTOMER_EXPLANATION_SUPPORT | P03의 맥락 파악과 중복될 수 있다. 공식 확인 지식의 공통화가 필요하다. |
| P03 고객 상황·통화 맥락 확인 | 사건 맥락, 누락 정보, 압박·고립 신호를 정리 | 통화·메시지 내용, 불명확한 요구와 고객 상황 | claim, demand, pressure, isolation과 Evidence | CUSTOMER_QUESTION_SUPPORT, CASE_SUMMARY_SUPPORT(비RAG 가능) | 독립 모듈인지 공통 Case Context Layer인지 STEP 2에서 결정한다. |
| P04 추가 피해 행동 차단 | 앱 설치·원격제어·자격정보 제공 등 확산 가능 행동을 점검 | 위험 행동 요구 또는 의심 정황 | request signals; 실제 app/credential/PII exposure | PREVENTION_ACTION_SUPPORT | P01과 병렬 적용 가능하다. 행동 요구와 실제 노출을 혼동하지 않는다. |
| P05 고객 설득 및 안전 행동 안내 | 고객이 확인·중단·보존 행동을 이해하도록 지원 | 위험을 이해하지 못했거나 설명 근거가 필요한 경우 | Case facts, 미해결 질문, 확인된 공식 근거 | CUSTOMER_EXPLANATION_SUPPORT | 최종 금융 판단이나 자동 조치를 지시하는 지식으로 만들지 않는다. |
| P06 대응기관 확인 및 보호조치 연결 | 필요한 기관·보호조치 확인 업무로 연결 | 공식 기관 확인, 신고·보호 관련 정보가 필요한 경우 | 관련 기관, 실제 노출·거래 상태 | VERIFICATION_SUPPORT, STAFF_DECISION_SUPPORT | 범위가 지나치게 넓어질 위험이 있다. 기관 확인·신고·보호조치의 구분을 STEP 2에서 검토한다. |

## 5. RECOVERY Taxonomy (R01~R06)

| Module | 목적 | 적용 Trigger / 상담 Knowledge 범위 | 관련 Facts / Runtime State | Knowledge Purpose | 중복·주의 및 STEP 2 검토 |
|---|---|---|---|---|---|
| R01 지급정지 및 추가 자금이동 차단 | 이미 발생했거나 진행 중인 자금 손실의 확산을 줄일 업무 검토 | 실제 이체·출금·이동이 확인되었거나 의심됨 | `transaction_status`, amount, transfer context | RECOVERY_SUPPORT, STAFF_DECISION_SUPPORT | PREVENT와 완전한 반대편이 아니다. 이후에도 P01/P04가 동시에 필요할 수 있다. |
| R02 신고 및 사건 접수 | 공식 신고·접수 관련 확인을 지원 | 신고 필요성 또는 접수 방법 문의 | 사건 요약, 관련 Evidence, 접수 여부 Runtime State | RECOVERY_SUPPORT, CUSTOMER_EXPLANATION_SUPPORT | 실제 기관별 절차는 조사 후에만 확정한다. |
| R03 피해구제 제도 안내·요청 지원 | 적용 가능한 제도와 확인 필요 사항을 안내 | 금전 피해 또는 구제 관련 문의 | 거래 상태, 기관, 증빙 | RECOVERY_SUPPORT, VERIFICATION_SUPPORT | 제도의 요건·기한·효력은 공식자료 조사 전 고정하지 않는다. |
| R04 증거·기록 보존 | 추후 확인에 필요한 자료를 보존하도록 지원 | 통화·메시지·거래·앱 관련 기록 존재 | Evidence/provenance, 고객 보유 자료 | RECOVERY_SUPPORT | 발화 배열을 통화 시간으로 추정하지 않는다. |
| R05 계정·기기·금융보안 복구 | 실제 노출 이후 보안 복구 업무를 지원 | 앱 설치, 자격정보·개인정보 노출의 확인 또는 의심 | actual exposure states | RECOVERY_SUPPORT, PREVENTION_ACTION_SUPPORT | 단순 요청만으로 노출 완료로 처리하지 않는다. |
| R06 후속 모니터링 및 Case 관리 | 미해결 사실, 후속 확인, 상태 관리를 지원 | 사건이 종료되지 않았거나 확인 항목이 남음 | unresolved facts, Runtime Case State | STAFF_DECISION_SUPPORT, CASE_SUMMARY_SUPPORT | Case management의 DB/Workflow를 이 문서에서 정의하지 않는다. |

## 6. Fraud Type Taxonomy

`fraud_type` 하나에 모든 정보를 넣지 않는다. Primary Scenario는 큰 분류이고, 사칭·주장·요구·압박은 서로 독립적인 다중 축이다.

| 축 | 초기 후보 | 설계 원칙 |
|---|---|---|
| Primary Fraud Scenario | 수사기관 사칭, 금융감독·금융기관 사칭, 카드 배송·발급 사칭, 대출 빙자, 가족·지인 사칭, 납치·협박, 정책지원금·환급금 사칭, 기타, 미확정 | 한 Case의 모든 신호를 단일 enum으로 축소하지 않는다. |
| Impersonated Entity | `POLICE`, `PROSECUTION`, `FSS`, `BANK`, `CARD_COMPANY`, `GOVERNMENT`, `FAMILY`, `ACQUAINTANCE`, `OTHER`, `UNKNOWN` | 실제 기관인지가 아니라 상대방이 주장한 주체다. |
| Claim Type | 상대방이 발생했다고 주장하는 사건·사유 | 전체 enum은 공식 자료 조사 및 사례 검토 뒤 결정한다. |
| Demand Type | `BANK_TRANSFER`, `CASH_DELIVERY`, `APP_INSTALL`, `REMOTE_CONTROL`, `PERSONAL_INFORMATION`, `CREDENTIAL`, `OTP`, `GIFT_CARD`, `CRYPTO_TRANSFER`, `LINK_ACCESS`, `SECRECY`, `OTHER` | 복수 요구가 가능하므로 multi-value 후보로 검토한다. |
| Pressure / Isolation Signal | 긴급성, 공포, 권위, 처벌 위협, 타인 연락 차단, 비밀 유지, 통화 유지 강요 | 실제 공식자료 조사 전에는 고정적 특징이라고 단정하지 않는다. |

## 7. Structured Case Facts와 RAG 연결 원칙

1. AI extraction proposal은 RAG 필터의 입력 후보일 수 있으나, 검증 완료 사실이 아니다.
2. Chunk는 Evidence의 직접 대체물이 아니다. Case의 주장·요구·상태와 공식 지식을 함께 해석할 보조 근거다.
3. RAG 검색은 `Case Facts + 업무 목적 + 필요 시 Runtime State`를 사용한다. Runtime State를 Knowledge metadata로 복제하지 않는다.
4. 출처 없는 모델 추론으로 기관 연락처, 법적 의무, 금융 조치, 제도 적용 가능성을 확정하지 않는다.

## 8. Case State Taxonomy

Request State와 Actual State는 반드시 별도 축이다.

| 구분 | 예시 | 의미 |
|---|---|---|
| Request / Demand Signal | `BANK_TRANSFER`, `APP_INSTALLATION_REQUEST`, `CREDENTIAL_REQUEST` | 상대방이 요청·유도한 행위 |
| Actual / Exposure State | 거래 미확정·시도·완료, 앱 설치 여부, 인증정보·개인정보 노출 여부 | 고객에게 실제로 발생했거나 확인된 상태 |
| Knowledge applicability metadata | `applicable_transaction_status=[ATTEMPTED, COMPLETED]` | 해당 Chunk가 어떤 Runtime 상태에서 유용한지 |

`transaction_status`는 Runtime Case State이고, `money_transferred` boolean은 같은 사실을 중복·축약할 가능성이 높아 제거 후보로 둔다. 인증·개인정보 노출도 단순 boolean보다 `NONE_CONFIRMED`, `SUSPECTED`, `CONFIRMED`, `UNKNOWN`처럼 불확실성을 보존하는 enum이 필요한지 검토한다. 단, 본 STEP 1은 Runtime Contract를 확정하지 않는다.

## 9. Knowledge Purpose Taxonomy

아래 값은 초기 후보이며 확정 enum이 아니다.

| Purpose | 외부 RAG 필요성 | 중복 검토 |
|---|---|---|
| `CASE_SUMMARY_SUPPORT` | 대체로 낮음. Case Facts/Evidence만으로 가능한 경우가 많음 | 항상 RAG 대상이 되면 안 된다. |
| `CUSTOMER_QUESTION_SUPPORT` | 상황에 따라 다름 | 질문 자체보다 외부 확인이 필요한 질문인지 분리한다. |
| `VERIFICATION_SUPPORT` | 높음 | Official Procedure Knowledge와 밀접하다. |
| `PREVENTION_ACTION_SUPPORT` | 상황에 따라 다름 | 조치 권한·확정 판단을 지식에 포함하지 않는다. |
| `RECOVERY_SUPPORT` | 높음 | 공식 제도·기관 절차의 최신성이 중요하다. |
| `CUSTOMER_EXPLANATION_SUPPORT` | 상황에 따라 다름 | 검증 근거를 안전한 설명으로 변환하는 용도다. |
| `STAFF_DECISION_SUPPORT` | 높음 | AI가 최종 결정을 내리는 의미가 되지 않도록 한다. |

## 10. Metadata 초안 검토

| Metadata | 검색 필터 적합성 / 타입 | 필수 | Facts 연결 | 층 / 중복 / 현재 생성 가능성 |
|---|---|---|---|---|
| `knowledge_id` | 높음 / string | 필수 | 아니오 | Knowledge. 안정 ID이며 UI·Agent·Vector DB 명을 넣지 않는다. |
| `module_id`, `phase` | 높음 / enum | 선택 | 간접 | Knowledge. `phase`와 module의 중복을 검토한다. |
| `knowledge_type`, `knowledge_purpose` | 높음 / enum 또는 multi-enum | 필수 후보 | 간접 | Knowledge. 목적별 검색·재사용에 유용하다. |
| `primary_fraud_scenario`, `impersonated_entity`, `claim_type` | 중간 / enum | 선택 | 예 | Knowledge applicability. Facts에서 생성 가능하되 불확실성을 보존한다. |
| `demand_type`, `pressure_type`, `isolation_signal` | 높음 / multi-enum | 선택 | 예 | Knowledge applicability. 복수값 가능성을 유지한다. |
| `applicable_*_status` | 높음 / multi-enum | 선택 | 아니오 | Knowledge metadata. Runtime DTO가 아니다. |
| `remote_control`, `urgency` | 중간 / boolean 또는 enum | 선택 | 예 | boolean이 충분한지, demand/pressure와 중복되는지 검토한다. |
| `target_role` / `consumer_role` | 중간 / enum | 선택 | 아니오 | Knowledge consumer. 둘 중 하나의 명칭을 STEP 2에서 선택한다. |
| `related_agency`, `next_module` | 중간 / multi-enum | 선택 | 간접 | `next_module`은 실행 명령이 아니라 추가 검토 후보다. |
| `source_type`, `source_agency`, `source_date`, `source_url` | 높음 / enum·string·date | 필수 후보 | 아니오 | Source/Governance. 공식자료 조사 뒤 채운다. |

검색 필터보다 Chunk 본문이 적합한 정보(예: 세부 확인 방법, 예외, 고객 설명 문구, 금지·주의 행동)는 과도한 metadata화 대신 본문에 둔다.

## 11. target_agent / target_role 분리 제안

| 구분 | 현재 값 또는 후보 | 사용 원칙 |
|---|---|---|
| Runtime Agent | `CaseSupportAgent`, `CustomerVerificationAgent`, `CaseUpdateAgent`, `AgentRouter` | 현재 코드의 실행·routing 단위 |
| Knowledge Consumer Role | `CUSTOMER_SUPPORT`, `BANK_STAFF_SUPPORT`, `VERIFICATION_SUPPORT`, `CASE_ORCHESTRATION_SUPPORT` | Knowledge를 소비하는 업무 역할 |
| 향후 Agent Concept | Bank Agent, Verification Agent, Case Orchestrator | 향후 구현 후보이며 metadata의 강한 의존 대상이 아님 |

Knowledge에는 `target_role` 또는 `consumer_role` 중 하나를 채택한다. 예를 들어 `knowledge_purpose=VERIFICATION_SUPPORT`, `target_role=BANK_STAFF_SUPPORT`는 함께 존재할 수 있다. 전자는 지식이 지원하는 업무 목적이고 후자는 주된 소비자 역할이다.

## 12. Module 간 연결 원칙

- Module은 고정 직선 Workflow가 아니다. `P01 → P02 → P03` 순서를 강제하지 않는다.
- 하나의 Case에 여러 PREVENT·RECOVERY Module이 함께 관련될 수 있다.
- RECOVERY 상황에서도 추가 송금·노출 방지를 위한 PREVENT Knowledge가 필요할 수 있다.
- `next_module`은 자동 실행 또는 담당자 지시가 아니라 추가 확인 Knowledge 후보다.
- Fraud Type과 Module은 N:M 관계다.
- Official Procedure Knowledge는 여러 Module에서 재사용한다.

## 13. Chunk ID 규칙

초기 ID는 업무 분류와 순번만 표현하며 구현 기술·UI·작성일에 의존하지 않는다.

| 영역 | 예시 |
|---|---|
| Operational | `P01-001`, `P02-001`, `R03-001` |
| Fraud Type | `FT-PROSECUTION-001`, `FT-BANK-001`, `FT-FAMILY-001` |
| Official Procedure | `PROC-POLICE-001`, `PROC-FSS-001` |
| Verification | `VER-INSTITUTION-001` |

`PROC`와 `VER`의 실제 분리 필요성은 보류한다. ID에 UI명, Runtime Agent명, Vector DB명, Embedding model명, 문서 작성일, 자연어 제목을 넣지 않는다.

## 14. RAG Chunk 최소 구조

각 Chunk는 독립적으로 검토 가능해야 하며, 최소한 다음 순서를 권장한다.

1. Knowledge ID와 제목
2. 적용 상황
3. 확인 사항
4. 공식 근거 또는 검증 기준
5. 담당자 참고
6. 관련 Module / Fraud Type
7. 출처

필요할 때만 담당자 검토용 고객 질문 후보, 고객 설명 시 유의점, 예외·추가 확인, 금지·주의 행동을 넣는다. 모든 Chunk에 모든 필드를 기계적으로 채우지 않는다.

## 15. 현재 Taxonomy의 과도·중복 위험

- `transaction_status`와 `money_transferred`: 같은 Runtime 사실의 이중 표현 위험이 있다.
- Request와 Actual State: 절대 하나의 필드로 통합하지 않는다.
- `fraud_type`: 모든 사실을 하나의 거대 enum에 압축하지 않는다.
- P03: 독립 Operational Module인지 공통 Case Context Layer인지 검토가 필요하다.
- P06: 대응기관 확인, 보호조치, 신고·구제의 범위가 섞이지 않도록 재검토가 필요하다.
- `target_agent`: Runtime 구현명 대신 소비 역할 기준 metadata가 더 재사용 가능하다.

## 16. 추가 보완이 필요한 영역

P/R Module을 늘리기 전에 다음의 지식 공백을 확인한다: 공식 절차와 사칭 주장 비교 기준, 기관 공식 URL·대표연락처 확인 원칙, 실제 노출 상태별 확인 항목, 출처 최신성·폐기 정책, 사람 검토와 고객 설명 사이의 안전한 표현 경계.

## 17. STEP 2에서 결정할 사항

- P03의 독립성 및 P06의 세부 경계
- Knowledge Purpose의 최종 enum과 중복 제거
- `target_role`/`consumer_role` 명칭 선택
- Request·Actual State에 대한 Runtime Contract
- Claim/Pressure/Isolation의 상세 enum과 multi-value 정책
- `PROC`/`VER` Chunk 분리 여부
- Module 간 추천·우선순위·실행 규칙
- 공식 Corpus, Source Registry, 최신성·유효성·폐기 정책
- `source_date`의 의미를 자료 발표·게시일, 제도 시행·효력 발생일, 자료 기준 시점, 마지막 유효성 확인 시점으로 세분화할 필요가 있는지 검토. `published_at`, `effective_date`, `last_verified_at`은 이 검토를 위한 후보 예시이며 최종 Metadata Contract가 아니다.

## 18. STEP 1에서 확정하면 안 되는 사항

실제 웹·공식자료 조사 결과, RAG 본문 Chunk, Embedding/Vector DB/Retriever/Pipeline, Production 코드·DB·Frontend 변경, Chat UI·Router·Agent 호출 순서, 금융기관 권한, 법적 의무·권고, 자동 질문 발송·거래 차단·최종 판단은 본 문서의 범위가 아니다.

또한 현재의 발화 배열·문장 번호는 전체 통화의 실제 시간·순서·개입 시점으로 추정하지 않는다.

## 19. 최종 요약

### 현재 확정 가능한 구조

- Knowledge Base는 업무 목적·Case State·Structured Case Facts 중심이며 UI와 Runtime Agent 구현명에 종속되지 않는다.
- Structured Case Facts는 Evidence-linked `AI_EXTRACTED` proposal이며 canonical truth가 아니다.
- Request Signal, Actual Runtime State, Knowledge applicability metadata를 분리한다.
- Operational(PREVENT/RECOVERY), Fraud Type, Official Procedure/Verification, Action/Exposure, Source/Governance의 다층 구조를 사용한다.
- RAG는 외부 공식 지식이 필요한 경우에만 사용하고 담당자 판단을 지원한다.

### STEP 2에서 검토할 구조

- P03/P06 경계, Purpose·Role 최종 enum, state contract, Chunk 분류와 Module 연결 규칙
- 공식 Corpus·출처 최신성·검증 및 RAG 평가 기준

### 실제 공식자료 조사 전 확정할 수 없는 내용

- 기관별 실제 연락처·확인 방식·지급정지·피해구제 절차
- 법적 의무·권고의 구분, 제도 적용 요건·기한
- 시나리오별 특징을 공식적·보편적 사실로 단정하는 내용
