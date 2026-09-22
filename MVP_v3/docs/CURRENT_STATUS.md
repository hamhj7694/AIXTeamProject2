# MVP v3 현재 구현 상태

최종 갱신: 2026-09-22 (첨부파일 데모 범위 제외·송금 기록 조회 명칭 정리)
역할: 개발·점검 작업을 시작할 때 확인하는 단일 최신 상태 문서

> 실제 코드와 최신 테스트 결과가 이 문서보다 우선한다. 완료하지 않은 기능은 구현된 것처럼 표시하지 않는다.

## 송금 기록 조회 — 데모 정책

- 실제 은행·계좌 원장 API는 연결하지 않는다. `송금 기록 조회`는 Case 최초 분석, 고객·직원 채팅, 직원의 데모 확인 입력으로 수집된 정보를 보여주는 화면이다.
- 분석에서 언급된 금액이나 고객의 송금 진술은 은행 확인 거래로 자동 승격하지 않는다. `case_transactions`는 표시용 기록 목록이며 `cases.actual_loss_amount_krw`는 별도의 사건 요약값이다.
- 화면과 API는 `거래 없음`, `조회 실패`, `미확인`, `송금 진술`, `데모 확인`을 구분해야 하며, 0건을 피해금액 0원으로 표시하지 않는다.
- 각 기록에는 출처·확인 상태·방향(`TRANSFER_OUT`/`RETURN_IN` 등)을 보존한다. 실제 금융기관 확인이 완료된 것처럼 표현하지 않는다.
- 상세 결정과 미완료 회귀 항목은 [`DB_USAGE_AUDIT.md`](../database/DB_USAGE_AUDIT.md)와 [`API_CONTRACT_AUDIT.md`](../database/API_CONTRACT_AUDIT.md)에 고정했다.

## 2026-09-21 DB 스키마 정상화 — 적용 완료

작업 브랜치: `hotfix/db-schema-normalization` (`merge-case2`에서 생성). 기존 미커밋 프론트 변경사항을 보존했다. 커밋·원격 push·PR 생성은 하지 않았다.

| 항목 | 현재 확인 결과 |
|---|---|
| 전체 구조 | 32개 테이블(028 legacy Fact 폐기 후), 356개 컬럼, 35개 FK, 29개 트리거 |
| 구조 일치 | 전체 migration을 빈 MySQL DB에 적용한 기준과 실제 `csr`의 타입·NULL·기본값·collation·인덱스·FK/CHECK·트리거 비교 차이 0건 |
| 신규 적용 | `021_create_case_transactions.sql`, `024_bank_staff_role_schema_alignment.sql` |
| 직원 역할 | VARCHAR(24)·3종 CHECK → VARCHAR(32)·5종 CHECK; 기존 배정 값 유지 |
| 이력 복구 | 004~011의 미기록 9건은 실제 구조와 008 데이터 보완 효과 검증 후 기준선으로 기록. 기존 ALTER 재실행 없음 |
| 현재 파일 적용 상태 | 정방향 SQL 26개와 과거 `021_bank_staff_assignment_fields.sql` 이력 1건 적용. 전체 `schema_migrations` 27건 |
| 데이터 보존 | 변경 전후 기존 업무 테이블 34개의 모든 행 해시 일치. Case 17건·메시지 194건·V2 Fact 258건 유지 |
| 신규 거래 테이블 | 생성 완료, 0건. 분석 금액 후보를 임의 거래로 만들지 않음 |
| 백업 검증 | SQL 백업을 별도 DB에 복원해 구조·행 해시 검증하고 그 복원본에서 변경 리허설 통과 |
| 서버 확인 | General API의 DDL 잠금을 해제하기 위해 잠시 중지 후 재실행. `/health` 정상, VP-15 거래 조회 HTTP 200·빈 목록 |

복원 검증 성공 백업은 로컬 Git 제외 경로 `backend/data/backups/20260921T084652Z_3fcb8401/csr.sql`, 검증 영수증은 같은 폴더 `receipt.json`이다. 개인정보를 포함하므로 Git에 올리지 않는다. 초기 복원 검증 실패 시도의 dump들과 혼동하지 않는다. 작업 중 생성한 격리 검증 DB는 제거했으며 서비스 DB는 삭제/재생성하지 않았다.

### 원문 보관 경계 정정

- 데모 분석 입력은 `case_inputs.input_text`에 `VOICE_TRANSCRIPT`로 보관한다. 원문은 최초 분석 결과 화면에서만 일시적으로 표시하고, Case read/list/bundle·Case Room 재진입·지원 AI에는 반환하지 않는다. 기존 17건은 이전 구현이 빈 값을 기록했기 때문에 소급 복원하지 않는다.
- 분석 계층은 화자·행위자·관계·정황을 추출하기 위해 분석 시점에 원문을 읽는다. 이후 Case Copilot·Context Snapshot·지원 AI에는 저장 원문을 전달하지 않고 구조화 diagnosis/Envelope만 전달한다.
- 다중 segment 방식의 레거시 `voice-sessions/.../transcript` URL은 중복 저장 방지와 API 경계 유지를 위해 410이다. 이는 데모 분석 입력의 단일 `case_inputs` 보관과 별개다.
- 원문 보관·지원 AI 비접근 회귀 테스트: General API **40 passed**, Frontend typecheck **통과**.

### 유지보수 변경

- `normalize_database.py`: 기본 계획 조회, 명시적 `--apply`에서 백업·격리 복원·스키마 대조·데이터 보존 검증 후 알려진 차이만 수정. 알 수 없는 차이는 중단.
- `inspect_database.py` / `export_database_catalog.py`: 실제 DB를 읽어 개인정보 없이 구조·행 수·무결성을 출력하고 [전체 DB 표](../database/DB_CATALOG.md)를 갱신.
- [엔티티별 migrations](../backend/migrations/README.md): 정방향 29개와 rollback 7개를 실제 엔티티 하위 폴더로 이동했다. SQL 내용·파일명·DB 이력은 유지하고 실행 순서는 `manifest.json`으로 고정한다. 복수 엔티티 변경 이력은 `shared/`에 보존한다. transcript·첨부 테이블·legacy `case_facts` 폐기 migration 및 410 API 경계를 추가했다.
- `database/01_mysql_csr_schema.sql`은 `build_schema_bootstrap.py`로 전체 migration에서 생성한다. 빈 DB/Docker 경로와 runner 경로가 같은 구조·이력을 만드는 것을 검증했다.
- Docker Compose에서 이미 bootstrap에 포함된 014 SQL의 별도 중복 마운트를 제거했다. 실제 Docker 컨테이너 실행은 이번 검증 범위 밖이다.
- 현재 코드에서 사용하지 않는 `case_number_sequences` 생성 지시와 오래된 테스트 기대 목록을 수정했다. Case 번호 할당 업무 로직 자체는 변경하지 않았다.
- GitHub workflow에 bootstrap 단위검사와 별도 MySQL `Database schema consistency` job을 추가했다. 원격 실행/Required Check 설정은 미확인·미변경이다.

