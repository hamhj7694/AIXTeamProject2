# Diagnosis model artifact

`WINDOW_LOGISTIC_DASHBOARD_EXPERIMENTAL_SAMPLE_v1.pkl`은 사용자가 지정한 GitHub 저장소의 실험용 Window Logistic bundle이다.

- source: `hamhj7694/AI-X-1-/main/a_함형준/MLmodel_v2/WINDOW_LOGISTIC_DASHBOARD_EXPERIMENTAL_SAMPLE_v1.pkl`
- SHA-256: `662db2a9351dc4ca2c453776ae6f45750e465234cc9abcecc65b58a6b047c5fc`
- model status: `EXPERIMENTAL_SAMPLE`
- trained with scikit-learn `1.6.1`
- 현재 실행 요구 버전: scikit-learn `1.6.1` 고정. `backend/requirements.txt`와 일치하며 Adapter는 다른 버전에서 모델 로드를 거부한다. `MVP_v3/.venv`에 해당 의존성을 설치한 Python으로 실행한다.

Pickle/joblib은 임의 파일을 로드하지 않는다. Adapter는 로드 전에 위 해시를 검증한다.
