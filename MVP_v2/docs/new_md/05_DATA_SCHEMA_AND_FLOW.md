# MVP_v2 데이터 스키마·흐름

## 2026-09-03 실제 AI·Backend 연결 기준선

- 활성 로컬 저장소 `backend/data/mvp_v2.sqlite3`는 Case·휴지통 0건의 빈 상태에서 시작한다.
- 초기화 전 테스트 저장소는 `backend/data/archive/260903_pre_ai_connection/`에 실행 경로와 분리해 보관하며 Git에는 포함하지 않는다.
- 다음 Case는 저장소의 순차 ID 규칙에 따라 `VP-1`부터 생성한다.
- Frontend는 다음 로드에서 기존 `mvp-v2:*` 브라우저 테스트 상태와 한정된 구형 키를 한 번만 제거한다. 이후 생성되는 실제 연동 데이터는 반복 초기화하지 않는다.
- 계약 테스트 fixture와 진단 화면의 세 가지 샘플 입력은 실행 DB 레코드가 아니며, API 계약 검증과 진단 입력 편의를 위해 유지한다.

## Case 중심 엔티티

`Case`(상태·담당자·피해정보·요약·시간) 아래에 `Message`, `Question/Answer`, `CaseFact`, `Verification`, `BankAction`, `PersonalNote`, `Bookmark`, `Event`, `Report`, `Member/Presence`가 연결된다. 모든 엔티티는 `case_id`를 공유하며 화면별 복사본을 만들지 않는다.

## 공개 범위

- 고객: CUSTOMER 공개 메시지, 본인 질문/답변, 공개 검증 결과, 진행 상태
- 은행: 고객 채널 + BANK_INTERNAL 협업 + AI_PRIVATE 개인 작업
- 검증: 검증에 필요한 최소 Case 정보

`Verification`은 `status, result_summary, evidence_url, verified_by, rag_source, customer_visible`을 가진다. `customer_visible`은 결과 내용을 자동 공개하는 값이 아니라, 고객 공개 카드로 전달할 수 있는 담당자 승인 후보임을 뜻한다.

## 이벤트·카드 흐름

의미 있는 메시지·질문 등록/답변·Fact 확정·검증·은행 조치·보고서·종료만 Event와 `updated_at`을 변경한다. 기능 카드는 `초안 → 실행 완료 → 고객/검증 Task 전달`로 상태를 저장하고, 고객 답변은 원 질문 ID에 연결한다.

Frontend 동기화 규칙: 질문 카드 전달과 보고서 생성처럼 팀이 함께 알아야 하는 업무 결과는 원본 객체 처리 후 은행 `TEAM` 채널에 짧은 `SYSTEM_EVENT` 업무 알림을 추가한다. 고객 답변은 Question Queue를 원본으로 삼아 `AI 개인 작업공간`의 질문·답변 접수 카드로 표시하며 `TEAM`에 복제하지 않는다. 일반 대화 말풍선과 섞이지 않도록 `SYSTEM_EVENT`는 별도 업무 카드로 렌더링한다. 고객의 `이미 사기 당했어요` 피해 신고도 `TEAM` 채널에 게시하지 않는다. 전용 `POST /api/cases/{case_id}/customer-emergency` 명령이 고객 확인 메시지, `victim_transfer_status=YES`, `mode=RECOVERY`, `CASE_FIELD_UPDATED` Event, Case 공용 `AI_INTERNAL + AI_PRIVATE` 긴급 알림을 함께 생성한다. 고객 클라이언트가 은행 내부 메시지를 직접 만들지 않으며, 운영 DB에서 완전한 원자성을 보장하기 위한 트랜잭션/Outbox 적용은 후속 과제다.

Frontend 화면 갱신은 `서버 mutation 성공 → case_id가 포함된 mvp-v2:case-changed 이벤트 발행 → 현재 탭 CustomEvent + 다른 탭 storage event → 해당 Case 화면과 Case 목록이 API 원본 재조회` 순서다. 메시지·질문·Fact·검증·담당자·상태 변경이 이 경로를 공유한다. 이벤트 payload는 데이터를 복제하지 않고 `caseId, reason, changedAt`만 전달한다. 3초 채팅/15초 목록 Polling은 누락 복구용 안전망이며, 운영 실시간 채널이 도입되면 SSE/WebSocket 수신이 동일 재조회 함수를 호출하도록 교체한다. Presence heartbeat는 업무 데이터 변경이 아니므로 이 이벤트를 발행하지 않는다.