### 이번 검증과 남은 항목

- 엔티티 폴더 재편 후 SQL SHA-256 동일 확인. 레거시 다중 transcript API는 SQL 025로 폐기했고, 026에서 빈 첨부 테이블, 027/028에서 legacy `case_facts`를 V2 복사 후 폐기했다. 데모 분석 입력 원문은 `case_inputs.input_text`에 `VOICE_TRANSCRIPT`로 보관한다. 이 원문은 최초 분석 결과 화면에서만 일시적으로 확인하고 Case read/list/bundle·Case Copilot·Context AI에는 반환하지 않는다. 로컬 `csr`는 현재 32개 테이블·356개 컬럼·35개 FK이며 `transcript_segments`, 첨부 테이블, `case_facts`는 제거됐다.
- 테이블 축소는 중복 transcript segment·첨부파일·legacy Fact 경로까지 처리했다. `case_context_facts_v2`가 유일한 Fact 원장이고 `/facts`는 V2 adapter다. `case_inputs.input_text`는 원장에만 보관하며 최초 분석 결과 화면에서만 transient로 표시한다. `analysis_segments`·`context_features`·Atom/Relation/Signal 테이블에는 저장 경로가 있으나 주요 조회는 `diagnosis_json`에 의존하므로 단일 원본 정리는 별도 작업이다. 356개 컬럼의 사용처·중복·삭제 위험은 `database/DB_USAGE_AUDIT.md`에 분류했다.
- 신규 schema 테스트: **8 passed, 4 subtests passed**. 빈 DB·bootstrap 일치, 과거 DB 변경, 사용자 편집 보존, 역할 제약, 재실행, 초기화 재적용 거부를 검증했다.
- 기존 MySQL repository 통합: **15 passed, 1 failed**. 실패는 `ContextProjectionRepository.claim`에서 MySQL DATETIME의 naive 값과 UTC aware `now`를 비교하는 기존 런타임 오류다. 스키마 오류로 숨기거나 테스트를 제외하지 않았으며 후속 수정 대상이다.
- Case 생성/조회 선택 회귀: **30 passed, 3 subtests passed**.
- Frontend typecheck 통과, Vite production build **1,473 modules 통과**. 첫 빌드는 sandbox의 상위 경로 접근 제한으로 실패해 권한 승인 후 동일 명령을 재실행했다.
- 금액 후보 중첩·사건 식별·합계 오류, 거래 조회 실패/mock 표시, 과거 추출 실패 job은 아직 미수정이다. 데이터 삭제·자동 CONFIRMED 전환·실제 외부 금융 연동은 하지 않았다.

## 2026-09-21 로컬 DB 점검 — 수정 전 상태

점검 대상은 `MVP_v3/.env`로 연결되는 MySQL `csr`(8.0.46), 기준 시각은 2026-09-21 17:24 KST다. 읽기 전용 일관 스냅샷으로 35개 테이블의 행 수, 현재 migration과의 테이블·컬럼 대조, FK·논리 참조, 중복 후보, 금액·처리 상태를 검사했다. DB 데이터·스키마·migration 기록은 변경하지 않았다. 원격 배포 DB, 백업 복구, 전체 로그·자유서술 필드의 개인정보 전수 검사까지 완료했다는 뜻은 아니다.

### 실제 저장 현황

| 항목 | 점검 결과 |
|---|---|
| Case / 대화 메시지 | 17건 / 194건 |
| 구조화 정황 / 정황 관계 | `case_semantic_atoms` 129건 / `case_semantic_relations` 16건 |
| 현재 사실 후보 / 기존 사실 테이블 | `case_context_facts_v2` 264건 / `case_facts` 제거 완료 |
| 금액 사실 후보 | 34건. 요구·송금 진술 등을 담은 분석 정보이며 공식 거래 내역이 아님 |
| 요약 피해금액 | `cases.actual_loss_amount_krw`는 17건 모두 `NULL`. 여러 송금 행을 저장하는 컬럼이 아니며 확인한 코드 경로에서 Fact/거래의 자동 합산·동기화는 없음 |
| 거래 상세 테이블 | `case_transactions` 없음. 현재 브랜치의 `021_create_case_transactions.sql`도 적용 기록 없음 |
| 채팅 정보 추출 작업 | 완료 133건, 실패 1건. 대기·처리 중 작업 없음 |

### 수정이 필요한 사항 — 아직 미수정

1. **실제 DB와 migration 기록 불일치**: 004~011 구간 9개 파일은 적용 기록이 없지만 해당 테이블·추가 컬럼 등 검사한 구조는 존재한다. 거래 migration까지 포함하면 현재 파일 중 미기록은 10개다. 반대로 DB에는 현재 브랜치에 없는 `021_bank_staff_assignment_fields.sql` 기록이 있다. 전체 migration을 무조건 재실행하지 말고 백업 후 실제 정의를 대조해 이력을 정합화해야 한다. 단순 파일명 변경이나 적용 기록 삽입만으로 해결됐다고 판단하지 않는다.
2. **조회 실패와 거래 없음이 구별되지 않음**: CaseRoom은 transactions 요청 실패를 경고 목록에 넣지 않고, `cardData.ts`는 데이터가 비면 `정보 없음 / 0원` 임시 행을 표시한다. 따라서 이를 실제 0원 거래로 해석하면 안 된다. 계좌·예금주와 FDS 신고 3건·의심·지급정지 가능 역시 이 파일의 mock 값이다. 실제 기관 API 연동은 계속 데모 범위 밖으로 두되, 데모값·조회 실패·데이터 없음을 구분해야 한다.
3. **동일 근거의 후보 중첩**: 동일 Case·분류·근거 기준으로 58개 그룹이 복수 후보(첫 행 외 70행)를 갖는다. 그중 금액은 같은 근거·요구 금액에 2개 후보가 있는 9개 그룹이다. JSON 전체가 동일한 중복은 0건이며, 일반 요약 후보와 Atom 상세 후보를 모두 생성하는 `seed_initial_context_facts` 경로 때문에 값의 상세도는 다르다. 서로 다른 정보일 수 있는 전체 70행을 삭제 대상으로 간주하지 말고, 특히 금액은 사건 식별자를 기준으로 통합·대체 정책을 정해야 한다.
4. **금액 후보의 출처·행동 상태 부족**: 34개 금액 후보 중 방향 정보가 없는 항목 25건, 금액 사건 식별자가 없는 항목 27건이다. VP-16에서는 `MENTIONED`/`PLANNED` 정황도 `transfer.actual.amount` 후보로 저장되어 있다. 모두 확인 전 상태이므로 실제 송금으로 확정된 것은 아니다. 요구·예정·송금 진술·은행 확인 거래를 구분해야 한다.
5. **합계 및 중복 제거 결함 재현**: DB에 저장하지 않은 합성 입력으로 현재 함수들을 실행했다. 채팅 추출기에 `첫 번째로 300만 원 송금했습니다. 두 번째로 300만 원 송금했습니다.`를 주면 송금액 후보가 1개만 나온다. 서로 다른 사건 ID를 가진 확인 완료 300만 원 송금 2건도 요약에서 1건/300만 원으로 합쳐진다. 송금 300만 원과 반환 100만 원은 요약에서 `실제 이체 2건 · 합계 4,000,000원`으로 더해진다. 추출기의 표시문구 기반 중복 제거, 요약의 표시문구 기반 통합 및 방향 무시 합계를 수정해야 한다. 현재 실DB에는 `CONFIRMED` Fact가 없어 이는 저장된 확정 합계 오류가 아니라 오프라인 재현 결과다.
6. **과거 추출 실패 1건**: VP-1 작업 1건이 3회 시도 후 `FAILED`로 남아 있다. 기록된 사유는 실제 LLM provider 응답이 아니라서 사실을 저장하지 않았다는 것이다. 원인과 현재 실행 경로를 확인한 후 재시도 여부를 정해야 하며, 이번 점검에서 재실행하지 않았다.
7. **검토 완료 기록 없음**: V2 258건과 legacy 6건 모두 확인 전이다. 직원이 채팅에서 확인했다고 쓰는 것과 Fact의 공식 `CONFIRMED` 전환은 별개다. 이번 점검에서 임의로 확인 완료 처리하지 않았다.

