# Backend runtime

General API, AI API, Database 등 백엔드 실행 환경의 Dockerfile과 Compose 설정을 둔다. 비밀값은 커밋하지 않고 환경변수 또는 별도 secret 관리 수단으로 주입한다.

현재 Dockerfile과 Compose는 아직 없다. 향후 C=ham이 통합 실행환경을 책임지고 A=eom·B=lee가 각 서비스의 실행 명령, health check, 필수 환경변수를 Review한다.

