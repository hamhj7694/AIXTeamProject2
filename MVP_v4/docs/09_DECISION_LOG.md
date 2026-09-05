# 결정 기록

## D-009 · 2026-09-06 · P1-001 · Shared Case schema baseline
Migration 002 creates the V4-owned Shared Case entity set and idempotency key record from the approved PRD.
The schema uses `tasks` as the only new bank-work source and deliberately creates no legacy `actions` table.
Schema constraints establish valid visibility, status, version and fingerprint boundaries; they do not substitute for server authorization, expected-version handling or projection enforcement in P1-002/P1-003.

## D-008 · 2026-09-06 · P0-006 · Phase 0 Gate 판정
승인 model artifact/adapter는 V4 내부에 물리 이식되었고, SHA-256/버전/feature order/threshold/guardrail을 검증했다.
V4 local model preflight, fresh copied V4 + fresh Python 3.11 venv isolation, disposable MySQL HTTP smoke, backend/frontend/audit gate가 통과했다.
따라서 Phase 0 foundation 및 local structured-feature ML gate는 PASS이며 P1 진입을 허용한다.
이는 전체 product readiness를 뜻하지 않는다. `/ready`는 Conversational/Intake 미구현을 명시하는 503이며 P2/P5/P7 최종 standalone/E2E gate는 별도다.

## D-007 · 2026-09-06 · P0-005 · Phase 0 AI 검증 공백 정합화
코드상 AI API는 liveness만 제공하고 readiness는 AI_ENGINE_NOT_PORTED=503이다.
따라서 scaffold 테스트 성공만으로 Phase 0 전체 완료로 표시하지 않는다.
P0-006을 추가하여 승인 모델/adapter를 V4에 먼저 이식하고 실제 load/predict/health preflight를 검증한다.
P2-001은 이식된 모델을 다시 복제하지 않고 intake adapter에 연결한다. 제품 결정 변경은 없다.

## D-006 · 2026-09-06 · P0-005 · Gate와 배포 검증 범위
Phase 0 scaffold gate는 liveness/adapter/독립 migration/설치/build/audit/회귀를 검증한다.
AI 실추론 readiness는 P2/P5에 예정된 이식 전이므로 503을 명시하며 완성 Phase 0 AI 엔진 gate로 대체하지 않는다.
공식기관 RAG gap은 새 verified corpus/contract가 필요한 P5-002 업무로 유지한다. 사용자가 별도 원본을 제공하지 않은 상태다.
실제 Ubuntu/systemd/nginx 및 최종 standalone/Scenario A+B는 미검증으로 남긴다.
requirements는 현재 설치된 transitive 버전까지 고정했다. Linux clean install은 별도 gate로 검증해야 한다.

## D-005 · 2026-09-06 · P0-004 · Frontend baseline
React 19.1.1, TypeScript 5.9.2, Node >=22.18(type stripping 기반 UUID/API unit tests), Vite 7.3.6.
초기 Vite 7.1.5의 online audit high 1건 때문에 공식 registry가 제시한 7.3.6으로 고정(갱신 후 0).
Vite envDir=false로 실제 env 자동 탐색을 막고 proxy 주소는 process environment에서만 사용한다.
브라우저 bundle은 /api만 사용한다. 미구현 상담 UI는 완료 기능처럼 만들지 않는다.

## D-004 · 2026-09-06 · P0-003 · 로컬 포트 충돌
기존 프로세스가 8100/8101을 점유한다(netstat 확인). 해당 프로세스는 변경/종료하지 않는다.
로컬 test/development는 loopback 대체 포트를 설정할 수 있다. production은 AI 8101을 검증하고 배포 자산은 General 8100/AI 8101 고정.
Phase 0 실제 HTTP smoke는 18100/18101을 사용한다. AWS 고정 포트 실환경 검증은 최종 gate에 남긴다.

## D-001 · 2026-09-06 · P0-001 · 재사용 표현 충돌
Master §0.8 및 PRD §30의 기존/외부 AI 서비스 재사용 표현보다 직접 사용자 요청 및 Hard Runtime Isolation을 우선한다.
V3 AI는 read-only 분석 후 필요한 파일을 V4에 실제 이식한다. V3 API runtime 호출은 허용하지 않는다.

## D-002 · 2026-09-06 · P0-001 · 문서 경로/버전 충돌
Source 문서의 PRD v1.2 표기는 과거 참조다. 이번 승인 원본은 V1.5이며 docs/01_PRD.md로 보존한다.
PRD §30의 예전 문서 번호보다 사용자 요청/Durable Continuation의 00–09 번호를 따른다.
원본 4개는 docs/source에 그대로 보존한다. 직접 사용자 요청은 모든 첨부 문서보다 우선한다.

## D-003 · 2026-09-06 · P0-001 · 기존 변경 보호
작업 시작 시 V3 및 발표 자료에 기존 staged/unstaged 변경이 있었다. V4만 작성하며 기존 index/worktree를 유지한다.
V3 지침의 과거 문서 재열람/수정 규칙은 이번 V3 read-only AI 경계 분석에 적용하지 않는다(직접 사용자 제한 우선).
