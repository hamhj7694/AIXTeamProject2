# ham 담당 작업 매핑

## 현재 상태

```text
WAITING — 다른 작업 완료 후 합류
```

합류 전에는 Backend 공통 파일을 선행 수정하지 않는다. 합류 시 `main` 최신 상태와 eom/lee의 Contract를 먼저 확인한다.

## 합류 후 배정 후보

| Task ID | 독립 작업 후보 | 선행 작업 | 충돌 방지 경계 |
|---|---|---|---|
| BE-02/03 | Case List·Detail·Bundle | INT-01 | analyze 수정 최소화 |
| BE-04 | Conversation·Question·Progress | AI-06/08 | 별도 conversation 모듈 |
| BE-05 | Verification·외부 Token | AI-07/12 | 별도 verification 모듈 |
| BE-06 | Report 저장·Section Version | AI-05/16 | 별도 report 모듈 |
| BE-07/08 | Action·Recovery·Official Data | Core DB | 별도 action/official 모듈 |
| BE-09 | Voice Session | Voice 결정 | 별도 voice 모듈 |
| RT-01 | SSE/WebSocket·Cursor | Event Schema | 별도 realtime 모듈 |

실제 담당 Task는 합류 시점에 완료되지 않은 항목 중 하나 이상을 선택해 `00_task_catalog.md`에서 확정한다.

## 권장 브랜치 예시

```text
ham/be-verification
ham/be-report-version
ham/rt-case-stream
ham/be-voice-session
```
