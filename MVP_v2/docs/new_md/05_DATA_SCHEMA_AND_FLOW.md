# MVP_v2 데이터 스키마·흐름

## Case 중심 엔티티

`Case`(상태·담당자·피해정보·요약·시간) 아래에 `Message`, `Question/Answer`, `CaseFact`, `Verification`, `BankAction`, `PersonalNote`, `Bookmark`, `Event`, `Report`, `Member/Presence`가 연결된다. 모든 엔티티는 `case_id`를 공유하며 화면별 복사본을 만들지 않는다.

## 공개 범위

- 고객: CUSTOMER 공개 메시지, 본인 질문/답변, 공개 검증 결과, 진행 상태
- 은행: 고객 채널 + BANK_INTERNAL 협업 + AI_PRIVATE 개인 작업
- 검증: 검증에 필요한 최소 Case 정보

`Verification`은 `status, result_summary, evidence_url, verified_by, rag_source, customer_visible`을 가진다. `customer_visible`은 결과 내용을 자동 공개하는 값이 아니라, 고객 공개 카드로 전달할 수 있는 담당자 승인 후보임을 뜻한다.

## 이벤트·카드 흐름

의미 있는 메시지·질문 등록/답변·Fact 확정·검증·은행 조치·보고서·종료만 Event와 `updated_at`을 변경한다. 기능 카드는 `초안 → 실행 완료 → 고객/검증 Task 전달`로 상태를 저장하고, 고객 답변은 원 질문 ID에 연결한다.

Frontend 동기화 규칙: 질문 카드 전달, 고객 답변, 긴급 대응 시작, 보고서 생성 시 원본 객체 처리 후 은행 `TEAM` 채널에 짧은 `SYSTEM_EVENT` 업무 알림을 추가한다. 일반 대화 말풍선과 섞이지 않도록 `SYSTEM_EVENT`는 별도 업무 카드로 렌더링한다. 현재 MVP는 Frontend가 후속 메시지를 생성하지만, 실서비스에서는 원본 트랜잭션 성공과 같은 서버 트랜잭션/Outbox가 관련 채널 Event를 발행해야 하며 고객 클라이언트가 은행 내부 메시지를 직접 생성해서는 안 된다.

보고서는 채팅·로그 원문을 복제하지 않는다. `Case`, 확정/후보 `CaseFact`, `Verification`, 담당자, 미확인 사항, 우선 작업, 처리 현황을 종합해 문서형 결과를 만든다. 현재 Frontend 구조화 템플릿은 AI 보고서 엔진 연결 전 계약 예시이며, AI 출력도 동일한 근거 필드와 사실/추론 구분을 유지해야 한다.

`미확인 정보` Frontend 흐름은 `GET /api/cases/{case_id}/facts → PROPOSED/UNRESOLVED 후보 표시 → 담당자 검토 → POST /facts/{fact_id}/confirm → CONFIRMED 재조회 → 은행 정보 레일 갱신`이다. 후보 생성은 현재 고객 질문 답변 흐름이 담당하며, AI/은행의 임의 텍스트를 자동으로 확정하지 않는다. 향후 생성·수정 UI가 추가되더라도 `confirmed_by`, `confirmed_at`, `evidence_message_id`를 보존해야 한다.

동일한 `미확인 정보` 카드에서 완료/확인 불가 기관 검증 결과를 `result_summary`, `verified_by`, `rag_source`, `evidence_url`, `customer_visible` 단위로 조회한다. 근거 URL은 Frontend에서 HTTP/HTTPS만 열 수 있다. `customer_visible=true`도 즉시 고객 공개를 뜻하지 않으며, 고객 전달 카드 생성과 담당자 최종 승인은 별도 후속 흐름이다.

## 개인 메모와 북마크

`PersonalNote`: `note_id, case_id, author_id, content, visibility(private-to-author), created_at, updated_at`. 개인 메모는 자동저장하고, 명시적 액션으로만 `BANK_INTERNAL` 메시지 또는 `CaseFact` 후보로 전환한다.

현재 MVP API는 작성자 기준 개인 메모 조회·생성·수정·삭제와 SQLite 영속화를 제공한다. 은행 화면에는 700ms 자동저장·Case별 복원·수정·삭제 UI가 연결되어 있으며, 내부 공유/Fact 후보 전환은 후속 계약 작업이다.

`Bookmark`: `bookmark_id, case_id, user_id, target_type, target_id, channel, note(optional), created_at`. 북마크는 원본 Message/Card를 참조하며 클릭하면 채널 전환 후 해당 원문을 강조한다. 개인 북마크가 기본이고 팀 공유 북마크는 후속 권한 기능이다.

현재 Frontend는 은행 담당자 메시지에 한해 `localStorage` 기반 `bookmarkStore` adapter를 사용한다. Case·사용자별 목록, 추가/해제, 채널 자동 전환, 원문 스크롤/강조가 구현되어 있다. 이 저장소는 임시 UI adapter이므로 Backend 담당자는 동일 필드와 호출 의미를 유지한 채 Bookmark API/SQLite 구현으로 교체한다. 기능 카드 북마크는 `target_type=CARD` 계약과 카드 인스턴스 ID가 확정된 뒤 연결한다.

## Case 상태

기본 고객 진행 단계는 `상황 접수 → 피해 여부 확인 → 기관 확인 → 보호 조치 → 처리 완료`이다. 시스템 상태는 `NEW/DETECTED, ASSESSING, CUSTOMER_CHECK, VERIFYING, PROTECTING, CASE_CLOSED, RECOVERY_MODE`를 사용한다. `RECOVERY_MODE`는 피해 발생 확인 후 기존 Case의 Timeline·검증·근거를 재사용한다.

## AI/RAG 경계

ML은 문장별 위험과 Case 생성 Trigger를 담당한다. Customer/Bank/Verification Agent는 후보와 초안을 제안하며 담당자가 확정한다. RAG 결과는 답변뿐 아니라 출처·최신성·적용 범위·확인 필요 여부를 저장한다.

## 저장소와 후속

로컬 MVP 원본은 SQLite/API다. 보고서 버전·휴지통, 검증 결과 입력, RBAC, SSE/WebSocket은 후속 구현 범위이며 상위 PRD의 Acceptance Criteria를 만족해야 완료한다.
