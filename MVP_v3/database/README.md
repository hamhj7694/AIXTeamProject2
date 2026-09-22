# MySQL DB 운영·전체 구조 보기

## 바로 보는 표

- [DB_CATALOG.md](DB_CATALOG.md): 전체 테이블의 엔티티·역할·행 수·PK·FK, 모든 컬럼의 타입/NULL/기본값, 인덱스·CHECK·트리거.
- [DB_USAGE_AUDIT.md](DB_USAGE_AUDIT.md): 실제 REST/repository/frontend 사용처 분류와 제거·전환 판정.
- [API_CONTRACT_AUDIT.md](API_CONTRACT_AUDIT.md): Frontend 타입·호출, General API 계약, repository SQL, DB 컬럼의 의미 대조.
- [엔티티별 migration 목록](../backend/migrations/README.md): 파일별 소유 엔티티·변경·보존 원칙.
- [CURRENT_STATUS.md](../docs/CURRENT_STATUS.md): 적용 결과와 아직 남은 금액·중복·화면 문제.

표는 조회 시점의 스냅샷이며 실시간 DB 화면이 아니다. 개인정보·대화·계좌 값은 포함하지 않는다.

> 데모 범위 안내: `case_transactions`와 `송금 기록 조회`는 실제 은행·계좌 원장 API가 아니라 Case 분석, 고객·직원 채팅, 직원 입력으로 구성한 표시용 기록이다. 실제 확인 거래로 자동 승격하거나 `actual_loss_amount_krw`에 자동 합산하지 않는다.

`DB_USAGE_AUDIT.md`의 `[ ]` 항목은 아직 검증·승인되지 않은 후속 작업이다. `voice_sessions` 외부 소비자 확인, `case_context_projections` 캐시 TTL/재생성 정책, `messages.attachments_json` 제거는 서로 다른 단계이며 한 번에 삭제하지 않는다. 첨부 컬럼은 핫픽스 안정화와 구버전 클라이언트 확인이 끝난 마지막 계약 변경에서만 제거한다.

## 문서 읽는 순서

1. [`API_CONTRACT_AUDIT.md`](API_CONTRACT_AUDIT.md)에서 프론트엔드·백엔드·DB의 의미와 공개 계약이 일치하는지 확인한다.
2. [`DB_USAGE_AUDIT.md`](DB_USAGE_AUDIT.md)에서 각 테이블·컬럼·API의 실제 사용처와 유지/전환/제거 판정을 확인한다.
3. [`DB_CATALOG.md`](DB_CATALOG.md)에서 현재 DB의 테이블·컬럼·행 수·FK·트리거 스냅샷을 확인한다.
4. [`backend/migrations/README.md`](../backend/migrations/README.md)와 `manifest.json`에서 스키마 변경 파일의 엔티티 분류와 실행 순서를 확인한다.

계약이 확정되지 않은 상태에서 Catalog의 0행이나 컬럼 중복만 보고 DROP하지 않는다. 계약 → 사용처 → 실제 스냅샷 → migration 순서로 검토하고, 삭제는 백업·복원·회귀 검증을 통과한 별도 변경으로 진행한다.

## 신규 DB 초기화 — 단일 기준

SQL 기준은 `backend/migrations/manifest.json`에 등록된 엔티티별 SQL이다. 실행 순서와 DB 이력 파일명은 기존과 동일하며 `rollback/`은 자동 실행하지 않는다. `.env` 설정 후 저장소 루트에서:

```powershell
MVP_v3/.venv/Scripts/python.exe MVP_v3/backend/scripts/apply_migrations.py
```

runner는 DB가 없으면 생성하고 파일명 순으로 적용한다. 계정에는 DB 생성(신규일 때), 테이블·인덱스·제약·TRIGGER 변경 권한이 필요하다. 비밀번호는 `.env`에만 넣고 명령줄·문서·Git에는 넣지 않는다.

`01_mysql_csr_schema.sql`은 동일 migration 전체에서 생성하는 **빈 DB/Docker 전용 파생 파일**이다. 업무 데이터는 없으며 023 migration의 데모 직원 2명만 포함한다. 현재 001~026 전체 구조와 적용 이력을 포함하므로 baseline을 수작업으로 편집하지 않는다.

```powershell
# SQL을 추가한 개발자가 파생 파일 재생성
MVP_v3/.venv/Scripts/python.exe MVP_v3/backend/scripts/build_schema_bootstrap.py --write
# 변경 누락 확인; SQL 실행이나 DB 접속 없음
MVP_v3/.venv/Scripts/python.exe MVP_v3/backend/scripts/build_schema_bootstrap.py
```

기존 DB에 초기화 SQL을 SOURCE하지 않는다. Docker 초기화 또는 오류 시 중단하는 MySQL batch 방식만 사용하고 `--force`를 사용하지 않는다. 기존 DB에는 runner/검증된 복구 절차를 사용한다.

