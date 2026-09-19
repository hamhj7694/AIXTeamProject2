# Analysis Envelope·새 통화 분석 기준선 고정 계약

작성일: 2026-09-19
상태: 현재 구현 기준선(FREEZE)
적용 범위: 데모 입력, 데모 Envelope 변환, AI API, Case 저장, 새 통화 분석 결과 패널

이 문서는 다른 브랜치나 팀원 작업을 병합할 때 현재의 원문 비접근형 CSR 구조가 과거 방식으로 되돌아가지 않도록 고정하는 계약이다. 코드가 문서와 다르면 무조건 코드를 정답으로 간주하지 말고, 이 계약의 불변 조건과 회귀 테스트를 먼저 확인한다.

> 보호 수준: 문서·strict contract·회귀 테스트와 `.github/workflows/analysis-envelope-guard.yml`을 제공한다. 원격 GitHub Required Check와 Branch Protection은 저장소 관리자 설정 전까지 활성 상태가 아니므로, 그 전에는 PR 작성자와 검토자가 병합 게이트를 직접 확인한다.

## 1. 고정하는 서비스 경계

목표 CSR 구조의 시작점은 통화 원문이 아니라 `AnalysisEnvelope`다. 이번 프로젝트에서는 실제 외부 계층을 연결하지 않고 데모 분석기가 그 역할을 모사한다.

```text
[온디바이스·통신사·ASAP·FDS]
원문 이해·화자 분리·정황 구조화
              ↓
       AnalysisEnvelope
              ↓
[CSR]
계약 검증 → 구조화 문장 생성 → Case 생성 → 담당자 업무
```

현재 텍스트 입력 화면은 외부 분석 계층을 모사하는 데모 어댑터다.

```text
데모 텍스트 입력
→ /ai/analyze/text
→ 데모 분석기가 AnalysisEnvelope 생성
→ 운영과 같은 Envelope 분석 코어 실행
```

Envelope 분석 코어는 `POST /ai/analyze/signals`이며 원문 필드를 받지 않는다. 외부 사업자가 Envelope를 제출하는 General API endpoint와 실제 통신사 연동은 이번 데모 범위가 아니다.

## 2. 병합으로 변경하면 안 되는 불변 조건

### 2.1 원문 비접근·비저장

- CSR 운영 분석 API에 통화 원문, 긴 인용문, raw evidence span을 추가하지 않는다.
- `AnalysisEnvelope.source_text_included`는 항상 `false`다.
- `raw_transcript`, `full_transcript`, `raw_text` 같은 임의 필드는 strict contract에서 거부한다.
- 신규 Case의 `input_text`는 빈 문자열로 저장한다.
- Window와 Event의 저장 문자열은 원문이 아니라 정규화된 요약·신호 라벨이어야 한다.
- Frontend는 분석 완료 후 입력 텍스트를 비우고 결과 화면에서 원문을 다시 표시하지 않는다.
- 로그·trace·오류 응답에 원문이나 인증정보·계좌번호·OTP를 남기지 않는다.

### 2.2 역할 귀속

다음 역할은 하나의 문자열로 합치지 않는다.

- `speaker_role`: 실제 발화 역할
- `actor_role`: 주장·요구·행동의 주체
- `target_role`: 행동이나 발화의 대상
- `reported_by_role`: 해당 내용을 전달하거나 보고한 역할

`엄마, 나 스마트폰 고장 났어` 같은 문장은 다음 의미를 보존한다.

```text
speaker_role = SUSPECTED_PARTY
actor_role = SUSPECTED_PARTY
target_role = CUSTOMER
claimed_relationship = CHILD
vocative_target = 엄마
```

`엄마`를 발화자로 저장하거나 고객을 사칭·송금 요구의 행위자로 바꾸면 안 된다. 누락된 주체는 임의 추정하지 않고 `UNKNOWN`을 사용한다.

### 2.3 세부 정보 보존

Envelope가 제공한 다음 정보는 generic label로 덮어쓰지 않는다.

