# 원문 비저장 분석·Case 생성 흐름

## 목적

통화 원문 전체를 Shared Case에 보존하지 않아도, 은행 담당자와 고객이 필요한 위험 맥락을
공유하고 AI가 초기 대응을 지원할 수 있게 한다. 이 문서는 Frontend, General API, AI API,
ML/피처 추출 담당자가 함께 사용하는 데이터 경계다.

## 목표 처리 흐름과 데모 범위

```text
[온디바이스·통신사·ASAP/FDS 분석 계층]
  통화 원문 이해·화자 분리·의미 구조화
  → versioned AnalysisEnvelope
       turn · speaker/actor/target/reporter · Atom · Mention · Relation
       기관/지점/인물/직책 · 관계/호칭 · 행동/금액/기한 · 빈도/confidence
  → CSR AI API: Envelope 검증 + 구조화 신호 기반 문장 생성
  → General API: 원문 제거 projection + Initial Report 생성
  → DB / Shared Case
  → Frontend: 상세 정황 + 역할·근거 metadata + 초기 Case 정리
```

현재 프로젝트는 실제 통신사·온디바이스 계층을 연동하지 않는다. Frontend 텍스트 입력과 데모 분석기가 그 경계를 모사한다.

```text
데모 입력 → 데모 분석기 → AnalysisEnvelope → 동일 CSR 분석 코어
```

## 원문 경계

| 단계 | 원문 허용 | 저장 |
| --- | --- | --- |
| 목표 CSR Frontend·General API | 아니오 | 아니오 |
| 외부 온디바이스·통신사 분석 계층 | 개념상 CSR 범위 밖이며 이번 데모에는 미연동 | CSR에 저장하지 않음 |
| 데모 Frontend 입력 중 | 예, 사용자 브라우저 메모리 | 아니오 |
| 데모 `/api/cases/analyze` 처리 | 예, 데모 Envelope 변환 시간에 한함 | 아니오 |
| `AnalysisEnvelope`·이벤트·ML 결과 | 아니오, 구조화 신호만 | 예 |
| Context LLM | 아니오 | 구조화 결과만 |
| Shared Case / 보고서 / API read | 아니오 | 예 |

신규 Case의 `case_inputs.input_text`는 빈 문자열이며, `analysis_segments.segment_text`는
원문이 아니라 `검찰·수사기관 사칭`, `송금·이체 요구` 같은 안전한 신호 라벨이다.

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
- 분석이 끝나면 Home textarea 값을 비워 원문을 프론트 상태에 오래 남기지 않는다.
- Case Room은 동일 Case ID를 재조회하며 원문을 렌더하지 않는다.

## 데모 구현 책임

- **데모 분석기**: 실제 온디바이스·통신사 계층을 모사해 원문을 화자·관계·정황의 versioned Envelope로 변환한다.
- **AI API**: Envelope만 Context LLM에 전달하고, LLM이 역할 metadata를 수정하거나 입력에 없는 사실을 만들지 못하게 한다.
- **General API**: persistence 직전 안전 projection을 강제한다. 클라이언트가 보낸 원문을
  repository에 직접 전달해서는 안 된다.
- **Frontend**: 원문을 분석 입력 이외의 화면 상태·로그·URL에 넣지 않는다.

## 남은 데모 과제

1. 데모 입력 → Envelope → Case 생성의 브라우저 E2E와 원문 비저장을 확인한다.
2. 역할 귀속·구체 명칭·시간 관계 fixture를 확대한다.
3. GPT 문장 품질·비용·latency·출력 잘림을 동일 fixture로 측정한다.
4. 병합 기준은 `33_ANALYSIS_ENVELOPE_FREEZE_CONTRACT.md`, 후속 작업은 `34_ANALYSIS_ENVELOPE_INTEGRATION_BACKLOG.md`를 따른다.

실제 통신사·온디바이스·ASAP/FDS 연결과 외부 서비스 인증은 이번 데모 범위 밖이다.
