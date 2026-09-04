# CONTEXT-FIRST CASE Frontend V3

V3는 은행 담당자가 하나의 Shared Case에서 사건 맥락, 고객 대화, 기관 확인과 대응 업무를 처리하는 별도 Frontend다. `MVP_v2` UI를 덮어쓰지 않으며, 현재 검증된 `MVP_v2/backend`의 General API와 AI API 계약을 사용한다.

## 실행 구조

```text
Browser :5176
  └─ /api proxy → General API :8100
                       ├─ SQLite/MySQL Repository
                       └─ AI API :8101
```

Frontend가 AI API를 직접 호출하지 않는다. General API가 필요한 Case Context만 AI API에 전달한다.

## 실행

Backend와 AI API는 `MVP_v2/backend`에서 실행한다.

```powershell
cd MVP_v2/backend
$env:AI_API_BASE_URL='http://127.0.0.1:8101'
python -m uvicorn ai_api.app.main:app --host 127.0.0.1 --port 8101
python -m uvicorn general_api.app.main:app --host 127.0.0.1 --port 8100
```

V3 Frontend:

```powershell
cd MVP_v3/frontend
npm.cmd install
npm.cmd run dev
```

접속: `http://127.0.0.1:5176`

## 검증

```powershell
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
```

## 핵심 문서

- 제품 요구사항: `PRD.md`
- 고객용 제품 요구사항: `CUSTOMER_PRD.md`
- 개발 매핑: `docs/01_WORK_MAPPING.md`
- 실시간 초세밀 TODO: `docs/02_DETAILED_TODO.md`
- 구현·검증·인수인계 현황: `docs/03_IMPLEMENTATION_STATUS.md`

## 안전 경계

- 고객 공개 메시지와 은행 내부 기록의 대상을 입력 전에 명확히 선택한다.
- AI 결과는 분석·권고이며 금융기관의 최종 결정으로 표시하지 않는다.
- Action 등록은 실제 지급정지나 신고 실행이 아니라 담당 업무 기록이다.
- 5초 polling은 Case/Bundle/Fact만 갱신한다. AI Brief endpoint는 반복 polling하지 않는다.
- 실제 인증/RBAC와 SSE/WebSocket은 현재 Backend 후속 과제다.
