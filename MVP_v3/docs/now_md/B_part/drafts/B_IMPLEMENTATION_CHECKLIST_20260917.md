# CSR B파트 Assisted Conversation & Verification 구현 체크리스트

작성일: 2026-09-17  
최종 업데이트: 2026-09-17  
목적: B 구현·검증 상태와 다음 실행 작업을 관리하는 공식 체크리스트
## 전체 진행 상태

- 현재 단계: P0/P1/P2 기본 구현 완료, 운영 연결은 부분 완료; P3 구현 준비.
- 기준: `MVP_v3`, `feat/b-dynamic-question-plan-p3`, HEAD `acee16b`.
- 완료 범위: 지원 답변 Fact 연결, 질문·검증 정책 helper, 역할별 Copilot, Python 품질 검사·산술 보조.
- 현재 한계: ANSWERED/정보 충족 혼동, baseline 보완 질문 차단, typed 의미·출처 손실, 검증 mapper 미연결.
- 다음 작업: P3-A1 상태 evaluator와 P3-C1 표현 검사; P3-I 입력 계약은 Integration과 병행 합의.
- 진행 원칙: 기존 흐름 유지, 담당자 검토 후 전송, AI 최종 판단·자동 질문 전송 추가 금지.
## 0단계 — 기준과 담당 범위 고정

- [x] 브랜치·HEAD·시작 시 working tree clean 확인.
- [x] A 체크리스트·High-Fidelity 설계와 현재 B 코드·관련 테스트 대조.
- [x] B: Question Plan/Eligibility, 답변 구조화, Verification 의미, Copilot/품질 정책.
- [x] A: 의미 추출, negation/uncertainty/correction, Atom/Fact·provenance 생성.
- [x] Integration: General API wiring, 공용 contracts, repository, migration, 공유 frontend 계약.
- [x] C: Action/Task, Timeline, Summary/Brief/Final Report, 업무 진행 흐름.
- 공유 변경은 Integration Requirement로 관리하며 B feature branch에서 임의 수정하지 않는다.
- 판정: `[x]`는 코드·테스트 코드·명시된 기존 실행 기록으로 확인한 한정 범위의 구현 완료.
- `[ ]`는 미구현·확인 불충분·연결 대기. 테스트 코드 존재는 이번 실행 통과를 뜻하지 않는다.
- helper 존재 ≠ 운영 wiring; 저장됨 ≠ B 전달; ANSWERED ≠ sufficiency; PROPOSED ≠ CONFIRMED.
## 1단계 — P0 Customer Answer → Case Fact

상태: 지원 필드 기본 연결 완료; 정정·충돌·최신 의미 상태 연결은 부분 완료.

- [x] 원답변·질문 관계 보존; legacy 답변 저장 경로 유지.
- [x] 명확한 지원 답변만 typed V2 Fact 생성; ambiguous/unsupported 답변은 의미 Fact 생성 억제.
- [x] `CUSTOMER_STATEMENT / PROPOSED` 저장, message ID + semantic key + canonical value 멱등성.
- [x] 송금 여부·개인정보·인증정보·원격 앱 지원; contextual 답변은 원답변 경로 유지.
- [x] provider 오류에서 가짜 AI 결과 생성 금지; deterministic/manual 경로 유지.
- [ ] B: ANSWERED와 semantic sufficiency 분리 → P3-A1/A2.
- [ ] A/Integration: correction/conflict 관계 생성·전달 → 8·9단계.
- [ ] Integration 검증: Fact 자체가 다음 Eligibility에 반영됨을 ANSWERED 제외와 독립 검증.
- 근거: `main.py::_structured_answer_fact_payload/_persist_structured_answer_fact`, `answer_service.py`.
- 기존 테스트: General `test_customer_answer_structured_fact.py`; 이번 실행 없음.
## 2단계 — P1 Question Policy

상태: helper 및 LLM normalization 완료; 모든 경로 적용·계약 연결은 부분 완료.

