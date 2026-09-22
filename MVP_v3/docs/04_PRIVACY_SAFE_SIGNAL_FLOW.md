# 원문 보관·AI 비접근 분석·Case 생성 흐름

## 목적

데모에서는 통화 원문을 Case 입력으로 보관하되, 원문은 **최초 분석이 완료된 결과 화면에서만 일시적으로 확인**할 수 있다. Case Room 재진입·Case 목록/상세·초기 분석 결과 재조회에서는 원문을 반환하지 않는다.
다만 저장된 원문은 CSR 지원 AI·Context AI의 입력으로 재사용하지 않고, 분석 시점에만 분석
어댑터가 읽는다. 이 문서는 Frontend, General API, AI API, ML/피처 추출 담당자가 함께
사용하는 데이터 경계다.

## 목표 처리 흐름과 데모 범위

```text
[데모 분석 계층]
  통화 원문 이해·화자 분리·의미 구조화 (분석 시점에만 원문 접근)
  → versioned AnalysisEnvelope
       turn · speaker/actor/target/reporter · Atom · Mention · Relation
       기관/지점/인물/직책 · 관계/호칭 · 행동/금액/기한 · 빈도/confidence
  → CSR AI API: Envelope 검증 + 구조화 신호 기반 문장 생성
  → General API: 구조화 projection + Initial Report 생성
  → DB / Shared Case
  → Frontend: 상세 정황 + 역할·근거 metadata + 초기 Case 정리 + 최초 분석 결과 화면에서만 데모 원문 확인
```

현재 프로젝트는 실제 통신사·온디바이스 계층을 연동하지 않는다. Frontend 텍스트 입력과 데모 분석기가 그 경계를 모사한다.

```text
데모 입력 → 데모 분석기 → AnalysisEnvelope → 동일 CSR 분석 코어
```

## 원문 경계

| 단계 | 원문 허용 | 저장·재사용 |
| --- | --- | --- |
| 목표 CSR 운영 AI·Context AI | 아니오 | 저장 원문을 재사용하지 않음 |
| 외부 온디바이스·통신사 분석 계층 | 개념상 CSR 범위 밖이며 이번 데모에는 미연동 | 데모에서는 General API가 입력을 보관 |
| 데모 Frontend 입력 중 | 예 | Case 생성 요청에 전달 후 화면 상태는 비움 |
| 데모 `/api/cases/analyze` 처리 | 예, 분석·Envelope 변환 시간 | `case_inputs.input_text`에 데모 원문 보관 |
| `AnalysisEnvelope`·이벤트·ML 결과 | 아니오, 구조화 신호만 | 예 |
| Context LLM | 아니오 | 구조화 결과만 |
| Shared Case / 보고서 / API read | 원문 반환 금지 | 원문과 구조화 결과를 분리 보관 |

신규 Case의 `case_inputs.input_text`에는 데모 입력 원문이 저장되고 `input_type`은
`VOICE_TRANSCRIPT`로 기록된다. 반면 `analysis_segments.segment_text`와 `diagnosis_json`은
원문이 아니라 `검찰·수사기관 사칭`, `송금·이체 요구` 같은 구조화 신호·정규화 라벨만 가진다.
저장된 `input_text`는 최초 분석 결과 화면의 일회성 표시를 위한 원장으로만 보관하며,
일반 Case read/list/bundle API에는 반환하지 않는다. Case Copilot·Context Snapshot·지원
질문 생성 입력에도 포함하지 않는다.

## Analysis Envelope 최소 예시

```json
{
  "schema_version": "analysis-envelope.v1",
  "source": "DEMO_ADAPTER",
  "source_text_included": false,
  "reference_time": "2026-09-19T13:00:00+09:00",
  "timezone": "Asia/Seoul",
  "turn_count": 2,
  "turns": [
    {
      "turn_id": 1,
      "sequence_index": 1,
      "speaker_role": "SUSPECTED_PARTY",
      "speaker_confidence": 0.94,
      "normalized_summary": "서울지검 수사관 사칭 정황"
    },
    {
      "turn_id": 2,
      "sequence_index": 2,
      "speaker_role": "SUSPECTED_PARTY",
      "speaker_confidence": 0.93,
      "normalized_summary": "15시까지 안전계좌 송금 요구"
    }
  ],
  "events": [],
  "semantic_atoms": [],
  "semantic_mentions": [],
  "semantic_relations": [],
  "context_features": {}
}
```

`turn_id`는 순서와 lineage만 나타내며 원문 문장을 복원하는 키가 아니다. 금액은 필요한 경우
`amount_krw` 숫자 또는 bucket으로 전달한다. 계좌번호, 전화번호, 인증 secret, 전체 인용문은 넣지 않는다.

원문에서 확인된 짧고 정규화된 기관·지점·인물·직책·관계 명칭은 Case 대응에 필요한 경우 전용 필드에 보존할 수 있다. 전체 문장이나 주변 문맥을 이름 필드에 복사하지 않으며, 법무·개인정보 정책과 masking·retention 기준을 적용한다.

## 화면 계약

- Home 분석 결과: 구간별 원문/점수 목록을 제공하지 않는다.
- 표시값: 핵심 신호, LLM 초기 요약, 보이스피싱 의심 인물의 주장·요구·압박, 고객 진술·행동, 권장 조치,
  미확인 정보.
- 분석이 끝나면 Home textarea 값을 비워 입력 컨트롤에 원문을 오래 남기지 않는다.
- 분석 결과의 `데모 입력 원문 확인` 영역은 최초 분석 응답 직후의 transient 입력만 표시한다. Case Room 재조회에서는 이 영역을 표시하지 않는다.
- Case Room의 Copilot·Context 패널은 구조화 결과만 재조회하며 저장 원문을 렌더하거나 AI에 전달하지 않는다.

## 데모 구현 책임

- **데모 분석기**: 실제 온디바이스·통신사 계층을 모사해 원문을 화자·관계·정황의 versioned Envelope로 변환한다.
- **AI API**: Envelope만 Context LLM에 전달하고, LLM이 역할 metadata를 수정하거나 입력에 없는 사실을 만들지 못하게 한다.
- **General API**: 원문은 `case_inputs.input_text`에 데모 보관하되, `project_diagnosis_for_case`로
  구조화 payload에서 제거하고 AI 지원 계약에는 전달하지 않는다.
- 레거시 `voice-sessions/.../transcript` 등록·조회 경로는 410으로 폐기했다. 이는 분석 요청으로
  보관되는 단일 Case 입력과 별개의 다중 segment 저장 API이며, 중복 저장 경로로 사용하지 않는다.
- **Frontend**: 원문을 URL·로그·AI 지원 요청·Case read 응답에 넣지 않고, 최초 분석 결과 화면에서만 표시한다.

## 남은 데모 과제

1. 데모 입력 → Envelope → Case 생성의 브라우저 E2E와 `case_inputs` 보관·AI 지원 입력 제외를 확인한다.
2. 역할 귀속·구체 명칭·시간 관계 fixture를 확대한다.
3. GPT 문장 품질·비용·latency·출력 잘림을 동일 fixture로 측정한다.
4. 병합 기준은 `33_ANALYSIS_ENVELOPE_FREEZE_CONTRACT.md`, 후속 작업은 `34_ANALYSIS_ENVELOPE_INTEGRATION_BACKLOG.md`를 따른다.

실제 통신사·온디바이스·ASAP/FDS 연결과 외부 서비스 인증은 이번 데모 범위 밖이다.
