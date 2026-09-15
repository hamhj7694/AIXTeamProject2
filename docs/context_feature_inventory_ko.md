# Context Feature Inventory (Runtime 기준)

생성일: 2026-09-06T18:03:04.637516+09:00

## Runtime에서 확인한 세 계층

| 계층 | 실제 개수 | Runtime 전달 규칙 |
| --- | ---: | --- |
| A. Window Feature Extractor 전체 후보 | 152 | 모든 후보가 숫자 dict로 계산됨 |
| B. ML 모델 selected Feature | 23 | 23개 열을 고정 순서로 구성하며 0도 전달 |
| C. `case_context_features` LLM Context 필드 | 12 | 12개 필드를 모두 JSON 직렬화; 코드 목록은 active만 포함 |
| C-보조. `signals[]` 이벤트 속성 | 7 | 이벤트가 있을 때만 item 생성; 금액/요구 여부는 조건부 |

전체 LLM payload의 명명된 schema 슬롯은 top-level 4개 + `signals[]` 7개 + nested context 12개 = 23개입니다(컨테이너 포함). leaf 기준은 21개입니다. 152개 숫자 Feature 및 23개 ML selected 벡터는 LLM에 직접 전달되지 않습니다.

## A. LLM 자연어 맥락 생성에 실제 사용되는 핵심 Field

| 대분류             | 실제 Feature/Field명                            | 한국어 의미             | 값 형태      | 어떤 정보인가                          | LLM 입력 여부   | 자연어 생성 시 사용 예                                |
|:-------------------|:------------------------------------------------|:------------------------|:-------------|:---------------------------------------|:----------------|:------------------------------------------------------|
| LLM 구조화 Context | case_context_features.claimed_actor_types       | 사칭 주체 코드 목록     | list[str]    | ROLE_ 관찰 중 부인되지 않은 코드       | O               | 사칭 주체 코드 목록을 근거로 요약·주장·요구를 생성    |
| LLM 구조화 Context | case_context_features.claim_codes               | 범죄자 주장 코드 목록   | list[str]    | CLAIM_ 관찰 중 부인되지 않은 코드      | O               | 범죄자 주장 코드 목록을 근거로 요약·주장·요구를 생성  |
| LLM 구조화 Context | case_context_features.requested_action_codes    | 행동 요구 코드 목록     | list[str]    | REQUEST_ 관찰 중 부인되지 않은 코드    | O               | 행동 요구 코드 목록을 근거로 요약·주장·요구를 생성    |
| LLM 구조화 Context | case_context_features.manipulation_tactic_codes | 심리 조작 코드 목록     | list[str]    | TACTIC_ 관찰 중 부인되지 않은 코드     | O               | 심리 조작 코드 목록을 근거로 요약·주장·요구를 생성    |
| LLM 구조화 Context | case_context_features.exposure_risk_codes       | 노출 위험 코드 목록     | list[str]    | 독립 Extractor 경로에서는 기본 빈 목록 | O               | 노출 위험 코드 목록을 근거로 요약·주장·요구를 생성    |
| LLM 구조화 Context | case_context_features.amount_values_krw         | 금액 목록(원)           | list[float]  | 독립 Extractor 경로에서는 기본 빈 목록 | O               | 금액 목록(원)을 근거로 요약·주장·요구를 생성          |
| LLM 구조화 Context | case_context_features.chronology                | 턴별 관찰 연대기        | list[str]    | T{turn}:{status}:{code}                | O               | 턴별 관찰 연대기을 근거로 요약·주장·요구를 생성       |
| LLM 구조화 Context | case_context_features.unknown_fields            | 추가 확인 필요 필드     | list[str]    | 독립 Extractor 경로에서는 기본 빈 목록 | O               | 추가 확인 필요 필드을 근거로 요약·주장·요구를 생성    |
| LLM 구조화 Context | case_context_features.source                    | 구조화 입력 출처        | string       | 항상 STRUCTURED_CONTEXT_FEATURES_ONLY  | O               | 구조화 입력 출처을 근거로 요약·주장·요구를 생성       |
| LLM 구조화 Context | case_context_features.schema_version            | Context 스키마 버전     | string       | 현재 case_context_features.v2          | O               | Context 스키마 버전을 근거로 요약·주장·요구를 생성    |
| LLM 구조화 Context | case_context_features.observations              | 상태·턴 포함 전체 관찰  | list[object] | code, turn, status 객체                | O               | 상태·턴 포함 전체 관찰을 근거로 요약·주장·요구를 생성 |
| LLM 구조화 Context | case_context_features.extraction_method         | 추출 방식               | string       | 현재 LLM_INDEPENDENT                   | O               | 추출 방식을 근거로 요약·주장·요구를 생성              |
| LLM 이벤트 Context | signals[].signal                                | 사용자 표시용 신호 라벨 | string       | event를 privacy-safe 라벨로 변환       | O               | 활성 신호의 맥락을 자연어로 요약                      |
| LLM 이벤트 Context | signals[].event_family                          | 이벤트 대분류           | enum         | IMPERSONATION 등 5개 family            | O               | 활성 신호의 맥락을 자연어로 요약                      |
| LLM 이벤트 Context | signals[].subtype                               | 이벤트 세부 유형        | string|null  | 각 family subtype                      | O               | 활성 신호의 맥락을 자연어로 요약                      |
| LLM 이벤트 Context | signals[].impersonation_group                   | 사칭 그룹               | string|null  | 공공기관·금융기관·가족 등              | O               | 활성 신호의 맥락을 자연어로 요약                      |
| LLM 이벤트 Context | signals[].turn                                  | 발견 턴                 | integer      | 원문 대신 턴 번호                      | O               | 활성 신호의 맥락을 자연어로 요약                      |
| LLM 이벤트 Context | signals[].amount_krw                            | 이벤트 금액             | number       | 금액이 있을 때만 조건부 전달           | O               | 활성 신호의 맥락을 자연어로 요약                      |
| LLM 이벤트 Context | signals[].is_requested                          | 요구 여부               | boolean      | 값이 있을 때만 조건부 전달             | O               | 활성 신호의 맥락을 자연어로 요약                      |