- [x] `QuestionSource.DETERMINISTIC / LLM` 모델·명시적 source 인자.
- [x] 선택지 공백·빈 항목·중복 제거, 선택지 최대 8개 검증.
- [x] TEXT/choice mode 정리; 선택지 없는 자유 입력은 TEXT로 변환.
- [x] multi-select boolean·고유 선택지 2개 이상 검증 helper.
- [x] 질문 본문·선택지의 일부 비밀번호/PIN/OTP 비밀값 요청·송금 실행 지시 차단.
- [x] LLM QUESTION_PLAN에서 `normalize_question()` 실제 호출.
- [ ] B: 설명·reason 포함 안전 검사 및 부작용 없는 OTP 제공 여부 허용 보강.
- [ ] B: SKIPPED 재추천 조건·보완 질문 목적 정의.
- [ ] Integration: deterministic/manual/queue 경로에도 동일 정책 적용.
- [ ] Integration: WorkCard multi-select·생성 source 계약 보존, baseline follow-up 필터 연결.
- 근거: `question_policy.py`, `work_card_service.py::generate`, `test_question_policy.py`.
## 3단계 — P1 Verification Policy

상태: Recommendation/Result 및 semantic mapper helper 완료; 운영 저장 연결 미완료.

- [x] `VerificationRecommendation`과 `VerificationResult` 의미 모델 분리.
- [x] completed + 비어 있지 않은 result_summary만 semantic proposal로 변환.
- [x] 기관·연락처 mapping, 불명확 대상 억제, task ID/version 기반 멱등 helper.
- [ ] Integration: `VerificationSemanticMapper.map_result()`를 실제 저장에 연결.
- [ ] Integration: 현재 기관 key 고정 저장을 결과 semantic scope에 맞게 연결.
- [ ] B: 실제 검증 범위만 해결; pending/failed는 확정 근거로 사용하지 않음.
- 근거: `verification_policy.py`, `test_verification_policy.py`, `main.py::update_case_verification`.
## 4단계 — P2 Customer / Bank Copilot Context

상태: 역할별 provider context 분리 완료; typed 근거 전달은 부분 완료.

- [x] Customer/Bank provider section과 역할 prompt 분리.
- [x] 고객 공개 진행 상태·현재 서비스 질문·공개 Verification 결과 사용.
- [x] Customer provider bundle의 직원 사실·업무·결정 등 내부 section 제외.
- [x] 검색 근거 수집에서 과거 AI_RESPONSE를 사실 Evidence로 제외.
- [x] 확정 grounding 입력에서 과거 AI 대화·첨부 파일명을 승인 근거로 제외.
- [ ] Integration: source_kind/typed value/evidence/확인자·시각 직접 전달.
- [ ] Integration: 최신 CHAT 의미 상태·완료 Verification의 직접 grounding 연결.
- [ ] B/Integration: 긴 context에서도 최신 핵심 근거·질문 상태 보존.
- 근거: `copilot_service.py::_context_sections/generate`, `case_retrieval.py::collect_records`.
## 5단계 — P2 Copilot Quality / Grounding

상태: 기본 품질·안전 검사 완료; 근거 수준 표현은 부분 완료.

- [x] deterministic Python evaluator: role, visibility, certainty, safety, relevance, conciseness, completeness.
- [x] direct answer 우선·불필요한 장문/번호 목록 억제 prompt·관련 평가.
- [x] 역할·내부 노출·unsupported certainty·위험 지시는 runtime 전달 차단.
- [x] relevance/conciseness/completeness는 평가되지만 단독 runtime 차단 기준은 아님.
- [x] 좁은 식별 가능 송금 문장의 합산·반복 진술 중복 억제·정정/충돌 합산 보류.
- [x] provider 오류는 오류로 전달; 다른 LLM 자동 재작성/재시도 미사용.
- [ ] B: “확인된 상태입니다” 등 확정 표현 누락 보강 → P3-C1.
- [ ] B/Integration: 진술·직원 확인·은행 기록·공식 결과의 구조적 grounding → P3-C2.
- 근거: `copilot_quality.py`, `copilot_accumulation.py`, directness/fact_grounding/quality 테스트.
## 6단계 — P3 Dynamic Question Plan

상태: 미완료. 기본 후보 정상 생성 + LLM 추가 질문만 허용하는 현재 구조를 점진적으로 변경한다.
### P3-A1 — Question State / Answer Sufficiency

담당: B. 첫 구현; 내부 evaluator + unit test, 저장 상태·공용 계약은 직접 변경하지 않는다.

