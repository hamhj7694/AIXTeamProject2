# CSR Judge Web

심사위원이 CSR의 목적과 실제 구현 구조를 짧게 이해한 뒤 기존 MVP를 체험하도록 돕는 독립 정적 웹이다.

- 공식 URL: `/judge/`
- 직접 파일 URL: `/judge/index.html`
- 내부 이동: `/judge/#architecture` 같은 hash만 사용
- 기존 CSR 진입: `/`를 새 탭으로 연다
- `data/auto/`: 실제 코드에서 Scanner가 생성한 기술 사실
- `data/curated/`: 서비스 목적, 쉬운 설명, TARGET SERVICE와 기대효과

기존 React 앱, API, Nginx와 Docker 설정을 import하거나 수정하지 않는다.
