# CSR 프로젝트 테스트 허브

이 문서는 저장소의 테스트 주제를 한눈에 찾는 단일 시작점이다. 새로운 독립 평가 주제를 추가할 때 이 표에 한 줄을 추가하고, 주제 폴더에는 사람이 먼저 읽을 문서 하나를 둔다.

## 현재 테스트 주제

| 테스트 주제 | 확인 범위 | 상태 | 시작 문서 |
|---|---|---|---|
| LLM Context Test | 원문→LLM Feature 추출→맥락 재구성→Case 저장 직전 구조와 개선 버전 비교 | Baseline v1 보존 | [`context_test/00_START_HERE.md`](context_test/00_START_HERE.md) |

기존에 나뉘어 있던 `context_reconstruction`과 `context_pipeline_evaluation`의 핵심 기준 자료는 `context_test` 하나로 통합했다.

## 새 주제 추가 규칙

1. `tests/<test_topic>/`처럼 목적이 드러나는 폴더를 만든다.
2. `_TOPIC_TEMPLATE/00_START_HERE_TEMPLATE.md`를 참고해 사람용 시작 문서 하나를 작성한다.
3. 작은 테스트는 불필요한 하위 폴더를 만들지 않는다.
4. 기존 production test는 import와 CI를 깨뜨리지 않도록 코드 가까이에 유지하고 이 허브에서 연결한다.
5. 실제 고객 데이터, 개인정보, API key, `.env`, 운영 DB dump를 fixture에 넣지 않는다.
6. baseline을 덮어쓰지 않고 dataset/evaluator/model/prompt/Git 조건이 같은 실행만 직접 비교한다.
7. 외부 유료 API와 production DB write는 기본 테스트에서 실행하지 않는다.
