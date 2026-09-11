# CSR Judge Explorer metadata scanner

이 도구는 Judge Web에 표시할 CURRENT 기술 사실을 `MVP_v3` 코드에서 정적으로 생성한다.

## 안전 경계

- `.env`, 운영 DB, 고객 데이터와 업로드 파일을 읽지 않는다.
- FastAPI 앱과 Backend process를 실행하거나 import하지 않는다.
- ML artifact는 파일 존재 여부와 SHA-256만 확인하고 역직렬화하지 않는다.
- 출력은 `frontend/public/judge/data/auto/`에만 생성한다.

## 실행

`MVP_v3`에서 프로젝트 전용 Python으로 실행한다.

```powershell
./.venv/Scripts/python.exe tools/judge_explorer/generate_metadata.py
./.venv/Scripts/python.exe -m unittest discover -s tools/judge_explorer/tests -v
```

Python interpreter가 없는 제한된 검증 환경에서는 동일한 read-only 규칙을 적용한
표준 Node.js fallback을 사용할 수 있다. 외부 package를 사용하지 않는다.

```powershell
node tools/judge_explorer/generate_metadata.mjs
node --test tools/judge_explorer/tests/*.mjs
```

AUTO manifest의 hash는 실행 시각과 Git 상태를 제외한 canonical metadata만 대상으로 한다.
