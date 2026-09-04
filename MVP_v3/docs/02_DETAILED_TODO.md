# Frontend V3 초세밀 개발 TODO

기준 문서: `MVP_v3/PRD.md`  
최종 갱신: 2026-09-03  
상태 표기: `[x] 완료`, `[-] 일부 완료·검증 제한`, `[ ] 후속`

이 문서는 구현 방향뿐 아니라 실제 코드 상태, 검증 결과, 운영 전 후속 작업을 함께 추적한다. 완료 표시는 코드와 정적·계약 검증 근거가 있는 항목에만 사용한다.

## A. 분석과 계약

- [x] A-01 `MVP_v3/PRD.md` 전체 확인
- [x] A-02 첨부 Codex 실행 지시문 전체 확인
- [x] A-03 Repository 상위 구조와 AGENTS 적용 범위 확인
- [x] A-04 V2 Frontend source map 확인
- [x] A-05 V2 Case/Message/Attachment/Verification/Action/AI client 확인
- [x] A-06 General API endpoint와 공개 Pydantic 계약 확인
- [x] A-07 Case/Message/Question/Fact/Verification/Action/Attachment DB migration 확인
- [x] A-08 Frontend → General API → AI API 호출 경계 확인
- [x] A-09 실제 SSE/WebSocket 부재와 polling 필요 기록
- [x] A-10 V2 파일을 수정하지 않는 독립 V3 경계 확정

## B. V3 기반 구조

- [x] B-01 `MVP_v3/frontend` 독립 앱 생성
- [x] B-02 V2와 다른 5176 strict port 설정
- [x] B-03 `/api` → General API 8100 proxy 설정
- [x] B-04 React Router `/`, `/cases/:caseId` 구성
- [x] B-05 공통 Header와 3열 Workspace Shell 구현
- [x] B-06 중립적 금융 업무도구 디자인 토큰 정의
- [x] B-07 820px 이하 Case List Drawer 구현
- [x] B-08 1180px 이하 Case Context Slide-over 구현

## C. API와 상태

- [x] C-01 General API 오류 parser 구현
- [x] C-02 Case list/detail Type 구현
- [x] C-03 Bundle/Message/Event Type 구현
- [x] C-04 Question/Fact Type 구현
- [x] C-05 Verification/Action Type 구현
- [x] C-06 Attachment Type과 binary upload 구현
- [x] C-07 AI Case-support와 invocation 구현
- [x] C-08 Case Room 병렬 조회와 부분 실패 처리
- [x] C-09 5초 polling과 mutation 후 즉시 refresh 구현
- [x] C-10 polling에서 AI support 반복 호출 제거
- [x] C-11 route 변경 시 이전 Case state 혼입 차단
- [x] C-12 AI API 직접 호출 금지 및 General API 단일 진입점 유지
- [ ] C-13 서버 이벤트 구독 endpoint 제공 후 polling을 SSE/WebSocket으로 교체
- [ ] C-14 인증 세션 기반 현재 사용자 ID·역할 주입

## D. Case List

- [x] D-01 ID 내림차순 기본 정렬
- [x] D-02 Case ID·위험·제목·상태·상대 시간 표시
- [x] D-03 검색과 위험/상태 필터
- [x] D-04 선택 Case 강조와 키보드 focus
- [x] D-05 목록 Loading skeleton
- [x] D-06 빈 Case 안내
- [x] D-07 목록 API 오류와 재시도
- [x] D-08 좁은 화면 Drawer 선택 후 자동 닫기
- [ ] D-09 실제 운영 데이터 기준 긴 제목·다국어·수천 건 성능 점검

## E. Shared Case Conversation

- [x] E-01 Case ID·유형·상태·담당자 Header
- [x] E-02 AI Brief 2~4문장 표시
- [x] E-03 AI Brief 실패 시 `initial_brief` fallback
- [x] E-04 대화/전체 기록 Toggle
- [x] E-05 메시지·질문·답변·검증·조치·Event 단일 Timeline
- [x] E-06 모든 Timeline 항목 `occurredAt ASC` 정렬
- [x] E-07 중복 질문/답변 원문 Message 제거
- [x] E-08 현재 은행 사용자 메시지만 오른쪽 정렬
- [x] E-09 고객/담당자/AI/검증/시스템 시각 구분
- [x] E-10 사용자가 하단에 있을 때만 새 항목 자동 추적
- [x] E-11 과거 기록 열람 중 강제 하단 이동 금지
- [x] E-12 Loading/Empty/부분 오류 상태
- [x] E-13 AI_PRIVATE 메시지 Shared Case 노출 차단
- [ ] E-14 인증 도입 후 메시지 본인 판정을 서버 세션 값으로 교체
- [ ] E-15 서버가 보장하는 전역 sequence로 동일 시각 항목의 순서를 확정

