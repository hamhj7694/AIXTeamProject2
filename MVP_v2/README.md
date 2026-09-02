# MVP v2 — Chat-first Case Workspace

> 문서 기준일: 2026-09-02  
> 상태: 프론트엔드 전환 방향 확정, 구현 전

## 1. 목표

기존의 여러 화면과 많은 고정 정보를 하나의 복잡한 대시보드에 배치하는 방식에서 벗어나, **하나의 Case를 중심으로 대화·질문·검증·조치·보고 결과를 주고받는 Chat-first UI**로 전환한다.

고객과 은행은 동일한 `case_id`와 Case 상태를 공유하지만, 서로 다른 목적·권한·정보 밀도를 가진 별도 화면을 사용한다.

- 고객 화면: 추가 피해 방지, 상황 설명, 질문 응답, 진행상태 확인
- 은행 화면: 여러 관계자의 협업, 고객 확인, 기관 검증, 조치 기록, Case 종료
- 공통: 메시지 입력창은 채팅 영역 하단에 고정
- 은행: 화면 밖의 실시간 보고서 패널 대신 **Append-only Case Live Log** 사용
- 고객: 기술적인 로그 대신 현재 단계와 다음 행동만 간단히 제공

## 2. 최종 핵심 결정

1. 채팅이 두 화면의 주요 작업 공간이다.
2. 화면 밖에는 대화 중에도 놓치면 안 되는 극소수 상태만 표시한다.
3. 고객 화면과 은행 화면의 데이터 접근 권한을 분리한다.
4. 은행의 내부 AI 업무 대화와 고객에게 보내는 대화를 명확히 구분한다.
5. 채팅 안의 카드가 DB 원본 데이터가 되지 않는다.
6. Message·Verification·Action·Report·Event 등 Backend에 저장된 Entity를 채팅 Block과 Log Row로 투영한다.
7. Case 변경은 덮어쓰는 화면 메모가 아니라 Version이 있는 현재 상태와 Append-only Event Log로 추적한다.
8. 현재 Event Polling을 MVP 시작점으로 재활용하고, 이후 SSE 또는 WebSocket으로 교체한다.
9. 루트 페이지와 Case 리스트 페이지는 기존 스타일·Route·API Client를 우선 재활용한다.
10. 은행 내부 팀 채팅은 사람 간 대화가 기본이며, AI는 `@CaseCopilot`으로 명시 호출됐을 때만 응답한다.
11. 은행 참여자의 영구 역할과 현재 접속 상태는 분리한다.

## 3. 문서 구성

| 문서 | 내용 |
|---|---|
| `01_frontend_final_direction.md` | 고객·은행 화면의 최종 구조와 구성요소 |
| `02_chat_and_case_log_contract.md` | 채팅 Block, 입력창, 은행 Case Log 규격 |
| `03_reuse_and_implementation_todo.md` | 기존 코드 재활용 범위와 구현 순서 |
| `04_bank_collaboration_and_ai_invocation.md` | 참여자 상태, 채널 분리, `@CaseCopilot` 호출 규칙 |
| `05_existing_project_reuse_catalog.md` | 기존 Frontend·Backend 파일별 재활용 판단 |

## 4. MVP 완료 범위

### 고객

- Case 진입 및 현재 상태 확인
- Customer Agent와 텍스트 대화
- 질문 카드 응답
- 고객 답변의 Backend 저장
- 긴급 안전 행동 확인
- 은행 담당자 연결 상태 확인
- 기관 검증 진행상태 확인

### 은행

- Case 진입 및 핵심 상태 확인
- Bank Copilot과 내부 업무 대화
- 고객 대화 조회 및 메시지 전송
- 고객 질문 검토·전송
- 기관 검증 요청·상태 확인
- 은행 조치 기록
- Case Live Log 실시간 갱신
- 담당자 Takeover·AI Resume
- Case 종료와 FINAL 결과 확인

## 5. MVP에서 제외하거나 후순위로 두는 항목

- 실제 음성통화 Provider와 Streaming STT
- Voice Intelligence AI
- 운영용 FDS 외부 연동
- Vector DB와 전체 RAG Pipeline
- 복잡한 분석 Dashboard
- 고객에게 ML 점수·FDS 상세·내부 메모 노출
- 은행 화면의 상시 전체 보고서 패널
- 자동 지급정지·자동 신고 등 승인 없는 외부 조치
- 복수 담당자 협업·고급 권한관리

## 6. 데이터 원칙

```text
사용자 입력
  → 일반 Backend Command
  → 필요 시 AI 분석·구조화
  → Backend 검증·Version·Transaction
  → MySQL Entity 저장
  → case_events Append
  → 고객/은행 화면의 Chat Block 또는 Log Row 갱신
```

- MySQL이 Case 상태의 Single Source of Truth다.
- AI는 DB를 직접 수정하지 않는다.
- Frontend는 AI API를 직접 호출하지 않고 General API를 호출한다.
- AI 결과는 Backend 검증과 저장이 끝난 후 화면에 표시한다.
- 고객과 은행에는 같은 원본 데이터의 서로 다른 Projection을 제공한다.