보고서는 채팅·로그 원문을 복제하지 않는다. `Case`, 확정/후보 `CaseFact`, `Verification`, 담당자, 미확인 사항, 우선 작업, 처리 현황을 종합해 문서형 결과를 만든다. 현재 Frontend 구조화 템플릿은 AI 보고서 엔진 연결 전 계약 예시이며, AI 출력도 동일한 근거 필드와 사실/추론 구분을 유지해야 한다.

`미확인 정보` Frontend 흐름은 `GET /api/cases/{case_id}/facts → PROPOSED/UNRESOLVED 후보 표시 → 담당자 검토 → POST /facts/{fact_id}/confirm → CONFIRMED 재조회 → 은행 정보 레일 갱신`이다. 후보 생성은 현재 고객 질문 답변 흐름이 담당하며, AI/은행의 임의 텍스트를 자동으로 확정하지 않는다. 향후 생성·수정 UI가 추가되더라도 `confirmed_by`, `confirmed_at`, `evidence_message_id`를 보존해야 한다.

동일한 `미확인 정보` 카드에서 완료/확인 불가 기관 검증 결과를 `result_summary`, `verified_by`, `rag_source`, `evidence_url`, `customer_visible` 단위로 조회한다. 근거 URL은 Frontend에서 HTTP/HTTPS만 열 수 있다. `customer_visible=true`도 즉시 고객 공개를 뜻하지 않으며, 고객 전달 카드 생성과 담당자 최종 승인은 별도 후속 흐름이다.

## 개인 메모와 북마크

`PersonalNote`: `note_id, case_id, author_id, content, visibility(private-to-author), created_at, updated_at`. 개인 메모는 자동저장하고, 명시적 액션으로만 `BANK_INTERNAL` 메시지 또는 `CaseFact` 후보로 전환한다.

현재 MVP API는 작성자 기준 개인 메모 조회·생성·수정·삭제와 SQLite 영속화를 제공한다. 은행 화면에는 700ms 자동저장·Case별 복원·수정·삭제 UI가 연결되어 있으며, 내부 공유/Fact 후보 전환은 후속 계약 작업이다.

`Bookmark`: `bookmark_id, case_id, user_id, target_type, target_id, channel, note(optional), created_at`. 북마크는 원본 Message/Card를 참조하며 클릭하면 채널 전환 후 해당 원문을 강조한다. 개인 북마크가 기본이고 팀 공유 북마크는 후속 권한 기능이다.

현재 Frontend는 은행 담당자 메시지와 고객 공개 메시지에 `localStorage` 기반 `bookmarkStore` adapter를 사용한다. 은행과 고객의 북마크는 `user_id`로 격리하며 Case·사용자별 목록, 추가/해제, 채널 자동 전환, 원문 스크롤/강조가 구현되어 있다. 이 저장소는 임시 UI adapter이므로 Backend 담당자는 동일 필드와 호출 의미를 유지한 채 Bookmark API/SQLite 구현으로 교체한다. 기능 카드 북마크는 `target_type=CARD` 계약과 카드 인스턴스 ID가 확정된 뒤 연결한다.

## Case 상태

기본 고객 진행 단계는 `상황 접수 → 피해 여부 확인 → 기관 확인 → 보호 조치 → 처리 완료`이다. 시스템 상태는 `NEW/DETECTED, ASSESSING, CUSTOMER_CHECK, VERIFYING, PROTECTING, CASE_CLOSED, RECOVERY_MODE`를 사용한다. `RECOVERY_MODE`는 피해 발생 확인 후 기존 Case의 Timeline·검증·근거를 재사용한다.

## AI/RAG 경계

ML은 문장별 위험과 Case 생성 Trigger를 담당한다. Customer/Bank/Verification Agent는 후보와 초안을 제안하며 담당자가 확정한다. RAG 결과는 답변뿐 아니라 출처·최신성·적용 범위·확인 필요 여부를 저장한다.