### 정상 확인 및 오탐 제외

- 선언된 FK 40개에서 끊어진 참조 0건. Case 연결, Atom 관계 16건, Fact 근거 258개, 질문·답변 메시지 연결도 검사 범위에서 끊어진 참조가 없다. `QUESTION_ANSWER` 근거 ID는 이 구현에서 질문 ID가 아니라 답변 메시지 ID다.
- Case·메시지 요청 키 중복, 같은 feature 식별 조합 중복, Case당 LIVE 보고서 중복, 동일 정의의 중복 인덱스는 검사 결과 0건이다. Case 17건 모두 LIVE 보고서가 있다.
- `diagnosis_json`과 정황 테이블의 Atom 내용이 일치하고 Context projection 17건 모두 최신 revision이다. 활성 사건 총괄 복수 배정은 없으며, 직원 명부에 없는 `mvp-v3-bank-operator`는 고정 기능 체험자라서 자동 삭제 대상이 아니다.
- 기존 17건 Case의 `case_inputs.input_text`는 변경 전 구현이 빈 값을 기록했기 때문에 0건이며, 025 적용 전 `transcript_segments`도 0건이었다. 신규 데모 Case부터는 원문을 `VOICE_TRANSCRIPT`로 보관한다. `analysis_segments` 94건과 diagnosis의 window/evidence 텍스트는 원문 제거 projection이 생성하는 라벨과 일치한다. 17건 모두 `model_metadata.source_text_retention=NONE`이다.
- 데모 분석 중에는 분석 계층이 원문을 읽고, General API가 입력 원문을 Case 입력으로 보관한다. 단, 저장 원문은 Case Copilot·Context AI·CSR 지원 API에 전달하지 않고 구조화 Envelope만 AI 지원 입력으로 사용한다. 레거시 다중 transcript 저장·조회 API는 410으로 차단한다.
- 반복된 고객/직원 채팅은 15개 그룹(첫 행 외 52행)이며 그중 6개 그룹은 10초 내 반복이 있다. 서로 다른 요청 키로 사용자가 재질문했을 수 있으므로 자동 중복 삭제 근거가 아니다.
- 소유자 없는 `AI_PRIVATE` 7건은 `SYSTEM_EVENT`로, 고객 답변의 내부 수신 이벤트를 남기는 코드 경로와 일치한다. 일반 개인 채팅의 소유자 누락과 구분한다.

위 내용은 정상화 전 읽기 전용 점검 기록이다. **백업·migration 정합화·거래 테이블 적용은 위 적용 완료 절에서 갱신했다.** 다음은 조회 실패/mock 표시 구분 → 금액 사건·중복·합계 정책 수정 → 검토·확정 흐름 및 실패 작업 재처리 판단이다.

## 서비스와 변경 불가 원칙

CSR(Case Share Room)은 보이스피싱 의심 사건에서 고객, 은행 직원, AI가 하나의 Shared Case를 통해 확인된 사실과 진행 업무를 공유하는 서비스다.

- AI는 분석·추천·요약을 지원하지만 은행 직원의 결정을 대신하지 않는다.
- 고객 진술과 AI 추출 결과는 직원 또는 공식기관 확인 전까지 확정 사실이 아니다.
- 안내 열람, 질문 답변, AI 추론만으로 지급정지·신고·피해구제가 완료됐다고 표시하지 않는다.
- 고객 공개 데이터와 은행 내부 데이터를 서버 경계에서 분리한다.
- 데모 통화 원문은 `case_inputs`에 보관하되 AI 지원 계층에는 전달하지 않고, Shared Case의 업무·맥락 데이터는 privacy-safe 구조화 결과를 사용한다.
- 직원 편집과 확정 사실을 AI 자동 갱신으로 덮어쓰지 않는다.
- Frontend는 General API만 호출하며 AI API와 DB를 직접 사용하지 않는다.
- 이번 데모에서는 Vector DB와 embedding 색인을 사용하지 않는다. MySQL 구조화 데이터·Case Snapshot JSON·Case-local TF-IDF 검색을 LLM 입력 기반으로 사용한다.
- 현재 최신 작업을 모으는 원격 통합 브랜치는 `integration/dev2-with-ham3-frontend`다. 팀원 작업은 이 브랜치를 PR base로 삼고, `dev2`·`main` 병합은 이후 릴리스 판단 시 별도로 진행한다.

## 현재 실행 구조

```text
React Frontend :5176
  └─ /api → General FastAPI :8100
                ├─ MySQL / attachment storage
                └─ AI FastAPI :8101
                     ├─ Event·Context Feature extraction
                     ├─ Window Logistic risk model
                     └─ LLM support services
```

