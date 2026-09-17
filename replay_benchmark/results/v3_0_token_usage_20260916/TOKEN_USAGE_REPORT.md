# v3.0 Token Usage Baseline

Official commit: `071fb512ce42a570b0bcf585041eac6f31c2fb1c`  
Provider: OpenAI · Model: `gpt-4o-mini` · Repetitions: 3

| Feature | Avg input | Avg output | Avg total | Avg calls | Status |
|---|---:|---:|---:|---:|---|
| Case Creation / Diagnosis | 3,001.33 | 525.00 | 3,526.33 | 6.00 | LIVE |
| Bank Staff Chat AI | 533.00 | 192.33 | 725.33 | 1.00 | LIVE |
| Customer Confirmation Question AI | 736.00 | 133.00 | 869.00 | 1.00 | LIVE |
| Verification AI | 737.00 | 140.33 | 877.33 | 1.00 | LIVE |
| Action / Work AI | 736.00 | 156.33 | 892.33 | 1.00 | LIVE |
| Customer Chat AI | 1,843.00 | 106.33 | 1,949.33 | 1.00 | LIVE |
| Final Report AI | 574.00 | 241.00 | 815.00 | 1.00 | LIVE |

One complete seven-feature pass averages **9,654.67 total tokens** and **12 provider calls**. Usage values come from OpenAI response metadata, not estimates. No production source, frozen benchmark, DB, commit, or push was changed.

Evidence: `token_usage_runs.json`, `token_usage_calls.json`, `../token_benchmark/token_fixtures_v1.json`.
