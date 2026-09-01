# Voice Intelligence Pipeline 설계

## 1. 역할

직원과 고객의 음성상담을 STT로 변환하고 Final Segment 단위로 Case 변화를 추출한다. 범용 자율 Agent가 아니라 Streaming Pipeline이다.

## 2. 흐름

```text
RTC Audio Track
  ↓
Streaming STT
  ├─ Partial → 화면 표시만
  └─ Final → Backend 저장
               ↓
        Voice Delta Analyzer
          ├─ 신규 사실
          ├─ Feature/Risk 변화
          ├─ 기존 사실 충돌
          └─ 후속질문 후보
               ↓
        Report Impact/Section Patch
```

상담 종료 시 전체 Final Transcript로 요약과 미확인사항을 생성한다.

## 3. 구성

| 구성 | 구현 방식 |
|---|---|
| RTC Session·Join Token | 일반 Backend/RTC Provider |
| Streaming STT | STT Model/Provider |
| Speaker Handling | Track ID 우선, 필요 시 Diarization |
| Delta Analyzer | Case Intelligence AI 재사용 가능 |
| Consultation Summary | LLM 구조화 요약 |

## 4. API

```text
WS /ai/stt/stream/:sessionId 또는 동등 API
POST /ai/voice/analyze-delta
POST /ai/voice/summarize
```

## 5. Transcript Schema

```json
{
  "segment_id": "seg_...",
  "session_id": "vs_...",
  "case_id": "VP-014",
  "sequence": 12,
  "speaker": "CUSTOMER",
  "text": "...",
  "is_final": true,
  "started_at": "...",
  "ended_at": "..."
}
```

## 6. 처리 원칙

- DB는 Final Segment 중심으로 저장한다.
- 별도 Audio Track/participant ID가 있으면 이를 화자 근거로 사용한다.
- Mixed Audio일 때만 Diarization을 사용한다.
- `segment_id`와 sequence로 중복·순서 역전을 처리한다.
- 원본 음성 URL과 Provider Secret을 Bundle/Event/localStorage에 넣지 않는다.

## 7. 실패·성능

- STT Stream 재연결 시 마지막 확정 sequence부터 복구한다.
- Partial 실패가 Final 저장을 오염시키지 않는다.
- Delta 분석 실패 시 Transcript는 유지하고 분석 Job만 재시도한다.
- 호출 빈도는 Final Segment 묶음 또는 시간 Window로 조정할 수 있다.

## 8. 평가·완료조건

- [ ] STT WER 또는 합의 지표
- [ ] Speaker 정확도
- [ ] Partial/Final·중복·순서 역전 테스트
- [ ] 신규 사실·충돌 추출 평가
- [ ] 상담 종료 Summary Contract
- [ ] 원본 음성 Retention 정책
- [ ] Transcript 한 건 Append E2E
