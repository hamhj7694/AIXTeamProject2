"""Reviewed, data-preserving repair for the September 2026 schema drift.

Default: inspect/plan only (an isolated reference database is created and removed).
--apply: native SQL backup, restore rehearsal, schema/data verification, then repair.
Never infers migration completion from column names alone or deletes business rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from scripts.apply_migrations import execute_all
from scripts.migration_manifest import ordered_migrations, migration_path
from scripts.schema_tools import MVP_ROOT, connect, identifier, schema_snapshot, differences, row_fingerprints, integrity_checks

RECONCILABLE = frozenset({
    '004_case_messages_and_event_actor.sql', '005_verification_actions.sql',
    '006_case_version.sql', '007_voice_sessions.sql', '008_collaboration_channels.sql',
    '009_case_attachments.sql', '009_mysql_parity_workflow.sql',
    '010_case_fact_question_link.sql', '011_message_idempotency.sql',
})
REPAIR_FILES = (
    '021_create_case_transactions.sql',
    '024_bank_staff_role_schema_alignment.sql',
    '025_retire_transcript_storage.sql',
    '029_normalize_case_transaction_amounts.sql',
)
HISTORICAL_RECORDS = {'021_bank_staff_assignment_fields.sql'}
ALLOWED_DRIFT = {
    'tables.case_transactions',
    'tables.transcript_segments',
    'tables.bank_staff_directory.columns.assignment_role.COLUMN_TYPE',
    'tables.bank_staff_directory.checks.chk_bank_staff_assignment_role.clause',
    'tables.case_transactions.columns.amount.COLUMN_TYPE',
    'tables.case_transactions.checks.chk_case_transactions_type',
    'tables.case_transactions.checks.chk_case_transactions_amount',
}


@contextmanager
def isolated_database(kind: str):
    name = f'csr_schema_{kind}_{uuid4().hex[:16]}'
    with connect() as connection:
        with connection.cursor() as cursor:
            # CREATE without IF NOT EXISTS ensures we own the database we remove.
            cursor.execute(f'CREATE DATABASE {identifier(name)} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    try:
        yield name
    finally:
        if not name.startswith(f'csr_schema_{kind}_'):
            raise RuntimeError('Unsafe scratch database cleanup')
        with connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'DROP DATABASE {identifier(name)}')


def applied_names(connection) -> set[str]:
    with connection.cursor() as cursor:
        cursor.execute('SELECT migration_name FROM schema_migrations')
        return {r['migration_name'] for r in cursor.fetchall()}


def migration_hashes() -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ordered_migrations()}


def validate_plan(expected: dict, actual: dict, applied: set[str]) -> list[dict]:
    pending = set(migration_hashes()) - applied
    unknown = applied - set(migration_hashes()) - HISTORICAL_RECORDS
    if unknown or pending - RECONCILABLE - set(REPAIR_FILES):
        raise RuntimeError('Unreviewed migration history; manual investigation required')
    delta = differences(expected, actual)
    if any(d['path'] not in ALLOWED_DRIFT for d in delta):
        raise RuntimeError('Unreviewed schema drift: '+json.dumps(delta, ensure_ascii=False, default=str))
    for item in delta:
        if item['path'].endswith('COLUMN_TYPE'):
            if item['path'] == 'tables.case_transactions.columns.amount.COLUMN_TYPE':
                if item.get('actual') != 'decimal(19,2)':
                    raise RuntimeError('Only the reviewed DECIMAL(19,2) -> BIGINT transaction normalization is allowed')
            elif item.get('actual') != 'varchar(24)':
                raise RuntimeError('Only the reviewed varchar(24) -> varchar(32) widening is allowed')
        if item['path'] == 'tables.case_transactions' and item['kind'] != 'missing':
            raise RuntimeError('Existing transaction-table drift requires separate review')
    return delta


def repair(connection, expected: dict) -> list[str]:
    repaired = []
    applied = applied_names(connection)
    validate_plan(expected, schema_snapshot(connection), applied)
    with connection.cursor() as cursor:
        for name in REPAIR_FILES:
            if name not in applied:
                execute_all(cursor, migration_path(name).read_text(encoding='utf-8'))
                cursor.execute('INSERT INTO schema_migrations (migration_name) VALUES (%s)', (name,))
                connection.commit()
                repaired.append(name)
        delta = differences(expected, schema_snapshot(connection))
        if delta:
            raise RuntimeError('Schema did not converge; history reconciliation stopped')
        # 008 has a data effect too; do not claim it applied just because DDL matches.
        cursor.execute("SELECT COUNT(*) n FROM messages WHERE mentions_json IS NULL OR mentions_json=''")
        if cursor.fetchone()['n']:
            raise RuntimeError('008 mentions backfill is incomplete; no historical markers added')
        checks = integrity_checks(connection, expected)
        if checks['foreign_key_violations'] or checks['case_orphans']:
            raise RuntimeError('Integrity checks failed; history reconciliation stopped')
        for name in sorted(RECONCILABLE - applied):
            cursor.execute('INSERT INTO schema_migrations (migration_name) VALUES (%s)', (name,))
            repaired.append(f'VERIFIED_BASELINE:{name}')
        connection.commit()
    return repaired


def mysql_program(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise RuntimeError(f'{name} is required for backup and restore rehearsal')
    return executable


def native_options() -> tuple[list[str], dict[str, str]]:
    # Do not place credentials in process arguments or print subprocess env.
    env = {**os.environ, 'MYSQL_PWD': os.getenv('MYSQL_PASSWORD', '')}
    options = ['--host='+os.getenv('MYSQL_HOST', '127.0.0.1'),
               '--port='+os.getenv('MYSQL_PORT', '3306'), '--user='+os.getenv('MYSQL_USER', 'root'),
               '--default-character-set=utf8mb4']
    return options, env


def run_reference(database: str):
    subprocess.run([sys.executable, str(Path(__file__).with_name('apply_migrations.py'))],
                   env={**os.environ, 'MYSQL_DATABASE': database}, check=True,
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def append_trigger_backup(connection, dump: Path, schema: dict) -> None:
    """Avoid mysqldump's version-comment/terminal-semicolon trigger restore error.

    Dump rows first, then recreate triggers from server-owned SHOW CREATE text.
    Only the outer statement terminator is removed; SQL body/literals are retained.
    """
    with connection.cursor() as cursor, dump.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write('\n-- Triggers appended after all data; restore-tested by normalize_database.py\n')
        stream.write('SET @csr_backup_sql_mode=@@sql_mode;\n')
        for name in sorted(schema['triggers']):
            cursor.execute(f'SHOW CREATE TRIGGER {identifier(name)}')
            row = cursor.fetchone()
            statement = row['SQL Original Statement'].strip().rstrip(';')
            if '$$CSR$$' in statement:
                raise RuntimeError('Trigger delimiter collision')
            stream.write(f"SET sql_mode={connection.escape(row['sql_mode'])};\n")
            stream.write(f"SET NAMES {identifier(row['character_set_client'])} COLLATE {identifier(row['collation_connection'])};\n")
            stream.write('DELIMITER $$CSR$$\n'+statement+'$$CSR$$\nDELIMITER ;\n')
        stream.write('SET sql_mode=@csr_backup_sql_mode;\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--database')
    args = parser.parse_args()
    load_dotenv(MVP_ROOT / '.env')
    database = args.database or os.getenv('MYSQL_DATABASE', 'csr')
    identifier(database)
    with isolated_database('reference') as reference:
        run_reference(reference)
        with connect(reference) as conn:
            expected = schema_snapshot(conn)
        with connect(database) as connection:
            lock = f'{database}:schema-migrations'
            with connection.cursor() as cursor:
                cursor.execute('SELECT GET_LOCK(%s, 5) acquired', (lock,))
                if cursor.fetchone()['acquired'] != 1:
                    raise RuntimeError('Another migration is running')
            try:
                actual = schema_snapshot(connection)
                names = applied_names(connection)
                delta = validate_plan(expected, actual, names)
                plan = {'database': database, 'drift_paths': [d['path'] for d in delta],
                        'pending': sorted(set(migration_hashes())-names),
                        'historical_records_retained': sorted(names-set(migration_hashes()))}
                print(json.dumps(plan, ensure_ascii=False))
                if not args.apply:
                    return
                if not delta and not plan['pending']:
                    print('Already aligned; no changes made.')
                    return
                run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8]
                directory = MVP_ROOT / 'backend/data/backups' / run_id
                directory.mkdir(parents=True, exist_ok=False)
                dump = directory / f'{database}.sql'
                opts, env = native_options()
                subprocess.run([mysql_program('mysqldump'), *opts, '--single-transaction', '--hex-blob',
                                '--routines', '--events', '--skip-triggers', '--no-tablespaces',
                                '--set-gtid-purged=OFF', '--result-file='+str(dump), database],
                               env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                append_trigger_backup(connection, dump, actual)
                before = row_fingerprints(connection, list(actual['tables']))
                with isolated_database('restore') as restored:
                    with dump.open('rb') as stream:
                        restored_process = subprocess.run([mysql_program('mysql'), *opts, restored], stdin=stream,
                                       env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        if restored_process.returncode:
                            error = restored_process.stderr.decode('utf-8', errors='replace')
                            raise RuntimeError('Backup restore failed before live changes: '+error[:500])
                    with connect(restored) as rehearsal:
                        if differences(actual, schema_snapshot(rehearsal)):
                            raise RuntimeError('Backup restored schema differs from live schema')
                        if row_fingerprints(rehearsal, list(actual['tables'])) != before:
                            raise RuntimeError('Concurrent writes or backup mismatch; stop before live changes')
                        trial_changes = repair(rehearsal, expected)
                        trial_after = row_fingerprints(rehearsal, list(actual['tables']))
                        if any(trial_after[t] != before[t] for t in before if t != 'schema_migrations'):
                            raise RuntimeError('Repair rehearsal changed business data')
                if row_fingerprints(connection, list(actual['tables'])) != before:
                    raise RuntimeError('Live data changed during rehearsal; retry in a maintenance window')
                journal = {**plan, 'backup': str(dump), 'restore_verified': True,
                           'status': 'LIVE_APPLY_STARTING', 'before': before,
                           'migration_sha256': migration_hashes()}
                journal_path = directory / 'attempt.json'
                journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
                try:
                    changed = repair(connection, expected)
                except Exception as error:
                    journal.update(status='LIVE_APPLY_FAILED_CHECK_CURRENT_SCHEMA', error_type=type(error).__name__)
                    journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
                    raise
                after = row_fingerprints(connection, list(actual['tables']))
                preserved = all(after[t] == before[t] for t in before if t != 'schema_migrations')
                receipt = {**plan, 'applied_at_utc': datetime.now(timezone.utc).isoformat(),
                           'backup': str(dump), 'backup_sha256': hashlib.sha256(dump.read_bytes()).hexdigest(),
                           'restore_verified': True, 'rehearsal_changes': trial_changes,
                           'changes': changed, 'business_rows_unchanged': preserved,
                           'before': before, 'after': after, 'migration_sha256': migration_hashes()}
                (directory / 'receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
                journal.update(status='COMPLETE' if preserved else 'DATA_CHANGED_REVIEW_RECEIPT')
                journal_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
                print(json.dumps({k:receipt[k] for k in ('backup','restore_verified','changes','business_rows_unchanged')},ensure_ascii=False))
                if not preserved:
                    raise RuntimeError('Business rows changed (possibly concurrent writes); inspect receipt, do not auto-restore')
            finally:
                connection.rollback()
                with connection.cursor() as cursor:
                    cursor.execute('SELECT RELEASE_LOCK(%s)', (lock,))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
