# Contracts

서비스 구현과 분리된 요청·응답 Schema의 기준 위치다.

- `public_api/`: Frontend와 General API 사이의 공개 계약
- `ai_internal/`: General API와 AI API 사이의 내부 계약

계약 변경은 소비자와 제공자 양쪽 검토 후 반영한다. 생성 코드가 필요하면 계약을 원본으로 삼아 생성하고, 복제한 타입을 각 서비스에서 따로 관리하지 않는다.

## 현재 편집 책임

| 영역 | 최종 편집자 | 필수 Reviewer |
|---|---|---|
| `public_api/**` | A=eom | C=ham 소비자 Review, B=lee 영향 Review |
| `ai_internal/**` | B=lee | A=eom 소비자 Review |
| 공개·내부 DTO가 섞인 공통 파일 | Task별 1명 지정 | 영향받는 A/B/C |

`diagnosis.py`처럼 양쪽 DTO가 한 파일에 있는 기존 코드는 호환성을 유지하며 단계적으로 분리한다. 분리 전까지는 한쪽이 단독으로 Breaking Change를 반영하지 않는다.