- 로컬 시연은 `MVP_OPEN_PERMISSIONS=1`을 사용할 수 있지만 실제 인증/RBAC를 의미하지 않는다.
- 환경변수는 `MVP_v3/.env` 하나를 사용한다.
- 신규 DB는 `backend/scripts/apply_migrations.py`로 전체 migration을 적용한다. Docker용 초기화 SQL은 같은 migration에서 자동 생성하며 두 경로의 일치를 테스트한다.

## 현재 구현된 핵심 기능

### 분석과 Case 생성

- 통화 원문을 Event, Context code, 숫자 Feature로 변환하고 Window Logistic 위험도를 계산한다.
- 데모 원문은 Case 입력 원장에 보관하고, 구조화 신호와 privacy-safe projection으로 업무 Case를 만든다. 저장 원문은 지원 AI 입력에서 제외한다.
- 목표 CSR 분석 경계는 원문이 아닌 strict `AnalysisEnvelope`이며 `/ai/analyze/signals`가 구조화 입력을 받는다.
- 이번 프로젝트는 실제 통신사·온디바이스 계층을 연결하지 않는다. 현재 텍스트 입력은 이를 모사하는 데모 어댑터이며, Envelope 생성 이후에는 동일한 CSR 분석 코어를 사용해 Case를 생성한다.
- 화자·행위자·대상자·보고자, 기관·지점·인물·직책, 관계·호칭, 기한·순서·빈도·confidence를 additive metadata로 보존한다.
- 새 통화 분석 결과는 `보이스피싱 의심 인물`과 `고객`을 구분하고 주요 metadata를 카드 내부에 표시한다. 담당자용 데모 원문 확인 영역은 최초 분석 결과 화면의 transient 입력에서만 제공하며, Case Room의 초기 분석 결과 재조회에는 원문을 포함하지 않는다.
- 모델은 실험용 sample artifact이며 금융기관의 최종 판단으로 표시하지 않는다.
- 과거 LLM pipeline의 합성 30건 baseline과 Feature inventory는 `../../tests/context_test/`에 보존한다.

### Context Panel V3

- 은행 Case Room은 `frontend/src/context-v3/`의 정확한 7개 Section을 사용한다.
- 고객·직원 CHAT 저장 후 durable extraction job이 Message를 typed `PROPOSED` Fact로 변환한다.
- 요청 금액·실제 송금액·수행 상태와 CLAIM·DEMAND·TACTIC을 분리한다.
- Fact confirm/reject/supersede, Gap, Verification, AI Suggestion, Staff Task, Decision을 분리한다.
- 고객 공개는 서버 allowlist를 사용하며 민감 연락처·계좌는 마스킹한다.
- Summary 직원 override는 revision이 맞을 때만 표시하고 canonical data를 변경하지 않는다.
- Context Quick Nav, 최근 사건 기록 Drawer, projection 오류·재시도 UI를 제공한다.

### 최근 Frontend 단순화
- 좁은 화면에서도 은행 Context Panel 토글과 고객 화면 이동 링크를 유지한다. 고객 화면의 현재 진행 상황은 980px 이하에서 헤더 토글로 여는 off-canvas panel로 제공한다.
- Context Quick Nav는 모든 아코디언을 펼쳐도 세로로 축소되지 않으며, 아래 Context 본문만 독립적으로 스크롤된다.
- Context 본문 스크롤바가 생겨도 카드 폭이 흔들리지 않으며, 좁은 카드 헤더의 한글 제목은 글자 단위로 쪼개지지 않고 액션이 필요한 경우 다음 행으로 배치된다.
- 사건 요약 카드가 좁아지면 편집 액션의 문구만 아이콘으로 축약해 제목·상태·액션을 한 행에 유지한다.
- 사건 요약 편집기는 카드 헤더 아래 독립 블록으로 배치하며, textarea와 취소·저장 버튼에 Context V3 전용 스타일을 적용한다.
- Context V3 본문은 좁은 패널에서 카드 가용 폭을 확보하도록 전용 스크롤 영역의 좌우 padding을 4px로 사용한다.
- Context 근거 상세는 내부 enum·UUID·revision·일반 confidence 수치를 노출하지 않고 대화 기록·고객 답변·기관 확인 결과 등 직원용 근거 종류와 건수로 표시한다.
- Context Panel은 `TRANSFERRED`·`PROPOSED` 같은 내부 상태와 미등록 source/status/event/actor 값을 직원 화면에 노출하지 않고 한국어 표시값 또는 안전한 일반 문구를 사용한다.
- Case Context Projection에 `confirmed_facts`, `proposed_facts`, `unresolved_items`, `verification_records`, `staff_actions`, `money_events`, `projection_revision`을 함께 전달하는 하위 호환 계약을 추가했다. C파트 요약 AI는 이 상태 보존 projection을 입력으로 사용해야 한다.

- 은행 `고객 공유 결과` Section은 `CustomerProgressEditor`를 바로 표시한다. 중복 notice, lane, count, empty state를 제거했다.
- Summary의 중복 `위험도 · 진행 상태` 문구는 구조화 Case metadata와 정확히 일치하는 deterministic item만 표시에서 제외한다. Case의 risk/status 데이터는 유지한다.
- 고객 `현재 진행 상황`은 5개의 큰 카드를 compact step list로 변경했다.
- `COMPLETED`, `SUBMITTED`, `IN_PROGRESS`, `UNKNOWN`, `NOT_APPLICABLE`을 서로 다른 의미로 표시한다.
- 상세 summary, next action, reference, 확인 시각, 담당자 확인 요청은 단계별 접근 가능한 상세 영역에 보존한다.
- 단일로 확정할 수 있는 `IN_PROGRESS`/`SUBMITTED` next action만 `지금 할 일`로 강조한다.
- 고객 진행 상태의 `COMPLETED`/`NOT_APPLICABLE` 단계에는 새 담당자 확인 요청을 노출하지 않고, 이미 기록된 요청 상태만 중복 없이 표시한다.
- 은행 Context Quick Nav의 고객 공유 항목은 본문에 표시되지 않는 공개 자원 수를 숫자로 표시하지 않는다.
- 고객 진행 패널의 핵심 상태·상세·안전 문구 가독성과 Fact 추가 작업 버튼의 클릭 영역을 보강하고, 직원 화면의 개발자용 미구현 안내 문구를 제거했다.

### 고객 진행 상태와 AI

- SAFETY, EVIDENCE, PAYMENT_HOLD, REPORT, RELIEF의 독립 상태를 append-only snapshot으로 저장한다.
- 제출·완료 확인에는 근거와 시각이 필요하다.
- 고객 확인 요청은 revision 단위로 멱등 저장하며 고객·은행 채팅에 기록한다.
- 고객 화면과 Customer Agent는 동일한 고객 공개 진행 상태를 사용한다.

### 보고서와 협업

