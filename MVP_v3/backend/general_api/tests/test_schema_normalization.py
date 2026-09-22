from __future__ import annotations

import os
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import pymysql

from scripts.build_schema_bootstrap import OUTPUT, bootstrap_sql
from scripts.normalize_database import (
    HISTORICAL_RECORDS, RECONCILABLE, isolated_database, migration_hashes, repair,
    run_reference, validate_plan,
)
from scripts.schema_tools import connect, differences, identifier, normalized_sql, row_fingerprints, schema_snapshot
from scripts.apply_migrations import execute_all
from scripts.export_database_catalog import ENTITIES
from scripts.migration_manifest import MIGRATIONS_DIR, ordered_migrations, migration_path


class SchemaToolUnitTest(unittest.TestCase):
    def test_manifest_preserves_history_order_and_excludes_rollback(self):
        paths = ordered_migrations()
        self.assertEqual(len(paths), 30)
        self.assertEqual([p.name for p in paths], sorted(p.name for p in paths))
        self.assertEqual(len({p.name for p in paths}), len(paths))
        self.assertFalse(list(MIGRATIONS_DIR.glob('*.sql')))
        for path in paths:
            self.assertNotIn('rollback', path.relative_to(MIGRATIONS_DIR).parts)
            self.assertEqual(migration_path(path.name), path)
        for rollback in (MIGRATIONS_DIR / 'rollback').rglob('*.sql'):
            forward = migration_path(rollback.name)
            self.assertEqual(rollback.parent.name, forward.parent.name)

    def test_manifest_rejects_missing_unlisted_duplicate_unsafe_and_reordered_sql(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'cases').mkdir()
            (root / 'staff').mkdir()
            (root / 'rollback').mkdir()
            (root / 'cases/001_first.sql').write_text('SELECT 1;', encoding='utf-8')
            (root / 'staff/002_second.sql').write_text('SELECT 2;', encoding='utf-8')
            valid = ['cases/001_first.sql', 'staff/002_second.sql']
            (root / 'manifest.json').write_text(json.dumps(valid), encoding='utf-8')
            self.assertEqual(len(ordered_migrations(root)), 2)
            invalid_lists = [[], {}, valid[:1], valid[::-1], valid + valid[:1],
                             valid + ['cases/003_missing.sql'],
                             ['../001_outside.sql'], ['rollback/001_first.sql'],
                             ['C:/001_first.sql'], [None]]
            for entries in invalid_lists:
                with self.subTest(entries=entries):
                    (root / 'manifest.json').write_text(json.dumps(entries), encoding='utf-8')
                    with self.assertRaises(ValueError):
                        ordered_migrations(root)
            (root / 'staff/001_first.sql').write_text('SELECT 1;', encoding='utf-8')
            (root / 'manifest.json').write_text(json.dumps(valid + ['staff/001_first.sql']), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Duplicate migration identity'):
                ordered_migrations(root)

    def test_bootstrap_is_current(self):
        self.assertEqual(OUTPUT.read_text(encoding='utf-8'), bootstrap_sql())

    def test_identifier_rejects_unsafe_names(self):
        for name in ('csr;DROP DATABASE csr', '../csr', '', 'a`b'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                identifier(name)

    def test_sql_normalization_preserves_literal_case_and_spaces(self):
        self.assertEqual(normalized_sql(" UPDATE `t` SET x='A B'; "), "updatetsetx='A B'")
        self.assertNotEqual(normalized_sql("x='A B'"), normalized_sql("x='ab'"))

    def test_detects_type_default_index_and_constraint_changes(self):
        a = {'tables': {'cases': {'column': {'type':'bigint','default':'1'}, 'index':['id'], 'check':'x>0'}}}
        b = deepcopy(a)
        b['tables']['cases']['column']['type'] = 'int'
        b['tables']['cases']['column']['default'] = '0'
        b['tables']['cases']['index'] = ['name']
        b['tables']['cases']['check'] = 'x>=0'
        self.assertEqual(len(differences(a,b)), 4)

    def test_unreviewed_drift_or_history_is_rejected(self):
        names = set(migration_hashes())
        with self.assertRaisesRegex(RuntimeError, 'Unreviewed schema'):
            validate_plan({'tables':{}}, {'tables':{'unexpected':{}}}, names)
        with self.assertRaisesRegex(RuntimeError, 'Unreviewed migration'):
            validate_plan({}, {}, names | {'999_unknown.sql'})
        self.assertEqual(validate_plan({}, {}, names | HISTORICAL_RECORDS), [])

    def test_entity_catalog_is_unique_and_covers_all_migration_tables(self):
        import re
        names = [name for entity in ENTITIES.values() for name in entity]
        self.assertEqual(len(names), len(set(names)))
        created = set(re.findall(r'CREATE TABLE(?: IF NOT EXISTS)?\s+(\w+)', bootstrap_sql(), re.I)) - {'transcript_segments'}
        self.assertEqual(set(names), created)


@unittest.skipUnless(os.getenv('MYSQL_HOST') and os.getenv('MYSQL_USER'), 'Isolated MySQL test credentials required')
class SchemaNormalizationIntegrationTest(unittest.TestCase):
    def test_bootstrap_and_migrations_create_identical_schema_and_markers(self):
        with isolated_database('test_migrations') as reference, isolated_database('test_bootstrap') as bootstrap:
            run_reference(reference)
            run_reference(reference)  # apply twice: no changes/errors
            with connect(reference) as expected_connection, connect(bootstrap) as boot:
                with boot.cursor() as cursor:
                    execute_all(cursor, bootstrap_sql())
                boot.commit()
                self.assertEqual(differences(schema_snapshot(expected_connection), schema_snapshot(boot)), [])
                for connection in (expected_connection, boot):
                    with connection.cursor() as cursor:
                        cursor.execute('SELECT migration_name FROM schema_migrations')
                        self.assertEqual({r['migration_name'] for r in cursor.fetchall()}, set(migration_hashes()))
                boot.rollback()
                with boot.cursor() as cursor, self.assertRaises(pymysql.err.OperationalError):
                    execute_all(cursor, bootstrap_sql())  # refuses existing DB before writes
            run_reference(bootstrap)  # Docker bootstrap followed by runner is safe

    def test_legacy_normalization_preserves_data_and_is_idempotent(self):
        with isolated_database('test_legacy') as database:
            run_reference(database)
            with connect(database) as connection:
                expected = schema_snapshot(connection)
                with connection.cursor() as cursor:
                    # Scoped test DB only: recreate the reviewed historical drift.
                    cursor.execute('DROP TABLE case_transactions')
                    cursor.execute("ALTER TABLE bank_staff_directory MODIFY assignment_role VARCHAR(24) NOT NULL DEFAULT 'CONSULTATION', DROP CHECK chk_bank_staff_assignment_role, ADD CONSTRAINT chk_bank_staff_assignment_role CHECK (assignment_role IN ('SUPERVISOR','MONITORING','CONSULTATION'))")
                    names = sorted(RECONCILABLE | {'021_create_case_transactions.sql','024_bank_staff_role_schema_alignment.sql'})
                    cursor.execute('DELETE FROM schema_migrations WHERE migration_name IN ('+','.join(['%s']*len(names))+')', names)
                    cursor.execute("INSERT INTO schema_migrations (migration_name) VALUES ('021_bank_staff_assignment_fields.sql')")
                    cursor.execute("UPDATE bank_staff_directory SET display_name='직원 편집 보존 테스트' WHERE staff_id='staff-demo-kim-cheolsu'")
                connection.commit()
                before = row_fingerprints(connection, ['bank_staff_directory'])
                changes = repair(connection, expected)
                self.assertEqual(len(changes), 11)
                self.assertEqual(row_fingerprints(connection, ['bank_staff_directory']), before)
                self.assertEqual(differences(expected, schema_snapshot(connection)), [])
                self.assertEqual(repair(connection, expected), [])
                with connection.cursor() as cursor:
                    for role in ('OTHER_VIEWER','HANDOVER_PENDING'):
                        cursor.execute('UPDATE bank_staff_directory SET assignment_role=%s WHERE staff_id=%s', (role,'staff-demo-kim-cheolsu'))
                    with self.assertRaises(pymysql.err.OperationalError):
                        cursor.execute("UPDATE bank_staff_directory SET assignment_role='INVALID'")
                connection.rollback()


if __name__ == '__main__':
    unittest.main()
