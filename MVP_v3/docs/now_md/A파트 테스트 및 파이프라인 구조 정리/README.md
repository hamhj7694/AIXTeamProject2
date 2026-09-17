# A파트 테스트 및 파이프라인 구조 정리

6.5단계에서 생성하는 내부 평가 자료를 모아두는 폴더다.
운영 웹 화면이나 public API의 응답 자료를 저장하는 곳이 아니다.

## 보관 대상

- `A_6_5_TEST_AND_PIPELINE_CHECKLIST.md`: 실행 체크리스트
- `fixtures/`: 원문 대신 privacy-safe 입력 식별자와 annotation 계약
- `schemas/`: 구조 JSON·지표 JSON schema
- `reports/`: 날짜별 평가 JSON 및 요약표
- `diagrams/`: pipeline data-flow, lineage, metric funnel 도표
- `commands/`: 재현 명령과 실행 환경 기록

## 금지 대상

통화 원문, raw transcript, 전체 evidence span, 전화번호·계좌번호·OTP·PIN·비밀번호 등 민감 literal은 저장하지 않는다.
