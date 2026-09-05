# AWS Ubuntu EC2 배포 · P0-005

현재 **Phase 0 기반 배포 절차**다. 로컬 fresh MySQL migration, 두 API HTTP health,
실제 모델 load/inference와 /ready/ml, Frontend clean install/typecheck/build 및 정적 배포 계약을 검증했다.
복사본 fresh Python 3.11 venv에서도 원본 repo 읽기/네트워크 차단 상태의 모델 추론을 검증했다.
Ubuntu/Nginx/systemd 실행, LLM readiness, 제품 Scenario A/B, 최종 전체 standalone은 아직 미검증이다.
AI /ready/ml은 200이며 제품 /ready는 Conversational/Intake 미구현으로 503이다. ML 성공으로 제품 완료를 판단하지 않는다.

## 1. 서버 준비와 V4 복사

서버 OS 도구: Python 3.11 및 venv 지원, Node >=22.18, npm, MySQL 8, Nginx, curl.
서버에 Python 3.11이 없는 경우 운영체제에 맞는 설치를 먼저 수행한다(스크립트가 임의로 OS 저장소를 추가하지 않음).
승인된 배포 아카이브의 **MVP_v4만** `/home/ubuntu/MVP_v4`로 복사한다.
아카이브에서 `.venv`, `node_modules`, 실제 `.env*`(example 제외), `.cache`, runtime DB/uploads,
로그를 제외한다. 모델/prompt/migration/source/lockfile은 포함한다.
현재 승인 ML model과 adapter가 포함되어 있다. 모델 상태는 EXPERIMENTAL_SAMPLE이며 현재 기반 코드를 완성 MVP로 배포하지 않는다.

```bash
cd /home/ubuntu/MVP_v4
python3.11 -m venv .venv
.venv/bin/python -m pip install --cache-dir .cache/pip -r backend/requirements.txt
.venv/bin/python -m pip check
mkdir -p backend/data/uploads backend/data/vector_db
```

로컬 venv를 복사하지 않는다. runtime 파일 위치는 이 V4 root 내부여야 하며 경로가 밖으로 벗어나면 설정 검증이 실패한다.

## 2. 별도 V4 DB와 환경변수

운영자가 MySQL에 `csr_v4` DB와 해당 DB 전용 계정을 만든다. V3 DB/migration/계정 재사용 금지.
DB 이름은 `csr_v4`로 시작해야 migration이 허용된다. UTF8MB4를 사용한다.
운영자가 `.env.example`을 기준으로 `.env`를 직접 작성하고 읽기 권한을 제한한다.
Agent는 실제 파일 내용을 읽거나 생성하지 않는다. 아래 변수명만 전달한다.

```text
[USER_SECRET_REQUIRED]
DATABASE_URL
OPENAI_API_KEY (P2/P5 실제 AI 연결 시)
```

DATABASE_URL 형식은 `mysql+pymysql://<user>:<URL-encoded-password>@<host>:3306/csr_v4?charset=utf8mb4`.
APP_ENV=production, GENERAL_API_HOST=127.0.0.1, GENERAL_API_PORT=8100,
AI_API_HOST=127.0.0.1, AI_API_PORT=8101, AI_API_BASE_URL=http://127.0.0.1:8101을 사용한다.
OPENAI_MODEL/MAX_*는 현재 예약 변수이며 Phase 0에서는 AI 호출 또는 비용 제한 구현 완료를 의미하지 않는다.
Vite는 envDir=false로 env 파일을 읽지 않는다. GENERAL_API_BASE_URL은 로컬 개발 proxy용 프로세스 변수다.

systemd가 런타임에 EnvironmentFile을 주입한다. 앱/배포 검사 스크립트는 env 파일을 탐색하지 않는다.

## 3. Migration

```bash
cd /home/ubuntu/MVP_v4
sudo install -m 644 deploy/systemd/csr-v4-migrate.service /etc/systemd/system/csr-v4-migrate.service
sudo systemctl daemon-reload
sudo systemctl start csr-v4-migrate.service
sudo systemctl status csr-v4-migrate.service --no-pager
```

현재 migration 001은 `application_metadata`와 Alembic revision을 만든다. 업무 Entity는 Phase 1에 추가한다.
DB URL이 주입된 운영 shell에서는 `.venv/bin/python -m backend.scripts.migrate`도 가능하다.
실패 시 DB 연결값/SQL 인자를 로그에 출력하지 않는다. 자동 downgrade/기존 DB 삭제는 수행하지 않는다.

## 4. Frontend production build

```bash
cd /home/ubuntu/MVP_v4/frontend
npm ci --cache ../.cache/npm
npm run typecheck
npm test
npm run build
test -f dist/index.html
test -d dist/assets
```

빌드에 비밀값은 필요하지 않다. `deploy/scripts/build.sh`는 Python install, audit, tests, frontend install/build를 묶어 실행한다.
production browser는 `/api`만 사용한다. AI URL/개발 PC IP는 bundle에 포함하지 않는다.

## 5. Static 파일 배포

```bash
cd /home/ubuntu/MVP_v4
sudo install -d -m 755 /var/www/mvp_v4
sudo cp -a frontend/dist/. /var/www/mvp_v4/
sudo find /var/www/mvp_v4 -type d -exec chmod 755 {} \;
sudo find /var/www/mvp_v4 -type f -exec chmod 644 {} \;
```

