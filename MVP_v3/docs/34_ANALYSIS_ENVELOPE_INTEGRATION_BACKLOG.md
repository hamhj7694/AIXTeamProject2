# Analysis Envelope 데모 완성 백로그

작성일: 2026-09-19
선행 계약: `33_ANALYSIS_ENVELOPE_FREEZE_CONTRACT.md`
제품 범위: 실제 통신사·온디바이스·ASAP/FDS 연동이 아닌, 해당 경계를 모사하는 CSR 데모
통합 기준 브랜치: `integration/dev2-with-ham3-frontend`

## 1. 범위 결정

이번 프로젝트는 실제 외부 분석 사업자와 연결하거나 그 연동을 검증하지 않는다.

```text
데모 입력
→ 데모 분석기에서 구조화 AnalysisEnvelope 생성
→ CSR AI API에서 검증·GPT 문장화
→ General API에서 Case 생성·저장
→ Frontend에서 업무용 결과 표시
```

- `/api/cases/analyze`가 위 전체 데모 흐름을 시작하며 Case는 이미 생성된다.
- `/ai/analyze/signals`는 저장 원문을 다시 받지 않는 지원 AI 분석 경계를 검증하기 위한 내부 분석 경계다.
- 외부 사업자가 Envelope를 직접 제출하는 General API endpoint는 데모 완료 조건이 아니다.
- 통신사 인증, mTLS, 외부 webhook, 실제 기기 SDK, ASAP/FDS 연결은 명시적으로 범위 밖이다.
- Vector DB와 embedding 파이프라인은 구현하지 않는다. MySQL 구조화 데이터, Case Snapshot JSON, 기존 Case-local TF-IDF 검색을 사용한다.
- UI와 문서에서 실제 외부 시스템이 연결된 것처럼 표현하지 않는다.

## 2. 현재 완료된 기준선

- strict `AnalysisEnvelope`와 참조 무결성 검증
- 데모 입력 → Envelope → 동일 분석 코어 → Case 생성
- 동일 `client_request_id`의 Case 생성 멱등성
- 데모 Case 입력 원문 보관과 지원 AI의 privacy-safe projection
- 화자·행위자·대상자·보고자, 기관·인물·관계·시간 metadata 보존
- GPT 기반 정황 문장·사건 초기 요약과 실패 시 명시적 중단
- 주요 정황 카드와 `추가 구조화 정보` 상세 영역
- Atom, Relation, Episode, Action Group, Entity, Mention, 미매핑 Observation 표시
- Case별·공개 범위별 TF-IDF 검색과 구조화 데이터 우선 원칙
- PR용 GitHub Actions 회귀 테스트·Frontend build·diff check

## 3. P0 — 데모 기준선 보호

### P0-1. GitHub Required Check 활성화

저장소에는 `.github/workflows/analysis-envelope-guard.yml`이 있다. 현재 최신 작업을 모으는 `integration/dev2-with-ham3-frontend` 브랜치의 필수 검사로 다음 job을 지정한다.

- `Envelope contract and Case regression`
- `Frontend typecheck and build`
- `Diff integrity`

추가 설정:

- `integration/dev2-with-ham3-frontend`에 Pull Request 요구
- 필수 검사가 통과하기 전 병합 금지
- force push와 branch deletion 제한
- 가능하면 1명 이상의 리뷰 승인 요구

워크플로 파일만 추가해도 원격 Branch Protection은 자동 활성화되지 않는다. 저장소 관리자 권한으로 `integration/dev2-with-ham3-frontend`에 GitHub 설정을 한 번 적용해야 한다.

### P0-2. 데모 E2E 확인

- 보이스피싱 샘플 입력 후 Case가 한 번만 생성되는지 확인
- 생성된 Case 재조회 시 원문이 없고 구조화 diagnosis가 복원되는지 확인
- 결과 패널에서 주요 카드와 추가 구조화 정보가 모두 표시되는지 확인
- 40개 narrative와 다수 구조화 객체에서도 결과 패널 내부만 스크롤되는지 확인
- 정상 통화는 `NO_CASE`이며 사건 목록에 저장되지 않는지 확인
- GPT 장애 시 HTTP 실패 응답이 반환되고 Case가 생성되지 않는지 확인

### P0-3. 역할·시간 fixture 확대

- `엄마, 나 스마트폰 고장 났어`에서 호칭 대상을 화자로 오인하지 않음
- 고객이 의심 인물의 주장을 재진술할 때 reporter와 actor를 구분
- 정확한 은행·검찰·법원·경찰서 명칭과 주장 직책 보존
- 송금 요구와 고객의 실제 송금 진술 분리
- `15시까지`와 `약 2시간 남음`의 기준 시각 관계 검증
- 기준 시각이 없으면 남은 시간을 임의 생성하지 않음

## 4. P1 — GPT 품질과 화면 완성도

- 동일 privacy-safe Envelope fixture로 prompt/model 품질 비교
- 역할 귀속, 세부 명칭 보존, 누락, 환각, 중복 문장 평가
- 토큰 잘림·latency·Case당 비용 측정
- 긴 결과와 모바일 1열 UI 수동 검증
- 구조화 정보 label 사전 확대 및 직원용 표현 개선
- 접근성: 키보드로 상세 영역 열기, 스크린리더 제목·개수 안내 확인

모델이 바뀌어도 Envelope의 역할·턴·Atom·Relation을 수정할 권한은 없다.

## 5. 범위 밖

아래 항목은 이번 데모에서 구현하거나 완료로 주장하지 않는다.

- 실제 통신사·기기 제조사·온디바이스 SDK 연결
- 실제 ASAP/FDS 송수신
- 외부 기관 service identity, mTLS, webhook 서명과 replay 방지
- 실계좌·고객정보·금융기관 운영 데이터 연동
- 외부 시스템 가용성·성능·보안 인증
- Vector DB, embedding 생성·저장·재색인 파이프라인

향후 실제 사업화 단계에서 별도 프로젝트와 보안·법무 검토로 다룬다.

## 6. 다음 작업 순서

```text
1. 팀원 작업 브랜치에서 `integration/dev2-with-ham3-frontend`로 PR 생성
2. 이 브랜치의 Branch Protection에서 3개 check를 필수로 지정
3. 데모 브라우저 E2E와 `case_inputs` 원문 보관·지원 AI 입력 제외 확인
4. 역할·시간·구체 명칭 fixture 확대
5. GPT 품질·비용 측정과 문장 개선
```

완료하지 않은 실제 외부 연동은 문서·발표·UI에서 구현된 것으로 표현하지 않는다.
