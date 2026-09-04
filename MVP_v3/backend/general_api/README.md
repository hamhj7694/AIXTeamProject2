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

MySQL `csr` 스키마와 AI API를 먼저 준비한 뒤 별도 터미널에서 실행한다.

```powershell
cd MVP_v3/backend
python -m uvicorn general_api.app.main:app --port 8100 --reload
```

환경변수는 `MVP_v3/.env`에서 자동으로 읽는다. 별도의
`MVP_v3/backend/.env`를 만들거나 터미널마다 다시 입력할 필요가 없다.

MVP_v3 런타임 Repository는 MySQL만 허용한다. 시작 시 DB 연결을 검사하며 `/health`에서도 MySQL에 `SELECT 1`을 실행한다. 단위 테스트는 Repository 선택 환경변수를 사용하지 않고 테스트용 메모리 구현을 직접 주입한다.