- 사건 종결은 관리자 암호와 AI 최종 보고서 생성 경로를 사용한다.
- 메시지, 질문·답변, Fact, Verification, Task, 결정 기록을 Case 단위로 검색해 은행 AI와 고객 AI에 서로 다른 공개 범위로 제공한다.
- 질문 카드, 구조화 답변, 참여자, 개인 메모, 북마크, 종결·복구·휴지통 흐름을 제공한다. 첨부파일은 데모 범위에서 제외했다.

## 아직 완료되지 않은 범위

- Context Summary는 현재 규칙 기반 projection이며 최신 Case 전체를 LLM으로 재요약하는 구조가 아니다.
- 실제 인증 세션과 운영형 RBAC가 없다.
- 실제 브라우저에서 은행·고객 전체 업무를 연속 수행한 E2E 증거가 없다.
- 실제 금융기관·수사기관·통신사 API와 공식 corpus가 없다.
- 실제 온디바이스·통신사·ASAP/FDS 연동은 데모 범위 밖이며 구현하지 않는다.
- 외부 Envelope 제출용 General API endpoint는 데모 완료 조건이 아니다. 현재 `/api/cases/analyze`가 데모 입력 → Envelope → Case 생성을 완료한다.
- 새 통화 분석 결과는 주요 정황 카드와 `추가 구조화 정보`에서 Atom·Relation·Episode·Action Group·Entity·Mention·미매핑 Observation을 표시한다.
- 실제 외부 AI를 이용한 새 Envelope schema live 호출, 비용·latency·출력 잘림 검증은 수행하지 않았다.
- 모든 legacy 메시지·답변의 Context V3 backfill은 없다.
- `bundle.recent_events`는 전체 감사 이력이 아니다. resource별 before/after와 cursor를 제공하는 History API가 필요하다.
- 신규 Fact 생성 시 기존 Fact를 대체하려는 의도를 polling 이후까지 보존하는 계약이 없다.
- Task 원본 상세 편집 projection과 Fact evidence 후보·직원 메모 계약이 부족하다.
- 고객 공개 Draft/Review/Publish/Withdraw workflow는 없다. 현재는 서버가 이미 공개한 결과만 사용한다.
- 영구 Vector DB와 embedding 의미 검색은 이번 개발 범위에서 제외했다. 현재 검색은 Case·공개 범위별 한국어 TF-IDF/동의어 검색이며 원본 DB보다 우선하지 않는다.
- 변경 동기화는 polling 중심이며 SSE/WebSocket이 아니다.
- 첨부파일은 제공하지 않는다(따라서 악성코드 검사·object storage·signed URL도 범위 밖이다).
- 실제 외부 업무가 연결되지 않았으므로 앱의 업무·Action 기록은 외부 처리 완료 증거가 아니다.

## 다음 작업 우선순위

### P0

1. 현재 변경을 commit/push하고 `Analysis Envelope Guard`의 최초 GitHub Actions 실행을 확인한다.
2. 원격 통합 브랜치에 3개 workflow job을 Required Check로 지정하고 force push를 제한한다.
3. 은행·고객 두 브라우저에서 새 분석→Case→채팅→질문→Fact→업무→고객 공개→새로고침 전체 E2E를 검증한다.
4. 역할 귀속·구체 명칭·시간 관계 fixture를 확대하고 GPT 품질·비용·latency를 측정한다.
5. 실제 인증 세션과 서버 권한 모델을 설계·구현한다.
6. resource별 전체 History API와 고객 공개 workflow 계약을 확정한다.

### P1

1. 최신 Shared Case 기반 LLM Summary와 revision cache를 구현한다.
2. persistent supersede intent, Task detail, Fact evidence/staff note 계약을 보강한다.
3. Case-local TF-IDF 중복 질문 방지와 검색 provenance를 개선한다.
4. polling을 SSE/WebSocket과 장애 시 fallback polling 구조로 개선한다.

### P2

1. 외부 기관·금융 시스템 연동과 직원 승인·감사·재시도 체계를 구현한다.
2. 첨부파일 기능은 실제 운영 범위가 확정될 때 별도 설계한다.
3. AI quota, model/prompt version, 비용, latency, 장애 복구를 운영 지표로 관리한다.

## 최신 검증 기준

| 검증 | 최신 확인 결과 |
|---|---|
| LLM Context baseline | 합성 30건 재집계: Context Feature Recall 0.4145, Critical Fact Recall 0.3137, contradiction 7건, hallucination 76건 |
| Context V3 General API | Prework Step 1에서 MySQL integration 제외 `general_api/tests` 168개와 별도 ActorContext 테스트 9개 통과. 실제 MySQL integration은 미실행 |
| Context V3 AI API | 2026-09-19 `ai_api/tests`: 312 passed, 155 subtests passed. 실제 외부 AI live 호출은 미실행 |
| Analysis Envelope·Case 생성 | 신규 Envelope/Narrative 6 passed, General API Case 생성 관련 선택 테스트 28 passed·3 subtests passed |
| Migration | 2026-09-21 schema 테스트 8 passed·4 subtests, 실DB 정상화/복원 검증 통과. 기존 MySQL suite는 15 passed·1 failed(lease 시각 비교) |
| Frontend | 2026-09-21 typecheck PASS, production build 1,473 modules PASS; 실제 브라우저 E2E는 미실행 |
| LLM Context evaluator | `tests/context_test/test_evaluate.py` 2개 PASS |
| Judge Explorer metadata | 현재 코드 기준 재생성, 관련 테스트 `8 passed` |

작업 종료 시 실제로 다시 실행한 검증만 이 표에 갱신한다. 과거 HTTP 200, 과거 유료 호출, 특정 Case 수동 보정 기록은 최신 기능 검증으로 재사용하지 않는다.

## 알려진 경고

- FastAPI `on_event`와 TestClient/httpx 관련 deprecation warning
- General API와 AI API의 `tests` Python package명이 같아 전체 경로를 한 pytest 명령에 섞지 않고 suite별로 실행해야 함
- MySQL `risk_score` 정밀도 경고
- MySQL `VALUES()` upsert deprecation warning
- 브라우저 E2E와 실제 외부기관 연동 미검증

## 유지하는 기준 문서

- 문서 안내: `README.md`
- 개인정보 안전 분석 흐름: `04_PRIVACY_SAFE_SIGNAL_FLOW.md`
- 고객 진행 상태와 AI: `07_CUSTOMER_PROGRESS_AND_AI.md`
- Case Context 데이터 계약: `09_CASE_CONTEXT_DATA_CONTRACT.md`
- 사건 종결 보고서 계약: `10_FINAL_CASE_REPORT_CONTRACT.md`
- Analysis Envelope 병합 기준선: `33_ANALYSIS_ENVELOPE_FREEZE_CONTRACT.md`
- Analysis Envelope 후속 연동: `34_ANALYSIS_ENVELOPE_INTEGRATION_BACKLOG.md`

