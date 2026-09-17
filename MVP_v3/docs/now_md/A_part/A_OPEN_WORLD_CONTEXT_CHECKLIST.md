# Open-world Context Observation 구현 체크리스트

작성일: 2026-09-17

- [x] 정형 Fact 계약과 별도로 `UNMAPPED` 확장 관찰 계약 추가
- [x] 미분류 관찰의 비식별 lexical code·turn·상태·신뢰도 보존
- [x] `case_context_observations` additive 저장 테이블 및 멱등 저장 경로 추가
- [x] 직원 전용 `분류 대기 · 기타 관찰` 패널 lane 추가
- [x] 고객 projection에는 미분류 관찰을 노출하지 않음
- [x] 새 도메인 키워드 보존 회귀 테스트 추가
- [ ] 직원의 관찰 채택/기각 및 새 semantic key 승격 API
- [ ] 요약·질문·Copilot 입력에 관찰 상태/provenance 전달
- [ ] 자동 폐기 0·매핑률·projection 보존율 내부 KPI 리포트