- [ ] 미확인, ASKED 대기, 명확한 고객 진술, 불확실 답변을 구분.
- [ ] 충돌/정정 검토, 직원 확인, 객관/공식 검증, SKIPPED를 구분.
- [ ] ANSWERED는 접수 상태로 유지하고 sufficiency는 별도 평가.
- [ ] “OTP를 알려주지 않았어요”는 동일 목적 기본 질문 제외, 객관 검증 승격 금지.
- [ ] “기억이 안 나요”는 답변 접수 후에도 부족 상태·보완 질문 허용.
- [ ] unit 완료 조건: 명확/불확실/대기/충돌/SKIPPED 입력별 허용·제외 이유 검증.
### P3-I — Integration Requirements

담당: Integration. B 상태: Requirement 정의 / 연결 대기. 실제 연결 완료 아님.

- [ ] semantic_key, typed value, source_kind, Fact status, evidence·provenance·lineage 전달.
- [ ] confirmed_by/confirmed_at, correction/conflict relation 전달.
- [ ] Verification semantic scope와 completed/failed/pending 결과 전달.
- [ ] allow_multi_select, question semantic purpose, related previous question 연결.
- [ ] source/projection revision과 최신 핵심 context 보존; 상세 파일은 9단계.
### P3-A2 — 실제 Question Eligibility 연결

담당: B 소비 로직 + Integration wiring. 선행: P3-A1, 필요한 P3-I 계약·입력.

- [ ] 명확한 답변은 같은 semantic 목적 제외; ASKED 응답 대기 중복 차단.
- [ ] 불확실 답변은 보완 허용; PROPOSED 존재만으로 해결 처리 금지.
- [ ] correction/conflict 관계 소비, 임의 최신값 선택 금지.
- [ ] completed Verification의 확인 범위만 적용; pending/failed 확정 근거 금지.
- [ ] SKIPPED 기본 재추천 억제·명시적 재허용 조건 적용.
- [ ] 완료 조건: CHAT/질문 답변/Fact/검증에서 같은 의미 상태가 같은 eligibility 결과 생성.
### P3-B — Dynamic LLM Question Plan

담당: B. 선행: P3-A1/A2 및 shared filter 연결.

- [ ] deterministic을 eligibility/safety/ASKED/semantic 중복/SKIPPED/fallback 중심으로 축소.
- [ ] LLM이 미충족·불확실·충돌 과제의 우선순위·문장·mode·options·짧은 이유 생성.
- [ ] baseline에 없는 추가 질문만 허용하는 prompt를 필요한 동일 주제 follow-up 허용으로 조정.
- [ ] Integration이 shared baseline 필터·queue semantic 목적 검증 연결; B 직접 수정 금지.
- [ ] provider failure 때 동일 eligibility를 통과한 deterministic 안전 후보 유지, 가짜 AI 결과 금지.
- [ ] 완료 조건: 보완 질문은 허용하고 동일 목적 반복·비밀값 요청은 차단; 직원 검토 유지.
### P3-C1 — Bank Copilot 표현 Evaluator

담당: B. P3-I 전에도 한정된 표현 규칙·unit 작업 가능.

- [ ] 과도한 확정 표현 검사; 진술 존재 확인과 거래 검증을 분리.
- [ ] 고객 진술·합계의 근거 수준을 원 Fact보다 높이지 않음.
- [ ] “확인” 전면 금지 대신 무엇을 어떤 근거로 확인했는지 평가.
- [ ] Python evaluator만 보강; another LLM 자동 재작성/재시도 없음.
### P3-C2 — Source-aware Grounding

담당: B rendering/prompt/evaluator, Integration typed 입력. 선행: 관련 P3-I 연결.

- [ ] CUSTOMER_STATEMENT, 직원 확인, BANK_RECORD, OFFICIAL_VERIFICATION 구분.
- 직원 확인은 신규 enum을 임의 도입하지 않고 원출처 + CONFIRMED + 확인 기록으로 해석.
- 권장 문장: “고객은 300만원을 송금했다고 진술했습니다.” / “담당자가 해당 내용을 확인했습니다.”
- 권장 문장: “은행 거래기록에서 300만원 이체 내역을 확인했습니다.” / “등록된 기관 확인 결과에 따르면 …입니다.”
- 합계: “고객 진술 기준으로 두 내역의 합계는 1,000만원입니다. 실제 거래내역 확인은 별도로 필요합니다.”
- [ ] 완료 조건: 각 주장·합계가 해당 source/status/evidence 범위에만 근거함.
### P3-D — Regression / REST E2E

