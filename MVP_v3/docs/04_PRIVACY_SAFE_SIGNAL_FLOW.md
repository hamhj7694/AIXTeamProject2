# 원문 비저장 분석·Case 생성 흐름

## 목적

통화 원문 전체를 Shared Case에 보존하지 않아도, 은행 담당자와 고객이 필요한 위험 맥락을
공유하고 AI가 초기 대응을 지원할 수 있게 한다. 이 문서는 Frontend, General API, AI API,
ML/피처 추출 담당자가 함께 사용하는 데이터 경계다.

## 처리 흐름

```text
Frontend 통화 텍스트 입력 (메모리)
  → POST /api/cases/analyze
  → AI API: 일시적 문장 분리 / 이벤트 추출 / ML 위험 점수 계산
  → 구조화 신호 projection
       event family · subtype · 기관군 · turn · 금액 집계 · 수치형 feature
  → Context LLM: 구조화 신호 payload만으로 요약·주장·다음 조치 생성
  → General API: 원문 제거 projection + Initial Report 생성
  → DB / Shared Case
  → Frontend: 최고 위험 점수 1개 + 핵심 신호 + 초기 Case 정리
```

## 원문 경계

| 단계 | 원문 허용 | 저장 |
| --- | --- | --- |
| Frontend 입력 중 | 예, 사용자 브라우저 메모리 | 아니오 |
| `/api/cases/analyze` 요청 처리 | 예, 추출·ML 처리 시간에 한함 | 아니오 |
| 이벤트/ML 결과 | 아니오, 구조화 신호만 | 예 |
| Context LLM | 아니오 | 구조화 결과만 |
| Shared Case / 보고서 / API read | 아니오 | 예 |

신규 Case의 `case_inputs.input_text`는 빈 문자열이며, `analysis_segments.segment_text`는
원문이 아니라 `검찰·수사기관 사칭`, `송금·이체 요구` 같은 안전한 신호 라벨이다.

## 최소 신호 계약

```json
{
  "source": "STRUCTURED_RISK_SIGNALS_ONLY",
  "signal_count": 3,
  "signals": [
    {
      "signal": "검찰·수사기관 사칭",
      "event_family": "IMPERSONATION",
      "subtype": "PROSECUTION",
      "impersonation_group": "PUBLIC_AGENCY",
      "turn": 1
    },
    {
      "signal": "송금·이체 요구",
      "event_family": "MONEY_MOVEMENT",
      "subtype": "TRANSFER",
      "turn": 3
    }
  ]
}
```

`turn`은 순서만 나타내며 원문 문장을 복원하는 키가 아니다. 금액은 필요한 경우
`amount_krw` 숫자 또는 bucket으로만 전달한다. 계좌번호, 전화번호, 이름, 인용문은 넣지 않는다.

## 화면 계약

- Home 분석 결과: 구간별 원문/점수 목록을 제공하지 않는다.
- 표시값: `최고 위험 점수`, 핵심 신호 라벨, LLM 초기 요약, 상대 주장(신호 기반), 권장 조치,
  미확인 정보.
- 분석이 끝나면 Home textarea 값을 비워 원문을 프론트 상태에 오래 남기지 않는다.
- Case Room은 동일 Case ID를 재조회하며 원문을 렌더하지 않는다.

## 구현 책임

- **ML/통화 연동**: 원문 또는 통화 플랫폼의 제한된 신호를 최소 피처 계약으로 변환한다.
- **AI API**: 신호만 Context LLM에 전달하고, LLM이 인용문·개인정보를 만들어 내지 않도록 한다.
- **General API**: persistence 직전 안전 projection을 강제한다. 클라이언트가 보낸 원문을
  repository에 직접 전달해서는 안 된다.
- **Frontend**: 원문을 분석 입력 이외의 화면 상태·로그·URL에 넣지 않는다.

## 남은 운영 과제

1. 기존 DB에 이미 저장된 원문의 보존 기간과 삭제 절차를 보안 담당자와 확정한다.
2. production ML extractor가 이 문서의 payload만 제출하도록 versioned schema를 고정한다.
3. PII 재식별 가능성 검사, 접근 감사, retention job을 운영 환경에 추가한다.
