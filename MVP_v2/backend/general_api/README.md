# General API

Frontend가 호출하는 유일한 공개 Backend API 영역이다. 인증·입력 검증, Case 상태와 DB transaction, AI API 조정, 실시간 이벤트 발행을 담당한다.

```text
app/
├─ core/          # 설정, 보안, 공통 오류 처리
├─ domains/       # 업무 도메인별 router/service/repository
└─ clients/       # AI API 등 외부 서비스 client
tests/            # 단위·통합 테스트
```


## 현재 실행

AI API를 8001 포트에서 먼저 실행한 뒤 별도 터미널에서 다음을 실행한다.

```powershell
cd 02_workspace/backend
$env:AI_API_BASE_URL = "http://127.0.0.1:8001"
python -m uvicorn general_api.app.main:app --port 8000 --reload
```

Frontend는 `VITE_API_BASE_URL=http://127.0.0.1:8000`을 사용한다. 기본값은 서버 재시작 시 초기화되는
메모리 Repository다. `CASE_REPOSITORY=mysql`을 설정하면 현재 구현된 MySQL Repository를 사용한다.
Core Case·Diagnosis·초기 LIVE Report Migration은 `migrations/001~003`에 있다. Message, Verification,
Action, 상태 PATCH, Realtime API는 아직 구현되지 않았다.