담당: B unit, Integration test, REST E2E 공동 검증. 선행: P3-A2/B/C2 연결 완료.

- [ ] B unit: 명확 답변 동일 목적 제외, ASKED 차단, 기억 안 남 보완, SKIPPED 정책.
- [ ] Integration/REST: 일반 CUSTOMER CHAT 부정, Answer→Fact→다음 추천; ANSWERED 제외만 의존하지 않음.
- [ ] B unit + Integration/REST: 300→30 정정, 충돌, 별도 300+700=1,000만원, 반복 송금 중복 합산 금지.
- [ ] B unit + Integration/REST: PROPOSED/CONFIRMED, 진술/직원 확인/BANK_RECORD/OFFICIAL_VERIFICATION.
- [ ] Integration/REST: Verification completed/pending/failed와 semantic scope.
- [ ] B unit + Integration/REST: provider failure 안전 fallback, multi-select, OTP/PIN/password 값 차단·제공 여부 허용.
- [ ] Integration/REST: 긴 context 최신 정보, revision/stale 후보, queue/dispatch 유지·자동 질문 전송 없음.
## 7단계 — A → B Semantic Contract

아래는 end-to-end 수용 기준이며, 계약 전체 소비가 확인되기 전 완료 표시하지 않는다.

- [ ] CALLER_CLAIM ≠ SYSTEM_FACT; CUSTOMER_STATEMENT ≠ VERIFIED_TRANSACTION.
- [ ] REQUESTED ≠ COMPLETED; CUSTOMER_REPORTED_COMPLETED ≠ VERIFIED_COMPLETED.
- [ ] UNKNOWN ≠ FALSE; NEGATIVE→POSITIVE 변환 금지.
- [ ] PROPOSED를 CONFIRMED처럼 표현하지 않고 REJECTED/SUPERSEDED는 현재 근거에서 제외.
- [ ] polarity/modality/action_state/검증 수준 및 source/evidence/lineage 보존.
- 검증 수준은 A의 실제 claim_status/action_state와 연결하며 문서 예시 verification_status를 구현 필드로 가정하지 않는다.
- [ ] A의 미확인 Fact를 질문 과제로 소비; correction/conflict가 있으면 관계 우선.
- [ ] BANK_INTERNAL의 Customer Copilot 유출 금지 end-to-end 검증.
## 8단계 — A 파트 요청사항

- [ ] 일반 CUSTOMER CHAT의 negation/uncertainty typed 구조화 보강.
- [ ] cross-turn “300만원→아니요 30만원” 정정 관계 제공.
- [ ] 별도 송금·반복 진술·누적/최종 금액 구분 및 기존 Fact 활용 correction/conflict 판단.
- 이미 존재하는 Atom 극성·modality·금액 role/direction·Atom lineage는 재구현 요청하지 않는다.
- 근거: 메시지 extractor의 기존 Fact 미활용, Relation의 CORRECTS 부재·동일 turn 규칙.
## 9단계 — Integration Requirements 요약

담당: Integration. B 상태: Requirement 정의 / 연결 대기. 아래 공유 파일은 B 수정 대상이 아니다.

- [ ] `main.py`·`case_retrieval.py`: typed Fact/Gap/관계 전달, CHAT 키워드·PROPOSED 존재 기반 제외 교체.
- [ ] `contracts/ai_internal/case_snapshot.py`: 의미·출처·확인·관계 입력 보존.
- [ ] `contracts/ai_internal/work_card.py`·`mvp_workflow.py`: multi-select/source/semantic 목적/이전 질문/sufficiency 연결.
- [ ] `contracts/ai_internal/case_copilot.py`·Bank payload: typed provenance·완료 검증·현재 money event grounding.
- [ ] `main.py::filter_contextual_questions`: baseline 보완 허용; `update_case_verification`: mapper 운영 연결.
- [ ] repository/MySQL: 최종 queue 정책·revision 보호; 공유 frontend 타입·질문 UI 호환 연결.
- [ ] truncation·cache에서 핵심 최신 상태 보존, 저장→B 입력→최종 추천 전체 검증.
- C 확인: Summary/Report 금액·반환·확정 합계 정책 및 projection revision 소비는 C/Integration 소유.
## 10단계 — P4 Verification Recommendation