## 2026-09-19 Analysis Envelope·새 통화 분석 기준선

- 저장 원문을 보지 않는 CSR 지원 AI 운영 경계를 `AnalysisEnvelope`로 분리하고 strict schema, 참조 무결성, `source_text_included=false`를 적용했다.
- 데모 텍스트 입력은 Envelope 변환 전용 어댑터로 유지하며 운영 분석 코어는 구조화 정보만 사용한다.
- 기관·지점·인물·직책·관계·호칭, 화자·행위자·대상자·보고자, 기한·남은 시간·등장 순서·횟수·confidence 필드를 추가했다.
- Context LLM은 구조화 metadata를 바꿀 수 없고 직원용 문장 생성만 담당한다. 직원 화면 용어는 `보이스피싱 의심 인물`로 통일한다.
- 새 통화 분석 결과 패널은 주요 metadata와 Mention 정보를 내부 스크롤 영역에 표시하고, 담당자용 데모 원문 확인 영역은 저장된 `case_inputs`에서 제공한다.
- 주요 카드에 매핑되지 않은 Atom·Relation·Episode·Action Group·Entity·Mention·Observation은 `추가 구조화 정보` 상세 영역에서 확인할 수 있다.
- `.github/workflows/analysis-envelope-guard.yml`에 Envelope/Case 회귀 테스트, Frontend build, PR diff 검사를 추가했다. 원격 Required Check 활성화는 commit/push 후 저장소 관리자 설정이 필요하다.
- 병합 시 보존할 불변 조건과 필수 회귀 명령은 `33_ANALYSIS_ENVELOPE_FREEZE_CONTRACT.md`에 고정했다.
- 실제 외부 연동은 데모 범위 밖이다. 구조화 전체 상세 표시와 GitHub Actions 병합 게이트를 추가했으며, 원격 Required Check 설정·브라우저 E2E·GPT 품질 측정은 `34_ANALYSIS_ENVELOPE_INTEGRATION_BACKLOG.md`의 후속 작업이다.
- Vector DB는 이번 개발 범위에서 제외한다. MySQL의 구조화 리소스를 원본으로 유지하고, Case Snapshot JSON과 Case-local TF-IDF 검색 결과만 허용 범위에 맞춰 LLM에 전달한다.

## 2026-09-21 DB 사용처 분류·안전한 API 전환

- `database/DB_USAGE_AUDIT.md`에 DB_CATALOG 기준 32개 테이블·356개 컬럼의 실제 route/repository/frontend 사용처를 분류했다.
- 현재 삭제하면 안 되는 핵심 원장·Context V2·대화·거래·보고서·이력 테이블과, 행 수가 0이어도 API 계약이 있어 유지해야 하는 선택 기능을 구분했다.
- 사용처가 없고 원문 보관 원칙과 충돌하던 통화 세션별 `transcript_segments`/transcript API만 안전하게 retirement했다. 빈 테이블일 때만 DROP하는 fail-closed migration과 HTTP 410 경계를 적용했다.
- 데모 입력 원문은 `case_inputs.input_text`에 보관하되 지원 AI에는 전달하지 않는다. `voice_sessions`는 원문이 아닌 세션 metadata 호환 계층으로 유지한다.
- Fact V2 복사·legacy 저장 전환·삭제 migration과 핵심 회귀를 완료했다. 남은 정리 대상은 diagnosis/report projection의 authoritative source matrix와 캐시 정책이다.
- 단계별 정리 투두·체크리스트는 `database/DB_USAGE_AUDIT.md`의 “DB 정리 후속 TODO·체크리스트”에 고정했다. canonical source 확정과 제품 기능 유지/제거 결정은 필수 검토이며, 실제 DROP은 백업·복원·회귀가 끝난 뒤에만 진행한다.
## 2026-09-15 Context 종료 업무 UI 보완

- 담당자 조치 Section의 `완료·취소 업무 N건` 요약을 누르면 종료 업무 목록과 상태·결과를 확인할 수 있다.
- 각 업무는 확인 후 기존 Backend 계약에 따라 대기(`TODO`) 업무로 복구할 수 있으며, 기존 변경 이력은 유지된다.
- 피해·노출, 사칭·접촉 정보, 사기 정황, 사실·확인 현황은 제외된 정보가 있을 때 하단 기록 요약을 제공하며, 해당 정보를 기존 이력을 보존한 채 `PROPOSED` 상태로 복구할 수 있다.
- 확정 Fact는 정정 제안을 만들거나 확정을 취소하거나 잘못된 정보로 제외할 수 있다. 정정안은 별도 `PROPOSED` Fact로 검토되며 확정될 때 기존 Fact를 `SUPERSEDED`로 보존한다.
- 얼럿 UI 전환 전 현재 입력·확인·오류 동작 기준선은 `docs/17_CONTEXT_DIALOG_MIGRATION_BASELINE.md`에 고정했다. 이번 단계에서는 런타임 동작을 변경하지 않았다.
## 2026-09-15 Context Dialog Migration Step 2

- Added reusable Context Panel UI primitives: `ContextActionModal`, `ContextConfirmModal`, `ContextTextArea`, and `ContextInlineError`.
- Existing `prompt`/`confirm`/`alert` runtime behavior remains unchanged until the next migration step.
- Typecheck, production build, and Context V3 regression passed.
## 2026-09-15 Context Dialog Migration Step 5

- Safety verification completed for the reusable dialog foundation.
- Frontend typecheck, production build, Context V3 regression, and diff check passed.
- Runtime prompt/confirm/alert migration remains pending for the next implementation step.
## 2026-09-15 Chat/Context synchronization audit

- Added `docs/18_CHAT_CONTEXT_SYNC_AUDIT.md` documenting the current resource ownership, projection paths, refresh rules, and known central-card/Context-panel gaps.
- No runtime or API contract changes were made in this audit step.
## 2026-09-15 Common Resource contract draft

- Added `docs/19_COMMON_RESOURCE_CONTRACT_DRAFT.md` covering shared identifiers, actor/source, visibility, versioning, lifecycle states, audit history, and central-card/Context-panel usage rules.
- This is a contract draft only; no runtime, schema, or API changes were made.
## 2026-09-15 Action contract migration plan

- Added `docs/20_ACTION_CONTRACT_MIGRATION_PLAN.md` defining the compatible title/content split, DTO/repository/migration order, fallback behavior, and version/visibility rules.
- No runtime, schema, or API code was changed in this planning step.
## 2026-09-15 Activity Event contract

