# B Part 문서 안내

이 문서는 B Part 문서의 공식 기준과 사용 우선순위를 안내한다.



## 공식 기준 문서

현재 B Part 구현 작업에서 공식 기준으로 사용하는 문서는 다음 3개다.

1. `B_PART_FOUNDATION.md`
2. `B_FEATURE_CONTRACT.md`
3. `B_CURRENT_PROGRESS.md`

각 역할:

### B_PART_FOUNDATION.md

거의 변하지 않는 B Part 원칙을 관리한다.

* B Part 역할
* AI 역할과 금지사항
* 의미 해석 원칙
* 개발 원칙
* Codex 작업 규칙

### B_FEATURE_CONTRACT.md

현재 구현의 기능 계약을 관리한다.

* Semantic State
* Question Eligibility
* Dynamic Follow-up
* Bank Copilot Grounding
* source/status/evidence 해석
* 각 계층 책임

### B_CURRENT_PROGRESS.md

현재 작업 상태만 관리한다.

* branch / HEAD
* 완료 단계
* 현재 작업
* 테스트 결과
* 남은 Integration Requirement

## drafts 규칙

`drafts/` 아래 문서는 다음 용도다.

* 과거 자료
* 미완성 자료
* 참고 보관 자료

별도 지시가 없는 한 Codex는 `drafts/` 문서를 읽거나 현재 구현 판단의 근거로 사용하지 않는다.

향후 B Part 작업은 기본적으로 공식 3개 문서를 기준으로 한다.