- 정확한 기관·상호·지점·부서명
- 인물명과 주장된 직책
- 가족·지인 등 주장된 관계와 호칭 대상
- 요구 행동·대상·목적·금액
- 절대 기한과 상대 남은 시간
- 최초·최종 등장 턴, 등장 순서, 반복 횟수
- 화자 및 귀속 confidence
- Semantic Atom·Mention·Relation·Episode lineage

예를 들어 `서울지검`, `OO은행 강남지점`, `OO경찰서`가 있으면 `수사기관`, `금융기관` 같은 상위 표현만 남기고 구체 명칭을 버리지 않는다.

### 2.4 직원 화면 용어

직원 화면과 LLM 출력은 다음 표현을 기준으로 한다.

- `보이스피싱 의심 인물의 주장`
- `보이스피싱 의심 인물의 요구`
- `보이스피싱 의심 인물의 압박·통제`
- `고객의 진술·행동`
- `화자 미상 · 확인 필요`

`상대방`처럼 주체가 불명확한 표현과 `범죄자`, `보이스피싱범`처럼 범행을 확정하는 표현을 기본 문구로 사용하지 않는다.

권장 문장 기준:

- `보이스피싱 의심 인물이 서울지검 수사관을 사칭한 정황이 확인됨`
- `보이스피싱 의심 인물이 고객 계좌가 범죄에 연루됐다고 주장함`
- `보이스피싱 의심 인물이 15시까지 송금을 요구함. 당시 기한까지 약 2시간 남은 상황으로 분석됨`
- `고객이 송금했다고 진술함. 실제 거래 완료 여부는 은행 내부 채널에서 별도 확인 필요`

`고객이 상대방의 주장을 전달함`처럼 행위·주장 내용이 없는 문장은 만들지 않는다.

### 2.5 LLM 권한 제한

- 역할·턴·Atom ID·Relation은 Envelope가 소유한다.
- LLM은 제공된 metadata를 수정하거나 새 화자·기관·금액·행동을 만들 수 없다.
- LLM은 검증된 구조를 직원용 문장과 요약으로 표현하는 역할만 맡는다.
- LLM 결과가 누락·실패해도 구조화 데이터와 deterministic fallback으로 Case 생성을 유지한다.
- 고객 진술과 의심 인물의 주장을 확인 사실로 승격하지 않는다.

### 2.6 Frontend 정보 보존

새 통화 분석 결과 패널은 디자인을 맞추기 위해 데이터를 삭제하지 않는다.

- 상세 항목 수가 많으면 영역 내부를 스크롤한다.
- 문장, 기관·인물·관계, 역할, 턴, 시간, 횟수, confidence를 서로 다른 표시 요소로 보존한다.
- 같은 code라는 이유만으로 근거가 다른 카드를 하나로 합치지 않는다.
- 동일 문장·동일 근거만 중복 제거한다.
- 기존 Case에 새 metadata가 없으면 기존 fallback으로 표시한다.

## 3. 현재 코드 기준점

| 책임 | 기준 파일 |
|---|---|
| Envelope·Atom·Narrative 계약 | `backend/contracts/diagnosis.py` |
| 데모 원문 → Envelope 변환 | `backend/ai_api/app/domains/diagnosis/envelope.py` |
| 데모/운영 분석 흐름 분리 | `backend/ai_api/app/domains/diagnosis/service.py` |
| 데모·운영 AI API | `backend/ai_api/app/main.py` |
| Atom JSON schema와 추출 지침 | `backend/ai_api/app/domains/diagnosis/constants.py` |
| 구조화 문장 생성·검증 | `backend/ai_api/app/domains/diagnosis/extractor.py` |
| 저장 전 privacy-safe projection | `backend/general_api/app/domains/cases/signal_projection.py` |
| Case 생성과 빈 `input_text` | `backend/general_api/app/domains/cases/service.py` |
| Frontend 타입 | `frontend/src/api/types.ts` |
| 새 통화 분석 결과 표시 | `frontend/src/pages/HomePage.tsx` |
| 결과 패널·메타정보 스타일 | `frontend/src/styles.css` |

## 4. 병합 충돌 처리 규칙

위 기준 파일에 충돌이 발생하면 다음 절차를 따른다.

