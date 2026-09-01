# General API

Frontend가 호출하는 유일한 공개 Backend API 영역이다. 인증·입력 검증, Case 상태와 DB transaction, AI API 조정, 실시간 이벤트 발행을 담당한다.

```text
app/
├─ core/          # 설정, 보안, 공통 오류 처리
├─ domains/       # 업무 도메인별 router/service/repository
└─ clients/       # AI API 등 외부 서비스 client
tests/            # 단위·통합 테스트
```