이 위치에는 V4의 dist 산출물만 둔다. source, model, 실제 env는 복사하지 않는다.
이전 hashed assets는 열린 브라우저의 청크 요청을 위해 유지할 수 있다. 제거는 운영자가 별도 release 정책으로 수행한다.

## 6. AI API → General API 시작

```bash
cd /home/ubuntu/MVP_v4
sudo install -m 644 deploy/systemd/csr-v4-ai.service /etc/systemd/system/csr-v4-ai.service
sudo install -m 644 deploy/systemd/csr-v4-general.service /etc/systemd/system/csr-v4-general.service
sudo systemctl daemon-reload
sudo systemctl enable --now csr-v4-ai.service
sudo systemctl enable --now csr-v4-general.service
curl --fail http://127.0.0.1:8101/health
curl --fail http://127.0.0.1:8100/api/v4/health
```

entrypoint: `backend.scripts.start ai|general` → V4 내부 ASGI app. sys.path/PYTHONPATH 추가 불필요.
production에서 포트/host 계약이 다르면 실행을 거부한다. 두 API는 외부에 공개하지 않는다.

## 7. Nginx

`deploy/nginx/csr-v4.conf`는 전용 서버의 port 80 default site 예시다.
기존 default site가 있으면 운영자가 충돌을 정리한 뒤 이 파일을 활성화한다. 스크립트가 기존 사이트를 자동 삭제하지 않는다.

```bash
cd /home/ubuntu/MVP_v4
sudo install -m 644 deploy/nginx/csr-v4.conf /etc/nginx/conf.d/csr-v4.conf
sudo nginx -t
sudo systemctl reload nginx
curl --fail http://127.0.0.1/api/v4/health
curl --fail http://127.0.0.1/
```

요청 흐름: Browser → Nginx `/api/*` → General 8100 → AI 8101.
proxy_pass에는 trailing slash가 없어 `/api/v4` prefix가 유지된다. SPA route는 index.html로 fallback한다.
HTTPS를 운영할 경우 인증서/도메인 설정은 운영자가 주입하며 앱 코드는 동일하다.

## 8. 검증과 완료 판정

```bash
cd /home/ubuntu/MVP_v4
.venv/bin/python -m scripts.verify_self_contained
.venv/bin/python -m scripts.verify_env_example
.venv/bin/python -m scripts.verify_frontend_uuid_usage
.venv/bin/python -m pytest tests -q
bash deploy/scripts/check-health.sh
```

ML 검증: `curl --fail http://127.0.0.1:8101/ready/ml` 또는 `.venv/bin/python -m backend.scripts.model_preflight --record`.
현재 마지막 제품 readiness 검사는 **503으로 실패해야 정상인 미완성 제품**이다. Conversational/Intake 구현 후 200이 되어야 제품 gate를 통과한다.
UUID unit tests는 localhost/secure provider와 randomUUID 없는 HTTP-IP fallback 및 API request ID를 검증한다.
실제 HTTPS/HTTP-IP 브라우저, draft/focus/cursor/selection/IME, Scenario A/B는 Phase 7에 검증한다.

최종 완료 전 별도 위치에 V4만 복사하여 clean Python 3.11 venv/requirements, clean npm ci,
새 MySQL migration, production build, 두 API readiness, Scenario A/B를 실행한다.
정적 audit은 탐지 가능한 source/config 패턴 검사이며 동적 경로 사용과 설치 환경의 독립성을 대신 증명하지 않는다.

## 로컬 Phase 0 재현 (Windows)

V4 root에서 `.venv\Scripts\python.exe -m backend.scripts.phase0_smoke --general-port 18100 --ai-port 18101`.
mysqld는 PATH에 있어야 한다. 기존 DB 설정을 읽지 않고 `--no-defaults`로 V4 `.cache`에 새 DB를 만든다.
loopback 테스트 DB만 생성하며 real secret 없이 실행하고 시작한 프로세스만 종료한다.
기존 8100/8101 프로세스는 건드리지 않는다. Windows용 smoke를 Ubuntu에서 root mysqld 절차로 사용하지 않는다.

## P0-006 복사본 ML 재현

V4 root에서 실행한다. 다운로드는 설치용 패키지이며 모델/추론에는 외부 호출이 없다.

```text
python -m pip download --dest .cache/model-wheelhouse --only-binary=:all: -r backend/requirements.txt
python -m scripts.verify_model_isolation
```

실제 env/venv/cache를 제외한 V4 파일을 `.cache/model-isolation-*/MVP_v4`로 복사하고,
wheel을 복사본 안에 준비한 뒤 새 venv에 `--no-index`로 설치한다.
추론 시 Python 환경 경로 주입을 무시하고 user site를 비활성화하며 audit hook으로 복사본 밖 원본 repo 읽기와 네트워크 접근을 거부한다.
모델과 sklearn/pandas/joblib의 실제 module 위치가 복사본 내부인지 검증한다.
이 검사는 ML 부분 독립 실행 증명이다. 최종 standalone 전체 migration/frontend/E2E gate를 대신하지 않는다.
