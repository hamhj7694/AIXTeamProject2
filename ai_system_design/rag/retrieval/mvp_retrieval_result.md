# MVP Retrieval 결과

| Question | Expected | Top-3 | Result |
|---|---|---|---|
| Q01 | VER-001, VER-002 | VER-001, VER-002, REC-001 | PASS |
| Q02 | VER-001, VER-002 | VER-001, VER-002, SEC-001 | PASS |
| Q03 | REC-001 | REC-001, VER-001, VER-002 | PASS |
| Q04 | REP-001, REP-002 | REC-001, REP-001, VER-001 | PASS |
| Q05 | REC-001, REC-002 | REC-001, REC-002, VER-002 | PASS |
| Q06 | SEC-001, VER-002 | VER-002, SEC-001, VER-001 | PASS |
| Q07 | SEC-002 | SEC-002, VER-002, REP-001 | PASS |
| Q08 | REP-001, REP-002 | REC-001, REP-001, REC-002 | PASS |

- PASS: 8/8
- FAIL: 없음
- 이 결과는 검색 적합성만 확인한다. Q02·Q03의 PARTIAL Coverage를 완전한 답변으로 해석하지 않는다.