- Added `docs/21_ACTIVITY_EVENT_CONTRACT.md` defining shared change events for central timeline and Context Panel projection, including actor, visibility, revision, idempotency, and failure rules.
- No runtime, schema, or API implementation was changed in this design step.
## 2026-09-15 Central timeline connection

- Added `docs/23_CENTRAL_TIMELINE_CONNECTION.md` documenting current Timeline composition, Context Panel separation, Activity Event insertion point, and visibility/duplication rules.
- No runtime or API changes were made in this design step.
## 2026-09-15 Mutation synchronization rules

- Added `docs/24_MUTATION_SYNC_RULES.md` documenting per-resource mutation APIs, central bundle refresh, Context projection refresh, and target consistency/visibility regression rules.
- No runtime or API contract changes were made in this documentation step.
## 2026-09-15 Actor·권한·Visibility 기준 (Step 8)

- `docs/25_ACTOR_PERMISSION_VISIBILITY_RULES.md`에 Actor 분류, 역할별 operation 권한, 은행/고객 Visibility 규칙을 정리했다.
- 은행 패널 mutation의 READ/WRITE/REVIEW 검사는 확인했으며, 고객 패널 조회의 인증·사건 소유권 검사가 후속 GAP으로 기록되었다.
- 이번 단계에서는 인증·권한 runtime 동작과 API를 변경하지 않았다.

## 2026-09-15 ActorContext 계약 초안 (Step 9)

- `docs/26_ACTOR_CONTEXT_CONTRACT.md`에 공통 ActorContext 구조, 기존 actor_user_id 호환 계층, 권한·감사 필드를 정의했다.
- 서버가 actor type/역할/권한을 계산하고 클라이언트 입력은 권한 판정에 사용하지 않는 원칙을 고정했다.
- 고객 사건 소유권 검증과 서비스 토큰 기반 AI/System mutation은 다음 구현 단계로 남겼다.

## 2026-09-15 ActorContext 공통 모듈 (Step 10)

- `backend/general_api/app/core/actor_context.py`에 레거시 actor 필드 정규화, 역할별 권한 계산, AI/System 서비스 토큰 제한을 추가했다.
- 기존 endpoint 시그니처는 유지하며, 라우트가 점진적으로 `ActorContext`를 사용하도록 순수 모듈로 분리했다.
- `test_actor_context.py`에서 직원 역할·위조 actor_type·AI 서비스 토큰 규칙을 검증한다.
- `main.py`의 `require_context_v2_member`가 기존 `actor_user_id`를 `ActorContext`로 정규화한 뒤 사건 멤버 역할로 권한을 판정하도록 연결했다.
- 기존 API query 계약과 데모 권한 동작은 유지하며, 빈 actor는 명시적인 401 응답으로 처리한다.
- 고객 패널 인증·소유권 검증과 세션 토큰 주입은 후속 단계에서 적용한다.
- 고객 Context Panel 조회에도 `actor_user_id`를 요구하고 활성 `CUSTOMER` 사건 멤버만 고객 projection을 조회하도록 검증을 추가했다.
- 중앙 타임라인의 action id와 우측 패널 `ACTION_RECORD` 투영, 고객 projection 비노출 규칙을 검증하는 `test_context_timeline_panel_sync.py`를 추가했다.
- `docs/27_FINAL_ACTOR_MIGRATION_CHECKLIST.md`에 1~15단계의 최종 완료 범위와 세션 인증 도입 전환 조건을 정리했다.
- 현재 MVP 환경에는 세션 인증 공급자가 없어 레거시 `actor_user_id`를 제거하지 않고 호환 상태로 마무리했다.

## 2026-09-15 Prework Step 1 공통 Backend 기준선

- `ActorContext`는 actor type만으로 사건 역할을 부여하지 않고, 활성 사건 멤버십에서 가져온 역할과 `case_id`를 결합해 READ/WRITE/REVIEW 권한을 계산한다.
- 고객 Context Panel은 활성 `CUSTOMER` 멤버만 자신의 사건에서 조회할 수 있으며, 미등록·비활성·다른 고객과 AI/System actor는 거부한다.
- `MVP_OPEN_PERMISSIONS=1`에서도 고객 멤버가 은행 Context Panel 또는 은행 전용 Context 표시 편집 경로로 우회하지 못하도록 경계를 고정했다.
- legacy Action의 DB `action_id`가 생성·수정 event payload와 Context Panel `ACTION_RECORD.item_id`에서 동일하게 유지되고, 기본 visibility가 `BANK_INTERNAL`임을 회귀 테스트로 고정했다.
- MySQL integration을 제외한 General API 테스트 168개, 별도 ActorContext 테스트 9개, Python AST parse 54개를 통과했다. 실제 MySQL과 브라우저 E2E는 이번 단계에서 실행하지 않았다.
- 실제 세션 인증, 전체 endpoint ActorContext 전환, canonical resource 결정, AI runtime 및 seed/extraction 계약은 이번 단계 밖의 후속 작업이다.

## 2026-09-15 Prework Step 3 Canonical Work Resource Contract

- `docs/29_CANONICAL_WORK_RESOURCE_CONTRACT.md`에서 Legacy Action, V2 Task, AI Suggestion의 현재 저장·API·UI 관계를 대조하고 Model B(`Suggestion → Task`, Action 독립 실제 조치 기록)를 확정했다.
- canonical source, lifecycle, human-in-control, timeline/history, STAFF_ACTIONS/customer projection, ABC ownership, migration/frontend impact를 기록했다.
- 이번 단계에서는 문서만 추가했으며 Frontend/Backend/AI runtime, DB schema, migration, data movement, commit/push는 수행하지 않았다.

## 2026-09-15 Prework Step 4 Actor Permission Visibility Contract

- `docs/30_ACTOR_PERMISSION_VISIBILITY_CONTRACT.md`에 Actor type·Case role·operation 분리, Resource permission matrix, visibility matrix, AI/System 경계를 확정했다.
- Context V2 Suggestion review는 `REVIEW` 권한을 사용하고, Legacy Action list/create/update는 명시적 actor와 active Case membership을 요구하도록 Backend 경계를 보완했다.
- Frontend, DB migration, session/token IAM, AI runtime fallback은 변경하지 않았다.

## 2026-09-15 Prework Step 4 Final Verification

- `MVP_v3/.venv/Scripts/python.exe`의 pytest 9.1.1로 General API non-MySQL 회귀를 실행했다.
- Legacy Action 및 Customer Progress 테스트 fixture에 현재 actor ownership 계약을 반영했다.
- General API non-MySQL: 168 passed, 43 subtests passed. MySQL integration은 실행하지 않았다.
- Step 4 permission 경계를 완화하지 않았으며 최종 판정은 `STEP_4_COMPLETE`, `READY_FOR_STEP_5`다.

