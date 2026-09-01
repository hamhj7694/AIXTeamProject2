# Contracts

서비스 구현과 분리된 요청·응답 Schema의 기준 위치다.

- `public_api/`: Frontend와 General API 사이의 공개 계약
- `ai_internal/`: General API와 AI API 사이의 내부 계약

계약 변경은 소비자와 제공자 양쪽 검토 후 반영한다. 생성 코드가 필요하면 계약을 원본으로 삼아 생성하고, 복제한 타입을 각 서비스에서 따로 관리하지 않는다.

