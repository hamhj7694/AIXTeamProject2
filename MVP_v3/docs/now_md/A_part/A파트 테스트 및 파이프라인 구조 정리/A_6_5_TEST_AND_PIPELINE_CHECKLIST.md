# A파트 6.5단계 실행 체크리스트

상태 기준일: 2026-09-16  
최종 업데이트: 2026-09-17  
목적: 1~6단계 Context Pipeline의 재현성·품질·성능·저장·패널 연동을 내부적으로 검증

현재 상태: **부분 완료**. `[x]`는 구현·문서화·샘플 실행까지 확인한 항목이며,
`[ ]`는 정답 annotation, 실제 DB/E2E 실행 또는 추가 자료가 필요한 항목이다.

## A. 기준 데이터와 실행 환경

- [x] privacy-safe fixture set 버전 고정
- [ ] Atom/Relation/Signal/Fact/Statement 정답 annotation 작성
- [x] 공식 Gold 3종 등록 및 기존 partial gold 정답지 제거
- [x] v3.0 benchmark Case 30건·atomic fact 270건 분포 요약 생성
- [x] 대표 Case 3건 사람 검토용 queue·안내 파일 정리
- [ ] 다중 금액·다중 요구·기관·역할·OTP 유형·긴급성·부정·조건 fixture 포함
- [ ] 동일 code revision·model artifact·환경 변수 기록
- [ ] fixture에 원문·민감 literal이 export되지 않는지 확인

## B. 추출 AI 평가

- [x] Precision·Recall·F1 자동 평가기 구현
- [ ] Event decomposition precision·recall·F1 실제 산출
- [ ] v3.0과 직접 비교 가능한 지표의 v3.1 재집계
- [x] v3.0 baseline·v3.1 현재 상태 비교 JSON·한국어 보고서 생성
- [x] v3.0 benchmark 요약 JSON·한국어 보고서 생성
- [x] 정답 annotation 없이 구조 지표(Event→Atom coverage·Relation/Signal lineage) 산출
- [ ] Semantic Atom class·predicate precision·recall·F1
- [ ] critical semantic slot coverage
- [ ] observed lexical cue surface/code 보존율
- [ ] expression/pragmatic feature 보존율
- [ ] 다중 금액·요구·주장 separate extraction recall
- [ ] UNKNOWN·NEGATIVE·CONDITIONAL·action state 보존율
- [ ] Atom fingerprint 재실행 일관성

## C. 점검 AI 평가

- [ ] 발동 조건별 fixture와 기대 상태 매핑
- [ ] `PASS / NEEDS_REVIEW / REEXTRACTION_REQUIRED` 판정 기준 확인
- [ ] 누락·혼합·unsupported lexical·privacy·lineage 오류 탐지율
- [ ] 오탐·미탐 confusion matrix 작성
- [ ] human review 결과와 점검 AI 결과 비교
- [ ] targeted re-extraction 누락 회복률 측정
- [ ] targeted re-extraction 불필요 변경률 측정
- [ ] 감사 결과가 원본 분석 결과를 직접 덮어쓰지 않는지 확인

## D. 최종 Feature와 DB 저장

- [ ] Atom→Relation/Signal lineage 보존율
- [ ] Atom→Fact one-to-one 및 다중 값 separate projection 확인
- [ ] 합산 값과 개별 값의 aggregation loss 측정
- [x] DB transaction success·rollback 관련 회귀 테스트 실행
- [x] retry·idempotency 관련 회귀 테스트 실행
- [x] revision·supersede·conflict 관련 회귀 테스트 실행
- [ ] raw transcript·민감 literal 비보관 검사
- [ ] `BANK_INTERNAL`과 고객 visibility 격리 검사

## E. 문장화 의미 일치성

- [ ] semantic slot preservation rate
- [ ] action state·claim status 일치율
- [ ] polarity·modality·unknown 보존율
- [ ] observed term specificity preservation
- [ ] unsupported lexicalization·semantic broadening rate
- [ ] 원문 자체를 보관하지 않는 annotation 기반 semantic fidelity 점수
- [ ] Relation 없는 Fact의 인과·목적 결합 차단
- [ ] 사건 요약·확인 질문의 evidence scope 제한

## F. 은행 화면·Case Room E2E

- [ ] 실제 API의 `analysis-result created` 응답 확인
- [ ] 기존 우측 패널 7개 섹션으로 Fact가 올바르게 매핑되는지 확인
- [ ] 직원용 문장과 근거·상태 라벨 표시 확인
- [ ] 세부 Atom code/개발자용 내부 label이 운영 패널에 노출되지 않는지 확인
- [ ] 입력 텍스트부터 Case Room 생성까지 성공률·처리 시간 측정
- [ ] AI 실패·부분 성공·재시도 시 사용자 상태와 DB 상태 일치 확인

