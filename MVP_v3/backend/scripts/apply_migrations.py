from __future__ import annotations

import os
import re
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from pymysql.constants import CLIENT


BACKEND_DIR = Path(__file__).resolve().parents[1]
MVP_ROOT = BACKEND_DIR.parent
MIGRATIONS_DIR = BACKEND_DIR / "migrations"


def connection_options() -> dict[str, object]:
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "charset": "utf8mb4",
        "client_flag": CLIENT.MULTI_STATEMENTS,
        "autocommit": False,
    }


def execute_all(cursor: pymysql.cursors.Cursor, sql: str) -> None:
    cursor.execute(sql)
    while cursor.nextset():
        pass


def main() -> None:
    load_dotenv(MVP_ROOT / ".env")
    database = os.getenv("MYSQL_DATABASE", "csr")
    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
        raise ValueError("MYSQL_DATABASE에는 영문, 숫자, 밑줄만 사용할 수 있습니다.")

    options = connection_options()
    try:
        bootstrap = pymysql.connect(**options)
    except pymysql.err.OperationalError as error:
        if error.args and error.args[0] == 1045:
            raise SystemExit(
                "MySQL 인증에 실패했습니다. MVP_v3/.env의 MYSQL_USER와 "
                "MYSQL_PASSWORD를 확인해 주세요."
            ) from None
        raise
    try:
        with bootstrap.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        bootstrap.commit()
    finally:
        bootstrap.close()

    connection = pymysql.connect(database=database, **options)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_name VARCHAR(255) PRIMARY KEY,
                    applied_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
                )"""
            )
            connection.commit()

            for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
                cursor.execute(
                    "SELECT 1 FROM schema_migrations WHERE migration_name=%s",
                    (migration.name,),
                )
                if cursor.fetchone():
                    print(f"SKIP {migration.name}")
                    continue

                try:
                    execute_all(cursor, migration.read_text(encoding="utf-8"))
                    cursor.execute(
                        "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
                        (migration.name,),
                    )
                    connection.commit()
                    print(f"APPLIED {migration.name}")
                except Exception:
                    connection.rollback()
                    raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
