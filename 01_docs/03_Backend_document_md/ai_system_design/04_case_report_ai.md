# Case Report AI 설계

> 현재 상태: PARTIAL. 규칙 기반 초기 LIVE Report Builder와 Draft Contract Fixture는 있으나 AI initialize/update/finalize·Impact Router는 미구현이다. 향후 책임은 B=lee다.

## 1. 역할

하나의 Case에 누적된 사실·근거·조치·미확인사항을 LIVE Section으로 관리하고, 사건 종료 시 전체 이력 기반 FINAL Report를 생성한다.

## 2. Section

```text
summary
risk_context
transfer_status
exposure_status
verification_status
current_actions
unresolved_items
next_checks
```

## 3. API

```text
POST /ai/reports/initialize
POST /ai/reports/update
POST /ai/reports/finalize
```

## 4. Update 입력·출력

```json
{
  "case_id": "VP-014",
  "base_report_version": 12,
  "changed_scope": {
    "event_type": "VERIFICATION_UPDATED",
    "source_ids": ["ver_18"]
  },
  "current_sections": []
}
```

```json
{
  "patches": [{
    "section_key": "verification_status",
    "operation": "UPSERT",
    "base_section_version": 3,
    "content": {},
    "source_ids": ["ver_18", "rag_ev_33"]
  }]
}
```

`patches`에 없는 Section은 변경하지 않는다.

## 5. Impact Routing

가능한 Event→Section 매핑은 일반 규칙 코드로 먼저 계산한다. 의미 충돌이나 복합 변화처럼 규칙만으로 판단하기 어려운 경우에만 AI Impact 판단을 사용한다.

| Event | 기본 Section |
|---|---|
| 송금 답변 | `transfer_status`, `unresolved_items` |
| 개인정보 답변 | `exposure_status`, `next_checks` |
| Verification 결과 | `verification_status` |
| Bank Action | `current_actions` |
| Risk Feature 변화 | `risk_context`, `summary` |

## 6. FINAL 원칙

- 전체 Case 이력을 다시 읽는다.
- LIVE Section을 단순 이어 붙이지 않는다.
- 최종 사실·Timeline·Verification·근거·조치·결과를 포함한다.
- 기존 확정본을 덮어쓰지 않고 Revision을 추가한다.

## 7. 평가

- Source와 Claim 추적 가능성
- 금액·송금상태·기관·조치 사실 보존
- 변경되지 않은 Section 재작성 여부
- Section 간 모순
- FINAL 전체 이력 누락
- Patch 크기·Latency·토큰 비용

## 8. 완료조건

- [ ] Initialize/Update/Finalize Schema 확정
- [ ] 규칙 기반 Impact Router 구현
- [ ] Section Version Conflict 테스트
- [ ] Source ID 연결 테스트
- [ ] Section 한 개만 갱신되는 E2E
- [ ] Immutable FINAL Revision 테스트