## 최근 실행 기록

- General API 저장·패널·projection·6.5 도구 회귀 테스트: `21 passed`
- AI Atom·lexical·audit·context safety 회귀 테스트: `52 passed`
- General API transaction·transition·context display 회귀 테스트: `25 passed`
- 샘플 artifact privacy scan: `PASS`
- 2026-09-17 AI API readiness: provider configured `true`
- 2026-09-17 live 분석 시도: `APIConnectionError`로 provider 연결 실패, 분석 결과 미생성

## G. 자료와 재현성

- [x] 개발자용 구조 JSON export 생성기 구현
- [x] 한국어 사람이 읽는 보고서형 Markdown 생성기 구현
- [x] 표와 Mermaid pipeline 그래프를 보고서에 포함
- [x] 샘플 결과(`reports/sample-20260916/`) 생성
- [x] 샘플 구조 지표 보고서 생성(`PENDING_HUMAN_ANNOTATION` 명시)
- [x] JSON artifact privacy scan 구현 및 샘플 PASS 확인
- [x] 동일 결과 비교용 Atom fingerprint/count diff 도구 구현
- [ ] 품질 지표 JSON export 생성
- [ ] pipeline/lineage/funnel 도표 생성
- [ ] 실행 명령과 환경 정보 기록
- [ ] 이전 실행과 fingerprint·지표 diff 생성
- [ ] 결과 파일 privacy scan 통과

## 산출물 완료 조건

6.5단계는 평균 점수만으로 완료 처리하지 않는다. critical slot 누락, 민감정보 유출,
상태 승격, orphan lineage, 잘못된 패널 매핑이 없고, 모든 지표와 JSON/도표 산출물이
동일 fixture로 재현될 때 완료로 판정한다.

## H. 6.5단계 최종 A파트 종합 보고서

- [x] 종합 보고서 목차·지표 표·그래프·판정 기준 템플릿 정의
- [ ] 1~6단계 구현 범위와 변경 파일 요약
- [ ] v3.0 baseline 대비 v3.1 비교표 작성
- [ ] 추출·감사·저장·문장화·패널 E2E 전체 지표 취합
- [ ] privacy·hard gate·오탐·미탐 결과 취합
- [ ] 알려진 한계와 다음 단계(B/C/통합) 권고 작성
- [ ] 한국어 공유용 최종 보고서 `FINAL` 판정

최종 보고서 초안/템플릿: `A_6_5_FINAL_A_PART_COMPREHENSIVE_REPORT.md`
## 2026-09-17 Latest reconciliation

This addendum records evidence-backed status only. Items without a raw artifact remain NOT RUN or BLOCKED.

### Completed
- [x] Official Gold fixtures and SHA-256 registration
- [x] v3.0 corrected-Gold 30-case projection audit
- [x] v3.0 token baseline: 7 features x 3 runs, 21 LIVE runs, 36 calls
- [x] Provider smoke / LIVE replay evidence and comparison documentation
- [x] Sample structural lineage evidence (Event -> Atom -> Relation/Context Signal)
- [x] All local servers stopped and verified OFF after measurement

### TODO before v3.1 comparison is publishable
- [ ] Freeze v3.1 raw structured output for 30 cases / 150 turns
- [ ] Run canonical + high-fidelity Gold mappings and case/category macro scores
- [ ] Measure status, polarity, UNKNOWN, correction resolution, and case pass/fail
- [ ] Measure relation accuracy, fact-lineage completeness, and section projection accuracy
- [ ] Execute contradiction, hallucination, and privacy hard gates
- [ ] Run DB persistence, pipeline completion, and browser/API E2E checks
- [ ] Repeat token/call/latency measurements three times and calculate token per correct critical fact
- [ ] Generate final metric JSON, diff artifacts, privacy scan, and Notion payload

Note: the earlier `APIConnectionError` entry above describes an initial failed attempt. It is superseded for connectivity by the later provider smoke / LIVE replay artifacts; it does not constitute a v3.1 full-score result.
> 최신 통합 기준은 같은 폴더의 `A_6_5_MASTER_CHECKLIST.md`다. 이 문서는 상세 항목과 과거 실행 이력을 보존하며, 현재 담당자·게이트·최종 상태는 마스터 체크리스트를 우선한다.