1. 파일 전체에 `ours` 또는 `theirs`를 적용하지 않는다.
2. 양쪽 변경의 목적을 확인하고 필드·라우트·UI 단위로 의미 병합한다.
3. 새 필드는 가능한 additive·optional 방식으로 추가해 기존 Case 조회를 깨지 않는다.
4. `AnalysisEnvelope`, `SemanticAtom`, `ContextNarrative` 필드를 삭제하거나 이름을 바꿀 때는 migration·하위 호환·Frontend 타입을 함께 변경한다.
5. `/ai/analyze/signals`를 텍스트 입력 API로 되돌리지 않는다.
6. `input_text` 저장, 원문 결과 UI, raw evidence 저장 코드가 재도입되면 병합을 중단한다.
7. UI 충돌은 결과 카드 수를 줄이는 방식이 아니라 내부 스크롤·접기·가상화로 해결한다.
8. 충돌 해소 후 아래 병합 게이트를 모두 실행한다.

## 5. 필수 병합 게이트

저장소 루트 기준 PowerShell 명령:

```powershell
cd MVP_v3/backend
..\.venv\Scripts\python.exe -m pytest ai_api/tests -q
..\.venv\Scripts\python.exe -m pytest general_api/tests/test_analyze_case.py general_api/tests/test_public_analyze_endpoint.py general_api/tests/test_case_creation_transaction.py general_api/tests/test_case_retrieval.py -q

cd ..\frontend
npm.cmd run build

cd ..\..
git diff --check
```

반드시 유지해야 하는 핵심 회귀 테스트:

- `test_analysis_envelope.py`: raw transcript 거부, 호칭/화자 귀속, 정규화 Window
- `test_feature_narratives.py`: 근거 참조 검증, 잘못된 주체 문구 교정, 은행 내부 확인 문구
- Case 생성 테스트: `input_text` 비저장과 구조화 diagnosis 복원

현재 기준 검증 기록:

- AI API: `312 passed`, `155 subtests passed`
- General API Case 생성 관련 선택 테스트: `28 passed`, `3 subtests passed`
- 신규 Envelope·Narrative 테스트: `6 passed`
- Frontend TypeScript·Vite production build: 통과, `1461 modules transformed`
- 실제 외부 AI live 호출, MySQL 통합, 브라우저 E2E: 이번 기준선에서는 미실행

테스트 수가 달라질 수는 있지만 핵심 테스트의 삭제·skip·완화로 통과시켜서는 안 된다.

## 6. PR 체크리스트

- [ ] 운영 CSR 입력이 여전히 `AnalysisEnvelope`인가?
- [ ] 데모 원문 입력과 운영 Envelope 입력이 구분돼 있는가?
- [ ] 원문·긴 인용문·민감 literal이 DB/API read/log에 남지 않는가?
- [ ] 화자·행위자·대상자·보고자가 분리돼 있는가?
- [ ] 구체 기관명·인물명·관계·시간 정보가 보존되는가?
- [ ] `보이스피싱 의심 인물` 용어가 유지되는가?
- [ ] 고객 행동은 은행 내부 확인 전까지 진술로 표시되는가?
- [ ] Frontend가 레이아웃 때문에 구조화 정보를 잘라내지 않는가?
- [ ] 기존 Case의 optional-field 하위 호환이 유지되는가?
- [ ] 필수 병합 게이트를 실행하고 실제 결과를 PR에 기록했는가?
- [ ] 충돌 해결에 `git checkout --ours/--theirs`로 기준 파일 전체를 덮어쓰지 않았는가?
- [ ] `33_ANALYSIS_ENVELOPE_FREEZE_CONTRACT.md` 자체가 삭제·완화되지 않았는가?

## 7. 현재 한계

이 기준선은 실제 통신사·온디바이스 시스템이 연결됐다는 의미가 아니다. 운영 General API의 Envelope 기반 Case 생성 endpoint, 서비스 인증, 의미 충돌 검증, 실제 LLM 품질 검증, 모든 구조화 객체의 Frontend 표시가 남아 있다. 후속 범위는 `34_ANALYSIS_ENVELOPE_INTEGRATION_BACKLOG.md`를 따른다.
