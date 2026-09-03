# CONTEXT-FIRST CASE MVP_v2

보이스피싱 의심 상황을 하나의 Case로 연결하고, 고객 상담·은행 협업·기관 검증·보고서를 같은 데이터에서 운영하는 Chat-first MVP입니다.

## 정본 구조

```text
MVP_v2/
├─ frontend/   React + TypeScript + Vite
├─ backend/    General API + AI API + 계약 테스트
├─ docs/       기준 PRD와 실행 문서
└─ agents/     역할별 작업 지침
```

프론트엔드의 실제 화면 진입점은 `frontend/src/router/routes.tsx` 하나입니다.

| 경로 | 정본 화면 |
|---|---|
| `/` | 텍스트 진단 |
| `/cases` | 보이스피싱 Case 목록 |
| `/cases/:caseId` | Case 개요 |
| `/cases/:caseId/bank` | 은행 대응·협업 |
| `/cases/:caseId/customer` | 고객 안전 상담 |
| `/cases/:caseId/verify` | 기관 검증 |

은행·고객 Chat-first UI의 정본 컴포넌트는 `frontend/src/features/mvp-chat/`입니다. 같은 목적의 두 번째 화면이나 목데이터 전용 페이지를 새로 만들지 않습니다.

## 문서 기준

- 최상위 제품 기준: `docs/CONTEXT_FIRST_CASE_MVP_v2_PRD_2026-09-03.md`
- 작업 문서 색인: `docs/new_md/README.md`
- 실시간 세부 백로그: `docs/new_md/06_LIVE_DETAILED_IMPLEMENTATION_TODO.md`
- 데이터 계약: `docs/new_md/05_DATA_SCHEMA_AND_FLOW.md`

구현과 문서가 다르면 실제 검증된 코드 상태를 확인한 뒤, 상위 PRD의 의도에 맞춰 같은 작업에서 문서를 갱신합니다.

## 로컬 실행

### Backend

```powershell
cd MVP_v2/backend
python -m uvicorn general_api.app.main:app --host 127.0.0.1 --port 8100
python -m uvicorn ai_api.app.main:app --host 127.0.0.1 --port 8101
```

### Frontend

```powershell
cd MVP_v2/frontend
npm.cmd install
npm.cmd run dev
```

Frontend 개발 서버는 `http://127.0.0.1:5175`를 사용하며 `strictPort`로 중복 실행을 막습니다.

로컬 개발에서는 `dist`를 사용하지 않습니다. Vite가 `src`를 직접 제공하고, 같은 Origin의 `/api/*` 요청을 `http://127.0.0.1:8100`으로 전달합니다. `VITE_API_BASE_URL`은 비워둡니다. AI API는 Frontend가 직접 호출하지 않고 General API를 통해 사용합니다.

## 검증

```powershell
cd MVP_v2/frontend
npm.cmd run build

cd ../backend
python -m pytest
```

`npm.cmd run build`는 배포 가능 여부를 확인하는 검증 명령이라 실행 시 `dist`가 임시 생성됩니다. 로컬 개발 서버와 Backend 연결에는 필요하지 않으며 Git에도 포함하지 않습니다.

## 현재 제외 범위

음성 통화·녹음·실시간 STT·화자 분리·음성 분석은 후속 PRD 승인 전까지 구현 범위에서 제외합니다. 실제 API 키와 개인정보는 저장소에 커밋하지 않습니다.
