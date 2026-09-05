"""Disposable MySQL + two real API processes. Never uses an existing DB or env file."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

import httpx
import pymysql

from backend.config import ROOT, Settings
from backend.contracts.case import ActorContext, ActorRole, CreateCaseRequest, CreateEventRequest, EntityType, EventType, Visibility
from backend.database import CURRENT_SCHEMA_REVISION, database_readiness
from backend.general_api.app.domains.cases.repository import CaseRepository
from backend.scripts.migrate import upgrade


def wait_for(check, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return check()
        except (OSError, pymysql.MySQLError, httpx.HTTPError):
            time.sleep(0.2)
    raise RuntimeError("Disposable service did not become available")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--general-port", type=int, default=8100)
    parser.add_argument("--ai-port", type=int, default=8101)
    args = parser.parse_args()
    general_port, ai_port = args.general_port, args.ai_port
    executable = shutil.which("mysqld")
    if not executable:
        raise SystemExit("mysqld must be available on PATH; no existing database will be used")
    # Refuse to interfere with an existing API process.
    for port in (general_port, ai_port):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        mysql_port = probe.getsockname()[1]
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="phase0-", dir=cache))
    data_dir = run_dir / "mysql"
    data_dir.mkdir()
    processes = []
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    report = {"mysql_migration": "NOT_RUN", "case_projection": "NOT_RUN", "api_health": "NOT_RUN", "ml_inference": "NOT_RUN", "conversational_inference": "NOT_IMPLEMENTED"}
    try:
        with (run_dir / "services.log").open("w", encoding="utf-8") as log:
            subprocess.run([executable, "--no-defaults", "--initialize-insecure", f"--datadir={data_dir}"],
                           stdout=log, stderr=log, check=True, timeout=60, creationflags=flags)
            processes.append(subprocess.Popen([
                executable, "--no-defaults", f"--datadir={data_dir}", "--bind-address=127.0.0.1",
                f"--port={mysql_port}", "--mysqlx=0", "--skip-log-bin",
            ], stdout=log, stderr=log, creationflags=flags))
            connection = wait_for(lambda: pymysql.connect(host="127.0.0.1", port=mysql_port,
                                                          user="root", password="", connect_timeout=1))
            try:
                with connection.cursor() as cursor:
                    cursor.execute("CREATE DATABASE csr_v4_phase0 CHARACTER SET utf8mb4")
            finally:
                connection.close()
            db_url = f"mysql+pymysql://root@127.0.0.1:{mysql_port}/csr_v4_phase0?charset=utf8mb4"
            settings = Settings(app_env="test", database_url=db_url)
            upgrade(settings)
            upgrade(settings)
            assert database_readiness(settings) == "ok"
            report["mysql_migration"] = f"PASS: fresh MySQL migration {CURRENT_SCHEMA_REVISION}, repeated upgrade"
            repository = CaseRepository(settings)
            try:
                staff = ActorContext(actor_id="smoke-staff", role=ActorRole.BANK_STAFF)
                create_id = uuid4()
                created = repository.create_case(staff, CreateCaseRequest(
                    client_request_id=create_id, customer_participant_id="smoke-customer"))
                repository.append_event(create_id, staff, CreateEventRequest(
                    client_request_id=uuid4(), expected_version=created.case.version, event_type=EventType.ENTITY_CREATED,
                    entity_type=EntityType.TASK, visibility=Visibility.BANK_INTERNAL, payload={"task_status": "TODO"}))
                customer = repository.projection(create_id, ActorContext(actor_id="smoke-customer", role=ActorRole.CUSTOMER))
                assert {event.visibility.value for event in customer.events} == {Visibility.CUSTOMER.value}
                report["case_projection"] = "PASS: V4 Case create/event/customer visibility projection on MySQL"
            finally:
                repository.close()
            environment = dict(os.environ)
            environment.update(APP_ENV="test", DATABASE_URL=db_url,
                               AI_API_BASE_URL=f"http://127.0.0.1:{ai_port}", AI_TIMEOUT_SECONDS="2",
                               ATTACHMENT_STORAGE_ROOT="backend/data/uploads", VECTOR_STORE_PATH="backend/data/vector_db")
            for service, port in (("ai_api", ai_port), ("general_api", general_port)):
                processes.append(subprocess.Popen([
                    sys.executable, "-m", "uvicorn", f"backend.{service}.app.main:app",
                    "--host", "127.0.0.1", "--port", str(port), "--no-access-log",
                ], cwd=ROOT, env=environment, stdout=log, stderr=log, creationflags=flags))
            with httpx.Client(trust_env=False, timeout=2) as client:
                def health(port, path):
                    response = client.get(f"http://127.0.0.1:{port}{path}")
                    response.raise_for_status()
                    return response.json()
                assert wait_for(lambda: health(ai_port, "/health"))["service"] == "csr-ai-api"
                ml = health(ai_port, "/ready/ml")
                assert ml["ready"] is True
                assert ml["checks"]["zero_features"]["label"] == "NORMAL"
                assert ml["checks"]["signal_features"]["label"] == "PHISHING"
                report["ml_inference"] = "PASS: actual model inference over HTTP /ready/ml"
                assert wait_for(lambda: health(general_port, "/api/v4/health"))["service"] == "csr-general-api"
                readiness = client.get(f"http://127.0.0.1:{general_port}/api/v4/ready")
                assert readiness.status_code == 503
                assert readiness.json()["checks"] == {"database": "ok", "ai": "AI_NOT_READY"}
            report["api_health"] = f"PASS: AI {ai_port} + General {general_port}, actual HTTP adapter"
            report["readiness"] = "PASS: ML ready; unimplemented conversational/intake retain product 503; DB ready"
    finally:
        for process in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        output = ROOT / "docs/evidence/phase0_backend_smoke.json"
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