## F. 고객 대화와 입력

- [x] F-01 입력 대상 `고객에게`/`은행 내부` 명시적 Toggle
- [x] F-02 Enter 전송, Shift+Enter 줄바꿈
- [x] F-03 전송 중 중복 submit 차단
- [x] F-04 CUSTOMER/TEAM 공개 범위 정확히 매핑
- [x] F-05 파일 선택·제거·개수/용량 검사
- [x] F-06 첨부 upload 후 Message에 attachment ID 연결
- [x] F-07 이미지/문서 첨부 표시와 다운로드
- [x] F-08 첨부만 있는 메시지 전송
- [x] F-09 전송 오류 시 입력과 선택 파일 보존
- [ ] F-10 악성 파일 검사·운영 Object Storage·서명 URL 연동

## G. 맥락형 업무 실행

- [x] G-01 입력창 주변 Action을 4개 이하로 제한
- [x] G-02 고객 확인 질문 Dialog
- [x] G-03 AI 추천 질문 다중 선택
- [x] G-04 은행 직원 직접 질문 추가
- [x] G-05 질문 Queue 저장 후 Dialog 닫기
- [x] G-06 기관 Verification 생성 Dialog
- [x] G-07 Verification 결과·상태·근거 수정 Dialog
- [x] G-08 보호조치 Action 기록 Dialog
- [x] G-09 AI 사건 정리 요청
- [x] G-10 실제 금융 조치 자동 실행이 아님을 명시
- [ ] G-11 Work Card lifecycle을 서버에 영속화
- [ ] G-12 실제 거래조회·지급정지·신고 시스템은 별도 승인·감사 흐름으로 연동

## H. Case Context

- [x] H-01 위험 단계·점수 표시
- [x] H-02 위험 숫자보다 근거 우선 표시
- [x] H-03 사건 유형 표시
- [x] H-04 범죄자 Claim 목록
- [x] H-05 범죄자 Demand 목록
- [x] H-06 확정 Fact와 미확인 후보 분리
- [x] H-07 확인 필요 항목 표시
- [x] H-08 권장 조치 우선순위 표시
- [x] H-09 Verification 상태 요약
- [x] H-10 Recovery Mode 전용 긴급 조치
- [x] H-11 낮은 위험 Case의 과도한 적색 제거
- [ ] H-12 고객 답변 후보와 사람·기관이 확정한 사실의 의미를 Backend 상태값으로 엄격히 분리

## I. 반응형·접근성·품질

- [x] I-01 Desktop 3열 고정 업무 흐름
- [x] I-02 1180px 이하 Context slide-over
- [x] I-03 820px 이하 Case List drawer
- [x] I-04 Dialog 최초 focus와 Escape 닫기
- [x] I-05 icon button aria-label
- [x] I-06 색 외 텍스트·아이콘으로 상태 전달
- [x] I-07 긴 문장·파일명·URL overflow 방지
- [x] I-08 `prefers-reduced-motion` 존중
- [-] I-09 실제 브라우저 키보드·스크린리더 점검 — 연결 가능한 브라우저 세션 부재
- [-] I-10 실제 화면 크기별 시각 회귀 점검 — 연결 가능한 브라우저 세션 부재

## J. 검증과 PRD DoD

- [x] J-01 dependency 설치
- [x] J-02 TypeScript 검사
- [x] J-03 production build
- [x] J-04 정적 검사
- [x] J-05 General API·AI API·V3 Frontend 기동
- [x] J-06 `/api/cases` 실제 연결 확인
- [-] J-07 빈 Case 사용자 Flow — 코드 상태 구현, 빈 운영 DB·브라우저 클릭 검증 미실시
- [x] J-08 의심 Case fixture 기반 Timeline 조립 검사
- [x] J-09 Verification 생성/수정 API 계약 테스트
- [x] J-10 Action 생성 API 계약 테스트
- [x] J-11 Attachment 계약 테스트
- [x] J-12 낮은 위험 표현 소스 검사
- [x] J-13 Recovery 표현 소스 검사
- [x] J-14 Mock/TODO/FIXME 소스 검색
- [x] J-15 conflict marker 검색
- [x] J-16 V2를 V3 구현 과정에서 추가 변경하지 않았는지 확인
- [-] J-17 PRD Definition of Done 최종 대조 — 브라우저 시각·콘솔·실제 클릭 검증 제외 완료