## 저장소와 후속

로컬 MVP 원본은 SQLite/API다. 보고서 버전·휴지통, 검증 결과 입력, RBAC, SSE/WebSocket은 후속 구현 범위이며 상위 PRD의 Acceptance Criteria를 만족해야 완료한다.

## 첨부파일 스키마와 흐름

`Attachment`는 `attachment_id, case_id, original_name, storage_path(server-only), mime_type, size_bytes, sha256, uploaded_by, status(UPLOADED/LINKED), visibility, ai_readable, created_at`을 가진다. 메시지는 `attachment_ids`로 첨부를 연결하며 MySQL에서는 `message_attachments` 연결 테이블을 사용한다. `storage_path`는 서버 상대 경로이고 Public API 응답에 포함하지 않는다.

흐름은 `파일 선택 → Frontend 크기/개수 확인 → binary 업로드 → 서버 확장자·MIME·signature 확인 → UUID 파일명으로 Case별 경로 저장 → DB 메타데이터 생성 → Message 생성 시 attachment_ids 연결 → LINKED 전환 → 역할별 조회/다운로드` 순서다. 같은 Case가 아니거나 메시지와 공개 범위가 다른 첨부는 연결할 수 없다.

현재 AI 내부 목록은 `ai_readable=true` 메타데이터와 은행 범위 다운로드 URL을 제공한다. 이것은 AI가 이미 파일 내용을 이해한다는 의미가 아니다. `악성 파일 검사 → 텍스트/이미지 추출 → OCR → 추출 결과/오류/버전 저장 → 권한 필터 → RAG 색인`은 후속 파이프라인이며 서비스 인증을 적용한 내부 API에서만 실행한다. 미연결 `UPLOADED` 파일은 재전송을 위해 잠시 유지하되 보존시간 이후 정리 작업이 필요하다.

## 음성 데이터 경계

현재 엔티티·화면·E2E에서 음성 통화 세션, 녹음 파일, STT segment를 생성하지 않는다. 기존 voice 계약과 컴포넌트는 휴면 참고 코드이며 현재 라우트 데이터 흐름에 포함되지 않는다. 후속 구현 시 `VoiceSession`, `RecordingConsent`, `AudioAsset`, `TranscriptSegment`를 일반 Attachment와 구분하고 암호화·동의·보존기간·접근 감사 정책을 별도 설계한다.

## WorkCard 표시 계약

Frontend 표준 descriptor는 `card_id, card_type, stage, title, payload, source, created_at`이다. `source`는 `USER_ACTION | AI_PROPOSAL | CASE_EVENT`, `stage`는 `DRAFT | READY | SUBMITTING | REGISTERED | DELIVERED | FAILED`를 사용한다. descriptor는 표시·입력 상태 계약이며 원본 도메인 객체를 대신하지 않는다.

카드 실행 시 원본 객체(`Question`, `Verification`, `BankAction`, `Message`, `Case`)를 먼저 생성/변경하고, 성공 후 관련 `Event`와 은행 `SYSTEM_EVENT` 알림을 갱신한다. 원본 실행 성공 후 알림 생성이 실패하면 원본을 롤백된 것처럼 표시하지 않고 부분 성공 경고를 보여 중복 실행을 방지한다. 운영 Backend에서는 이 부분을 트랜잭션/Outbox로 단일화한다.

현재 Frontend 레지스트리는 `FACT_REVIEW, QUESTION_PLAN, VERIFICATION_REQUEST, BANK_ACTION, CUSTOMER_NOTICE, CASE_TRANSITION`을 지원한다. 상세 payload와 역할별 노출은 `07_WORK_CARD_CATALOG.md`를 따른다.

### 은행 질문 → 고객 카드 → Fact 후보

`AI 질문 후보(question_text, reason, customer_explanation, options, answer_mode, allow_free_text) → 은행 직원 선택/직접 질문 추가 → Question Queue(PENDING) → 한 문항 ASKED → 고객 공개 projection(reason/requested_by 제거) → 고객 질문 카드 → 선택지 또는 직접 입력 → 고객 Message + Question ANSWERED(answer_text/answered_at 저장) → 답변 접수 카드 복원 → CaseFact PROPOSED → 다음 PENDING 질문 ASKED` 순서다.