## 2026-09-16 A파트 LLM Context lexical/pragmatic fidelity

- 현재 브랜치 `v3.1-ham`의 working tree를 기준으로 A파트 Context Pipeline에 privacy-safe `observed_terms`와 `speech_form_codes`를 additive하게 연결했다.
- 기존 normalized `lexical_cues`와 semantic fields는 유지하고, 실제 source turn에 존재하는 짧은 allowlist 용어만 Atom에 surface form·lemma·normalized lexical code로 저장한다.
- Context observation은 surface form을 복제하지 않고 `source_atom_ids`, `observed_lexical_codes`, `semantic_features`로 Atom lineage를 참조한다.
- OTP·계좌번호·인증 secret 값, raw phrase, token dump, source에 없는 lexical cue는 저장하지 않도록 targeted tests를 추가했다.
- ML feature vector/model artifact와 Frontend는 변경하지 않았고, 기존 JSON persistence 컬럼을 확장하므로 DB migration은 필요하지 않다.
- `MVP_v3/docs/now_md/A_part`에 A파트 기준 문서를 모아 관리한다. 기존 문서의 historical note는 당시 상태를 기록한 것이다.
- 현재 Grounded 문장화는 존재하지만 일부 Panel projection이 여러 세부 Fact를 넓은 문장으로 합칠 수 있어 specificity 손실 가능성이 남아 있다.
- 다음 A 구현은 `Fine-Grained Grounded Statement`, one-Fact-one-Statement 기본 정책, semantic slot/action-state/polarity/unknown 보존, 다중 Fact 분리 projection과 Relation-aware 문장화를 대상으로 한다.
- Context Signal의 상위 label을 그대로 직원용 문장으로 사용하지 않고 supporting Atom/Fact의 구체 의미를 우선하는 방향으로 보강한다.
- Fine-Grained Grounded Statement 1차 구현으로 Fact가 참조하는 supporting Atom의 OTP 유형, 안전계좌 목적, 긴급성 lexical cue, 통신 통제, action state를 직원용 문장에 반영한다.
- 2026-09-16 다중 predicate Atom 분리 validator를 추가해 송금·인증정보·통신 통제처럼 서로 다른 의미가 한 Atom에 혼합되면 저장하지 않도록 하고, 분리된 Atom별 lineage를 유지한다.
- 2026-09-16 2단계 세분화 피처화를 완료해 슬롯 허용값 검증, action state 확장, 독립 semantic field 보존, source 검증 observed term, 다중 금액·행동 fixture, privacy-safe coverage report를 추가했다. AI API 전체 테스트 152개 통과.
- 2026-09-16 다음 작업으로 2.5단계 `Semantic Feature Audit Agent`를 추가했다. Atom 누락·혼합·slot 불일치·unsupported lexicalization·lineage 단절을 감사하고, 원본을 자동 확정/삭제하지 않은 채 `PASS / NEEDS_REVIEW / REEXTRACTION_REQUIRED`로 판정하는 범위다.
- 2026-09-16 2.5단계 1차 구현으로 `SemanticAuditResult` 계약과 결정적 감사기를 추가하고 `DiagnosisResult.semantic_audit`에 연결했다. 감사기는 원문을 결과에 반환하지 않으며 Atom·Relation·Signal coverage, 혼합 Atom, observed term source 불일치, orphan lineage를 검사한다. 관련 테스트 47개 통과.
- 2026-09-16 2.5단계 2차 구현으로 `SemanticAuditReview` LLM 검토기와 selected-turn targeted re-extraction을 연결하고, 원문·근거 문장을 제거한 개발자용 JSON export 명령 `backend/scripts/export_diagnosis_report.py`를 추가했다. LLM 검토 실패 시 결정적 감사 결과를 유지하며 자동 확정/삭제하지 않는다. AI API 전체 테스트 158개 통과.
- 2026-09-16 4~6단계 구현 메모 `now_md/A_part/A_4_TO_6_IMPLEMENTATION_HANDOFF.md`를 추가했다. 4단계 Fact 저장·human review·revision 규칙, 5단계 기존 7개 패널 Fact projection, 6단계 one-Fact-one-Statement grounded 문장화와 완료 조건을 분리해 기록했다. 기존 Context V2 계약 테스트 33개가 통과했으며, 다음 구현 대상은 미완료 Fact projection과 semantic slot 보존이다.
- 현재는 전체 semantic slot과 모든 semantic key를 완전히 보존하는 단계가 아니므로 broad abstraction validator, 부정·조건·UNKNOWN 전 범위 검증, revision/conflict는 후속 작업으로 남아 있다.

## 2026-09-15 Prework Step 2 Frontend Freeze Contract

- `docs/28_FRONTEND_FREEZE_CONTRACT.md`에 현재 Frontend 구현을 기준으로 Context Panel 7개 Section, Fact/Verification/Question/Progress/Action 계약, visibility, version/revision, mutation reload 규칙을 고정했다.
- 현재 Backend/AI와 일치하는 계약과 후속 Backend/AI Gap을 분리해 기록했다.
- Action title 수정값이 legacy Action API로 전달되지 않는 `FRONTEND_FREEZE_EXCEPTION`을 확인했으며 이번 단계에서는 수정하지 않았다.
- Frontend, Backend business logic, AI, DB migration은 이번 단계에서 변경하지 않았다.
- Step 5에서 `contracts/public_api/ai_runtime.py` 공통 오류 코드·retryable 계약, AI readiness endpoint, General/AI 경계 테스트를 추가했다.
- 외부 AI live 호출은 실행하지 않았고, provider 실패 시 가짜 Fact/Action/Task/Report를 생성하지 않는 정책을 `docs/31_AI_RUNTIME_ERROR_CONTRACT.md`에 기록했다.
- Step 5 결과: `STEP_5_COMPLETE` / `READY_FOR_STEP_6`. AI runtime targeted tests와 AI API targeted tests는 통과했으며, 전체 General API 실행은 기존 MySQL schema test의 `case_number_sequences` 누락 1건으로 실패했다(이번 변경과 무관한 기존 환경/마이그레이션 상태).
- Step 6에서 Diagnosis 구조화 신호의 최소 seed bridge, Message extraction 상태 조회 endpoint, deterministic extractor/provenance/visibility 계약을 추가했다.
- `docs/32_CONTEXT_POPULATION_EXTRACTION_CONTRACT.md` 기준으로 `STEP_6_COMPLETE`·`PREWORK_COMPLETE_READY_FOR_PARALLEL`을 기록했다. 외부 AI 호출과 DB migration은 수행하지 않았다.