## 현재 DB 읽기 전용 점검·표 갱신

```powershell
MVP_v3/.venv/Scripts/python.exe MVP_v3/backend/scripts/inspect_database.py --output MVP_v3/backend/data/db-current.json
MVP_v3/.venv/Scripts/python.exe MVP_v3/backend/scripts/export_database_catalog.py
```

첫 명령은 정의·건수·FK 무결성·미적용 파일을 JSON으로 출력한다. 두 번째는 `DB_CATALOG.md`를 갱신한다. 업무 행/개인정보는 내보내지 않는다. 금액 후보 삭제·Fact 확정·실패 job 재시도는 수행하지 않는다.

문서 갱신 후에는 다음을 함께 확인한다.

- `DB_CATALOG.md`의 테이블·컬럼·행 수가 `information_schema`와 일치하는지
- `DB_USAGE_AUDIT.md`의 완료 체크(`[x]`)가 실제 명령·테스트 결과로 입증되는지
- `backend/migrations/README.md`와 `manifest.json`의 엔티티 폴더·실행 순서가 일치하는지

## 기존 DB 구조 정합화

먼저 General API를 중지하고 작업 중인 사용자가 없는지 확인한다. 읽기 트랜잭션도 DDL metadata lock을 잡을 수 있다. MySQL·AI·프론트 서버를 전부 종료할 필요는 없다.

```powershell
# 실DB에는 읽기만 수행. 격리 reference DB는 생성·제거함.
MVP_v3/.venv/Scripts/python.exe MVP_v3/backend/scripts/normalize_database.py
# 백업→격리 복원→변경 리허설→업무 행 해시 대조→실DB 적용
MVP_v3/.venv/Scripts/python.exe MVP_v3/backend/scripts/normalize_database.py --apply
```

범용 자동 수정기가 아니다. 검토된 거래 테이블 누락, 과거 직원 역할 길이/제약, 004~011 이력 누락만 처리한다. 다른 스키마 차이나 알 수 없는 이력이 있으면 중단한다. 008의 데이터 보완 효과도 검사한다.

- PATH에 `mysqldump`·`mysql`이 있어야 하며 격리 검증 DB 생성·제거 권한이 필요하다.
- 백업은 Git 제외 경로 `backend/data/backups/<UTC시각_식별자>/`에 둔다. 대화·고객정보를 포함하므로 로컬 접근을 제한하고 Git/공개 저장소에 업로드하지 않는다.
- 일부 단문 trigger 끝 세미콜론/버전 주석 조합의 mysqldump 복원 오류를 피하기 위해, 행을 먼저 dump하고 SHOW CREATE의 trigger 정의를 마지막에 별도 delimiter로 첨부한다. 복원 후 원래 구조·행 해시를 대조한다.
- `receipt.json`은 백업 경로·SHA256·적용 SQL·검증 기준선·전후 행 해시를 기록한다. 실패한 시도의 dump와 복원 검증에 성공한 백업을 혼동하지 않는다.
- 모든 테이블 타입·NULL·기본값·charset/collation·인덱스·FK/CHECK·트리거가 새 DB에서 전체 migration을 실행한 결과와 같아야 기준선을 등록한다.
- 기존 업무 행을 삭제/중복 정리/재확정하지 않는다. DDL 부분 적용 후 실패할 수 있으므로 재실행 때 현재 상태를 다시 검사한다.
- 검증 DB만 생성한 이름을 확인해 제거한다. 서비스 DB는 DROP/재생성하지 않는다.

성공 후 General API를 재시작하고 `/health`, `/api/cases/{case_id}/transactions`를 확인한다. SELECT 1 성공만으로 전체 스키마가 정상이라고 판정하지 않는다.

## 백업 복구 원칙

자동으로 서비스 DB에 덮어쓰지 않는다. 먼저 **별도로 만든 빈 DB**에 SQL을 복원하고 schema·건수·참조·업무 데이터를 검증한 뒤 서비스 전환 여부를 결정한다. 백업에는 DROP TABLE 문이 포함될 수 있으므로 기존 업무 DB에 직접 SOURCE하지 않는다. 다른 계정/서버로 복원할 때에는 trigger definer 권한도 확인한다.

## 테스트

```powershell
cd MVP_v3/backend
../.venv/Scripts/python.exe -m pytest general_api/tests/test_schema_normalization.py -q
```

MySQL 통합 테스트는 `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD` 환경변수가 있을 때 격리 임시 DB에서 실행한다. 서비스 DB에 테스트 데이터를 쓰지 않는다. GitHub의 `Database schema consistency` 작업은 실제 MySQL 초기화·정상화·재실행을 확인한다. 원격 Required Check 설정은 파일 변경만으로 바뀌지 않는다.