## B. 내부 Extractor/ML에는 존재하지만 LLM 자연어 생성에는 직접 사용되지 않는 Feature

전체 152개 행은 CSV에 수록했습니다. 아래는 ML selected 23개입니다.

| 대분류                 | 실제 Feature/Field명                  | 한국어 의미                             | 값 형태   | 어떤 정보인가                                | LLM 입력 여부   | 자연어 생성 시 사용 예   |
|:-----------------------|:--------------------------------------|:----------------------------------------|:----------|:---------------------------------------------|:----------------|:-------------------------|
| 사칭 주체              | imp_present                           | 사칭 존재                               | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 사칭 주체              | imp_financial                         | 사칭 금융기관                           | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 사칭 주체              | imp_other                             | 사칭 기타                               | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 사칭 주체              | imp_bank                              | 사칭 은행                               | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 심리 압박              | strategy_authority_present            | 심리전략 권위 존재                      | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 공포                   | strategy_fear_present                 | 심리전략 공포 존재                      | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 긴급성                 | strategy_urgency_present              | 심리전략 긴급성 존재                    | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 심리 압박              | strategy_legitimacy_present           | 심리전략 정당성 존재                    | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 심리 압박              | strategy_info_extraction_present      | 심리전략 정보 탈취 존재                 | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 심리 압박              | strategy_info_extraction_repeat       | 심리전략 정보 탈취 반복                 | integer   | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 심리 압박              | strategy_diversity                    | 심리전략 유형 다양성                    | integer   | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 개인정보·인증정보 요구 | action_sensitive_info_present         | 행동요구 민감정보 정보 존재             | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 개인정보·인증정보 요구 | action_sensitive_info_repeat          | 행동요구 민감정보 정보 반복             | integer   | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 행동 요구              | action_contact_restriction_present    | 행동요구 접촉 제한 존재                 | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 행동 요구              | action_other_high_risk_action_present | 행동요구 기타 고위험 위험 행동요구 존재 | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 행동 요구              | action_other_high_risk_action_repeat  | 행동요구 기타 고위험 위험 행동요구 반복 | integer   | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 행동 요구              | action_diversity                      | 행동요구 유형 다양성                    | integer   | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 금전 요구              | money_movement_present                | 금전이동 이동 존재                      | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 금전 요구              | money_movement_repeat                 | 금전이동 이동 반복                      | integer   | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 금전 요구              | money_transfer_present                | 금전이동 이체 존재                      | 0/1       | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 금전 요구              | money_action_diversity                | 금전이동 행동요구 유형 다양성           | integer   | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 신호 집계              | signal_family_count                   | 신호 패밀리 횟수                        | integer   | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |
| 상호작용               | ix_info_sensitive                     | 상호작용 정보 민감정보                  | number    | Window 이벤트에서 계산되는 숫자 후보 Feature | X               | 직접 사용 안 함          |

