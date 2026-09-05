import json

from scripts.verify_self_contained import ROOT


def test_nginx_retains_api_prefix_and_spa_fallback():
    config = (ROOT / "deploy/nginx/csr-v4.conf").read_text()
    assert "location /api/" in config
    assert "proxy_pass http://127.0.0.1:8100;" in config
    assert "proxy_pass http://127.0.0.1:8100/;" not in config
    assert "try_files $uri $uri/ /index.html;" in config
    assert "8101" not in config


def test_systemd_uses_v4_venv_and_entrypoints():
    for service in ("ai", "general"):
        unit = (ROOT / f"deploy/systemd/csr-v4-{service}.service").read_text()
        assert "WorkingDirectory=/home/ubuntu/MVP_v4" in unit
        assert f"ExecStart=/home/ubuntu/MVP_v4/.venv/bin/python -m backend.scripts.start {service}" in unit


def test_frontend_build_inputs_and_no_env_autoload():
    manifest = json.loads((ROOT / "frontend/package.json").read_text())
    lock = json.loads((ROOT / "frontend/package-lock.json").read_text())
    assert manifest["dependencies"] == lock["packages"][""]["dependencies"]
    assert manifest["devDependencies"] == lock["packages"][""]["devDependencies"]
    assert "envDir: false" in (ROOT / "frontend/vite.config.ts").read_text()


def test_real_environment_files_are_ignored():
    rules = (ROOT / ".gitignore").read_text().splitlines()
    assert all(rule in rules for rule in (".env", ".env.*", "!.env.example", ".venv/", "node_modules/"))
