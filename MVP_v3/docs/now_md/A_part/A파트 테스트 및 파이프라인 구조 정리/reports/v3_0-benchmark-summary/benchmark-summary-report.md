# v3.0 기준선 데이터 요약

Benchmark: `benchmark_v1.0`  
Case: `30`건  
Atomic fact: `270`건

## 분포

| 구분 | 분포 |
|---|---|
| 시나리오 | {'HIGH': 10, 'MIXED': 10, 'LOW': 10} |
| Semantic key | {'claimed_organization': 30, 'claimed_role': 30, 'transfer_requested': 30, 'transfer_amount': 30, 'otp_shared': 30, 'password_shared': 30, 'remote_app_requested': 30, 'isolation_family': 30, 'isolation_bank_staff': 30} |
| 패널 섹션 | {'IMPERSONATION_CONTACT': 60, 'FRAUD_INDICATORS': 120, 'LOSS_EXPOSURE': 90} |
| Visibility | {'BANK_INTERNAL': 270} |
| 중요도 | {'HIGH': 180, 'CRITICAL': 90} |

## 해석

이 자료는 v3.1 평가의 비교 기준선과 annotation 범위를 확인하기 위한 요약입니다.
통화 원문과 민감 literal은 export하지 않았으며, v3.1 신규 lexical·expression·relation·signal 정답은 포함하지 않습니다.