## PPT용 한국어 카테고리

| PPT 카테고리   | 실제 코드                       | 한국어 의미            |
|:---------------|:--------------------------------|:-----------------------|
| 사칭 주체      | ROLE_PROSECUTION                | 검찰·수사기관 사칭     |
| 사칭 주체      | ROLE_POLICE                     | 경찰 사칭              |
| 사칭 주체      | ROLE_BANK                       | 은행 사칭              |
| 사칭 주체      | ROLE_FAMILY                     | 가족 사칭              |
| 사칭 주체      | ROLE_SUPPORT                    | 고객지원·수리센터 사칭 |
| 범죄자 주장    | CLAIM_CRIME_INVOLVEMENT         | 범죄 연루 주장         |
| 범죄자 주장    | CLAIM_ACCOUNT_VERIFICATION      | 계좌 검증 주장         |
| 범죄자 주장    | CLAIM_DEVICE_BROKEN             | 기기 고장 주장         |
| 범죄자 주장    | CLAIM_UNAUTHORIZED_PAYMENT      | 미승인 결제 주장       |
| 범죄자 주장    | CLAIM_LOAN_APPROVAL             | 대출 승인 주장         |
| 요구 목적      | PURPOSE_SAFE_ACCOUNT            | 안전계좌 명목          |
| 요구 목적      | PURPOSE_LOAN_REPAYMENT          | 대출 상환 명목         |
| 요구 목적      | PURPOSE_REPAIR                  | 수리 명목              |
| 요구 목적      | PURPOSE_REFUND                  | 환불 명목              |
| 행동 요구      | REQUEST_TRANSFER                | 송금 요구              |
| 행동 요구      | REQUEST_INSTALL_APP             | 앱 설치 요구           |
| 행동 요구      | REQUEST_AUTH_INFO               | 인증정보 요구          |
| 행동 요구      | REQUEST_PERSONAL_INFO           | 개인정보 요구          |
| 행동 요구      | REQUEST_KEEP_CALL               | 통화 유지 요구         |
| 행동 요구      | REQUEST_SECRECY                 | 비밀 유지 요구         |
| 긴급성         | DEADLINE_TODAY                  | 오늘 기한              |
| 긴급성         | DEADLINE_IMMEDIATE              | 즉시 기한              |
| 심리 압박      | TACTIC_FEAR                     | 공포 유발              |
| 심리 압박      | TACTIC_URGENCY                  | 긴급성 압박            |
| 심리 압박      | TACTIC_ISOLATION                | 고립 유도              |
| 피해·행동 상태 | CUSTOMER_TRANSFERRED            | 고객 송금 완료         |
| 피해·행동 상태 | CUSTOMER_NOT_TRANSFERRED        | 고객 미송금            |
| 피해·행동 상태 | CUSTOMER_PROVIDED_AUTH          | 고객 인증정보 제공     |
| 피해·행동 상태 | CUSTOMER_PROVIDED_PERSONAL_INFO | 고객 개인정보 제공     |
| 피해·행동 상태 | CUSTOMER_INSTALLED_APP          | 고객 앱 설치           |
| 정상 맥락      | NORMAL_DEPOSIT_CONSULTATION     | 정상 예금·은행 상담    |
| 정상 맥락      | NORMAL_CARD_CONSULTATION        | 정상 카드 상담         |
| 정상 맥락      | NORMAL_DAILY_CALL               | 정상 일상 통화         |

## 연결 관계

`DiagnosisService.analyze()`는 원문을 Window 이벤트/ML 경로와 독립 Context Extractor 경로에 각각 일시적으로 전달합니다. 이후 `signal_context_payload(events)`에 독립 `case_context_features`를 덮어써서 Context LLM에 보냅니다. Context LLM의 `ContextResult.summary`가 HIGH Case에서 `initial_brief`가 되며, `InitialReportBuilder`의 summary 섹션에도 같은 값이 들어갑니다. Shared Case 저장 직전 `project_diagnosis_for_case()`가 원문 evidence/window text를 안전 라벨로 치환하고 `input_text`는 빈 문자열로 저장합니다.