- [ ] 사건별 확인 대상·공식 확인 방법·추천 이유 고도화; 추천을 실행/결과로 표현하지 않음.
- 기본 mapper wiring·완료 결과 grounding은 P4까지 미루지 않고 P3-I에서 처리.
## 11단계 — P5 Official Corpus / RAG 필요성 검증

- [ ] 실제 검색 부족 사례로 필요성 평가; 공식 출처·최신성·provenance 검증.
- P3 필수 선행 조건 아님. Agent/Vector DB 등 새 기술을 임의 도입하지 않는다.
## 12단계 — P7 B 전체 E2E

- [ ] Case→질문 검토/전송→답변→Fact→다음 추천→검증→역할별 Copilot 전체 흐름 확인.
- 기존 P6 후반 Integration은 단일 후행 단계 대신 P3-I 및 단계별 연결로 앞당긴다.
## 13단계 — P8 UI Smoke Test

- [ ] 공유 UI 담당과 질문 편집·선택·답변·multi-select·오류·새로고침 확인; build와 별도 기록.
## 14단계 — P9 안정화 / 문서화

- [ ] 실제 검증 결과·잔여 문제·운영 오류·포트폴리오 근거 정리; 미검증 기능 완료 표시 금지.
## 품질 평가 지표

- [ ] Question Duplicate Rate, Critical Question Coverage, Answered-but-Unresolved Recovery.
- [ ] Customer/Bank Role Isolation, Unsupported Certainty Rate, Sensitive Question Block Rate.
- [ ] Correction Handling Accuracy, Verification Scope Accuracy, Provider Failure Fallback.
- [ ] Follow-up Question Appropriateness, Question Grounding, Context Freshness/stale recommendation.
- 전부 측정 전. dataset·분모·판정 기준·모델/prompt 버전과 함께 기록하며 수치 추정 금지.
## 현재 테스트 가능 범위

- [x] 정책·검증 mapper·grounding·Copilot directness/fact grounding/quality/progress 테스트 코드 존재.
- [x] General의 지원 답변 Fact·contextual 질문·queue 연결 테스트 코드 존재.
- [ ] typed 입력·cross-turn correction·동일 주제 follow-up·source-aware grounding 전체 검증.
- unit/provider mock, API Integration, 실제 REST/LLM, MySQL, 브라우저 검증은 구분한다.
## 최근 테스트 / 검증 기록

- 기존 실행 기록(사용자 제공): 2026-09-17 최신 main→dev 통합 후 103 tests PASS, 42 subtests PASS, 0 failures.
- FastAPI/Starlette/anyio deprecation warning 존재; 기능 실패와 구분. 실행 환경·명령은 이번에 독립 확인하지 않음.
- 이번 문서 작업: 테스트·서버·API·DB·브라우저 실행 없음. 위 기록은 새 검증 결과가 아니다.
## 현재 구현 기록

- P0: 지원 답변의 typed PROPOSED Fact 연결. P1: helper 및 LLM normalization. P2: 역할·품질·산술 보조.
- 최신 A: Atom별 typed Fact·근거·grounded validator, snapshot revision·추가 projection 존재.
- B 한계: merge는 일부 key의 display 문자열, Bank 입력은 string[]; 추가 projection도 QUESTION_PLAN에서 문자열화.
- 문서/코드 차이: A 체크리스트의 money_events 공통 연결 표시는 Bank의 typed 소비 완료로 해석하지 않는다.
## 다음 작업

- [ ] 1순위 P3-A1 state evaluator·unit 설계/구현, 병행 P3-C1 표현 evaluator.
- [ ] P3-I 계약 합의·Integration 연결 → P3-A2 → P3-B/P3-C2 → P3-D.
- B 서비스만 수정하며 adapter의 C projection 영향은 사전 협의; 공용 파일 임의 변경 금지.
## 변경 시 기록 규칙

- 코드·근거 테스트·실행 환경/명령·날짜·결과·warning·잔여 범위를 함께 기록.
- 부분 완료는 하위 항목만 체크; helper/운영 연결 및 진술/객관 검증을 분리한다.
- A/B/Integration/C 담당과 의존성을 유지하고 실제 연결·검증 전 체크하지 않는다.
- 이번 작성의 유일한 변경 파일은 이 문서; CURRENT_STATUS/README/A 문서·코드·설정은 수정하지 않는다.