질문 전달 시 생성되는 Customer Agent의 일반 질문 말풍선은 Frontend에서 동일한 `question_text`를 가진 구조화 질문 카드와 중복 표시하지 않는다. 질문 전·후 상태는 Queue가 단일 원본이며, 새로고침 후에도 `ANSWERED + answer_text`를 사용해 답변 접수 카드를 복원한다.

고객은 `customer_explanation`을 보지만 은행 내부 `reason`은 보지 않는다. `options`는 AI가 생성할 수 있고, `allow_free_text=true`이면 선택지에 없는 상황을 직접 입력할 수 있다. 고객 답변 접수 카드는 답변이 최종 확정 사실이 아니라 담당자 검토 대상임을 명시한다.

은행 AI 개인 작업공간은 같은 Question Queue의 `ANSWERED + answer_text`를 3초 주기로 조회해 질문과 답변을 한 묶음의 얇은 접수 카드로 표시한다. 별도의 복제 메시지를 데이터 원본으로 사용하지 않는다. `확인 및 확인중 정보` 패널도 같은 Queue를 사용해 `PENDING/ASKED/ANSWERED/SKIPPED`와 응답 내용을 일괄 표시한다.

고객 오른쪽 보조 영역은 상태 전환 전후 동일한 Grid를 유지한다. 기본 상태는 `CustomerProgressCard + 안전 상담 안내`, 피해 발생 선택 후에는 `CustomerProgressCard + RecoveryGuideCard`이며, 중복된 현재 확인/정적 피해구제 안내 카드는 렌더링하지 않는다.

`RecoveryGuideCard`는 오른쪽의 작은 단계 선택 메뉴만 담당한다. 선택값 `recovery_step_id(CONTACT/EVIDENCE/REPORT/RELIEF)`는 고객 Chat Shell의 `RECOVERY_STEP` descriptor로 변환되고, `RecoveryStepDetailCard`가 실행 순서·주의사항·공식 연락처와 `AI_ADVICE/HUMAN_HANDOFF` 요청을 렌더링한다. 상세 내용은 오른쪽 메뉴 아래로 펼치지 않는다. 피해구제 모드는 서버 Case의 `mode=RECOVERY` 또는 `victim_transfer_status=YES`를 권위 값으로 복원하고 localStorage는 응답 지연·오프라인 UI 보조값으로만 사용한다. 마지막 선택 단계는 Case별 localStorage에 유지하며 Backend `RecoveryAction` 상태 API로 교체할 예정이다.

피해구제 모드 최초 진입은 하나의 전용 서버 명령으로 처리한다. 동일 요청이 반복되더라도 고객 확인 메시지와 AI 긴급 알림을 중복 생성하지 않는다. `CASE_FIELD_UPDATED.payload.victim_transfer_status=YES` 이벤트는 사건 진행 현황에서 `고객 피해 발생 신고` 전용 경고로 렌더링하며, 클릭하면 Case 공용 AI 긴급 알림이 있는 `AI 개인 작업공간`으로 이동한다. 이 최초 신고는 은행 `TEAM` 메시지를 만들지 않는다. 이후 고객이 상세 절차 카드에서 `AI_ADVICE` 또는 `HUMAN_HANDOFF`를 누르는 것은 별개의 지원 요청이며, 요청 종류에 맞는 담당 채널과 Action으로 연결한다.

고객 북마크는 은행 북마크와 같은 `bookmarkStore` 계약을 사용하되 `user_id=mvp-v2-customer`로 격리한다. 고객은 CUSTOMER 채널에서 본 메시지만 북마크하며 목록 선택 시 해당 메시지 DOM으로 이동한다. 실서비스에서는 인증 사용자 기반 Bookmark API로 교체한다.

### 검증 결과 고객 projection

고객 Bundle의 `customer_verification_results`는 `status=COMPLETED`, `customer_visible=true`, `result_summary` 존재 조건을 모두 만족한 항목만 포함한다. 필드는 `verification_task_id, target, result_summary, published_at`만 허용하며 `claim, evidence_url, verified_by, rag_source`는 고객에게 전달하지 않는다.
