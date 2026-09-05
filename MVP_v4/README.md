# CSR | Case Share Room V4

독립 구축 중. Phase 0 기반 및 실제 local ML을 구현했다. Conversational/제품 E2E 완료 상태는 아니다.
작업 재개는 AGENTS.md와 docs/08_HANDOFF_CHECKPOINT.md를 따른다.
제품 기준은 docs/00_SOURCE_OF_TRUTH.md, docs/01_PRD.md.
모든 소스·모델·prompt·migration·배포 파일은 이 디렉터리 내부에 둔다.
실제 .env는 사용자가 생성/관리한다. 배포 방법은 docs/AWS_DEPLOYMENT.md.

## 현재 제공
- React 연결 확인 화면, General health `/api/v4/health`, AI health `/health`.
- MySQL 전용 V4 migration 001, 역할별 API process entrypoint.
- UUID secure/fallback 공통 helper, same-origin API 호출.
- 격리/env/UUID 검사, nginx/systemd/build 배포 자산.
- 승인 모델/adapter가 내부에 포함되며 실제 structured-feature ML 추론 및 `/ready/ml`을 제공한다.
- 제품 AI readiness는 Conversational/Intake 미구현으로 503. 상담/업무 기능은 아직 없다.

## 로컬 검증
V4 root에서 Python 3.11 venv를 생성하고 backend/requirements.txt를 설치한다.
`python -m pytest tests -q`, `python -m scripts.verify_self_contained`, `python -m scripts.verify_env_example`.
frontend에서 `npm ci`, `npm run typecheck`, `npm test`, `npm run build`.
두 API 실행은 V4 root에서 `python -m backend.scripts.start ai` 및 `python -m backend.scripts.start general`.
기본 포트 8100/8101이 사용 중이면 development 환경에서 AI_API_BASE_URL/AI_API_PORT/GENERAL_API_PORT를 대체 포트로 주입한다.