### 2026-09-03 검증 기록

- `npm.cmd run typecheck`: 통과
- `npm.cmd run lint`: 통과 (`tsc -b` 기반 정적 검사)
- `npm.cmd run build`: 통과, 1,432 modules
- V3 `/`, `/cases/VP-1`, `/api/cases`: HTTP 200
- General API `/health`, AI API `/health`: HTTP 200
- 실제 VP-1 조회: Message 1, Question 3, Verification 1, Action 1, Event 1, Fact 3
- General API unittest: 34개 통과
- AI API unittest: 61개 통과
- Timeline 순서 fixture: `BRIEF → QUESTION → VERIFICATION_REQUEST → ACTION → MESSAGE → ANSWER → VERIFICATION_RESULT → EVENT` 통과
- 외부 유료 AI 요청은 검증 중 실행하지 않음
- 소스 내 Mock/TODO/FIXME 및 conflict marker 없음

## K. 운영 전 필수 Backend·AI 과제

- [ ] K-01 실제 인증 제공자와 은행 사용자 세션 결정
- [ ] K-02 Backend RBAC와 customer/bank view 서버 강제
- [ ] K-03 URL 파라미터만으로 내부 Bundle에 접근할 수 없도록 권한 검사
- [ ] K-04 SSE/WebSocket Case Event 구독 endpoint
- [ ] K-05 WorkCard lifecycle 서버 영속화
- [ ] K-06 질문 발송·답변·Fact·AI 요약을 원자적 workflow 또는 보상 트랜잭션으로 처리
- [ ] K-07 고객 답변을 곧바로 확정 사실로 간주하지 않고 AI 후보→담당자 확정 상태로 분리
- [ ] K-08 운영 MySQL migration 재시도·부분 적용 안전성 검증
- [ ] K-09 Redis/DB 기반 다중 인스턴스 AI quota
- [ ] K-10 sklearn 1.6.1 모델 artifact와 1.9.0 runtime 버전 정합화
- [ ] K-11 외부 시스템 실행은 사람 승인·권한·감사 로그·재시도 정책 추가
- [ ] K-12 실제 운영 데이터 기반 부하·보안·접근성·시각 회귀·E2E 테스트

K 항목은 현재 Frontend V3 실행을 막지는 않지만, 실제 은행 운영 완료 판정 전에는 반드시 해결해야 한다.

## L. 고객용 V3 후속 Track

- [x] L-01 고객용 제품 목표·사용자·안전 원칙 정의
- [x] L-02 일반 모드와 서버 영속 Recovery Mode 요구사항 정의
- [x] L-03 질문 Card·답변·중복 방지·AI 선제 질문 규칙 정의
- [x] L-04 고객 답변→Fact 후보→은행 Context 양방향 계약 정의
- [x] L-05 피해구제 Navigator와 시간순 상세 절차 Card 정의
- [x] L-06 첨부·북마크·진행 상황·공개 범위 요구사항 정의
- [x] L-07 고객용 Definition of Done 작성
- [ ] L-08 `CUSTOMER_PRD.md` 기준 API gap 상세 매핑
- [ ] L-09 Customer projection·인증·RBAC Backend 구현
- [ ] L-10 V3 Customer Frontend 구현
- [ ] L-11 은행 질문→고객 답변→은행 Fact 후보 E2E 검증
- [ ] L-12 Recovery Mode 양방향 E2E 검증

## M. 새 통화 분석 진입점

- [x] M-01 Home Empty 하단 `새 통화 분석하기` 버튼
- [x] M-02 같은 Home 영역에서 열리는 텍스트 입력 분석 UI
- [x] M-03 입력 문장·줄바꿈 구간 수와 사전 미리보기
- [x] M-04 실제 `POST /api/cases/analyze` General API 연결
- [x] M-05 생성 Case 재조회 후 ML 구간 결과 표시
- [x] M-06 생성 Case 재조회 후 LLM 초기 요약·주장·권장 조치·미확인 정보 표시
- [x] M-07 `NO_CASE`·실패·분석 중 상태와 재시도 UI
- [x] M-08 생성된 Case Room 이동
- [x] M-09 TypeScript·정적 검사·프로덕션 build·API 경로 검증
- [ ] M-10 실제 분석 요청을 사용한 브라우저 E2E — 비용 발생 가능성과 연결 브라우저 세션 부재로 미실시
