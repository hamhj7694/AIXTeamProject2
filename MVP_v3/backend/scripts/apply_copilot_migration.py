"""Plan, backup/restore-rehearse and apply ONLY the additive Copilot migration.

Stop application writers before --apply. Never restores over the service database.
All business row hashes use the original columns so added nullable metadata is safe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from scripts.normalize_database import (isolated_database, run_reference, native_options,
    mysql_program, append_trigger_backup, applied_names, migration_hashes)
from scripts.schema_tools import MVP_ROOT, connect, identifier, schema_snapshot, differences, integrity_checks

MIGRATION = '031_case_copilot_workflow.sql'
ALLOWED = {
    'tables.messages.columns.ai_metadata_json',
    'tables.case_tasks.checks.chk_case_task_source.clause',
    'tables.case_copilot_jobs',
}
# Existing local extension tables were inspected separately. Never adopt, alter,
# or remove their schema/history as part of this additive migration.
PRESERVED_EXTENSIONS = {'case_context_proposal_scans', 'case_context_update_proposals'}


def original_rows(connection, schema):
    result = {}
    connection.rollback()
    with connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION READ ONLY')
        cursor.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT')
        try:
            for table, meta in sorted(schema['tables'].items()):
                if table == 'schema_migrations':
                    continue
                columns = ','.join(identifier(c) for c in meta['columns'])
                cursor.execute(f'SELECT {columns} FROM {identifier(table)}')
                hashes = sorted(hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False,
                    default=str).encode()).hexdigest() for row in cursor.fetchall())
                result[table] = {'count': len(hashes), 'sha256': hashlib.sha256(''.join(hashes).encode()).hexdigest()}
        finally:
            connection.rollback()
    return result


def apply_only(database):
    subprocess.run([sys.executable, str(Path(__file__).with_name('apply_migrations.py')), '--only', MIGRATION],
        env={**os.environ, 'MYSQL_DATABASE': database}, check=True, capture_output=True)


def verify(connection, expected, original, rows):
    connection.rollback()
    if differences(expected, schema_snapshot(connection)):
        raise RuntimeError('Schema mismatch after rehearsal/application')
    if original_rows(connection, original) != rows:
        raise RuntimeError('Original business data changed; no automatic restore will be attempted')
    checks = integrity_checks(connection, expected)
    if checks['foreign_key_violations'] or checks['case_orphans']:
        raise RuntimeError('Integrity check failed')
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    load_dotenv(MVP_ROOT / '.env')
    database = os.getenv('MYSQL_DATABASE', 'csr')
    identifier(database)
    with connect(database) as connection:
        names = applied_names(connection)
        pending = set(migration_hashes()) - names
        if not pending:
            print(json.dumps({'database': database, 'pending': [], 'applied': False}))
            return
        if pending != {MIGRATION}:
            raise RuntimeError('Only migration 031 may be pending; inspect all other migrations first')
        original = schema_snapshot(connection)
        connection.rollback()
        with isolated_database('copilot_reference') as reference:
            run_reference(reference)
            with connect(reference) as ref:
                expected = schema_snapshot(ref)
            for table in PRESERVED_EXTENSIONS:
                if table in original['tables'] and table not in expected['tables']:
                    expected['tables'][table] = original['tables'][table]
            delta = differences(expected, original)
            if {d['path'] for d in delta} != ALLOWED:
                raise RuntimeError('Unreviewed schema differences: ' + ', '.join(d['path'] for d in delta))
            print(json.dumps({'database': database, 'pending': sorted(pending),
                              'reviewed_drift': sorted(ALLOWED), 'apply': args.apply}))
            if not args.apply:
                return
            rows = original_rows(connection, original)
            run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_copilot_' + uuid4().hex[:8]
            directory = MVP_ROOT / 'backend/data/backups' / run_id
            directory.mkdir(parents=True, exist_ok=False)
            dump = directory / f'{database}.sql'
            opts, environment = native_options()
            subprocess.run([mysql_program('mysqldump'), *opts, '--single-transaction', '--hex-blob',
                '--routines', '--events', '--skip-triggers', '--no-tablespaces', '--set-gtid-purged=OFF',
                '--result-file=' + str(dump), database], env=environment, check=True, capture_output=True)
            append_trigger_backup(connection, dump, original)
            connection.rollback()
            with isolated_database('copilot_restore') as restored:
                with dump.open('rb') as stream:
                    subprocess.run([mysql_program('mysql'), *opts, restored], stdin=stream,
                        env=environment, check=True, capture_output=True)
                with connect(restored) as rehearsal:
                    if differences(original, schema_snapshot(rehearsal)) or original_rows(rehearsal, original) != rows:
                        raise RuntimeError('Backup restore does not match source; live DB untouched')
                    apply_only(restored)
                    verify(rehearsal, expected, original, rows)
            if original_rows(connection, original) != rows or applied_names(connection) != names:
                raise RuntimeError('Live DB changed during rehearsal; stop writers and retry')
            connection.rollback()
            receipt = {'migration': MIGRATION, 'database': database, 'backup': str(dump),
                'backup_sha256': hashlib.sha256(dump.read_bytes()).hexdigest(),
                'restore_verified': True, 'rehearsal_verified': True, 'before': rows,
                'migration_sha256': migration_hashes()[MIGRATION], 'status': 'APPLY_STARTING'}
            receipt_path = directory / 'receipt.json'
            receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
            try:
                apply_only(database)
                checks = verify(connection, expected, original, rows)
                receipt.update(status='COMPLETE', original_rows_preserved=True, integrity=checks)
            except Exception as error:
                receipt.update(status='FAILED_INSPECT_BEFORE_RETRY', error_type=type(error).__name__)
                raise
            finally:
                receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({k: receipt[k] for k in ('status', 'backup', 'restore_verified', 'rehearsal_verified', 'original_rows_preserved', 'integrity')}))


if __name__ == '__main__':
    main()
