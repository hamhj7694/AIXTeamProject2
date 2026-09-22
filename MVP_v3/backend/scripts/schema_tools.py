"""Read-only schema inventory shared by diagnostics and migration tests.

No application payloads, names, account values or credentials are exported.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pymysql

from scripts.apply_migrations import connection_options

BACKEND = Path(__file__).resolve().parents[1]
MVP_ROOT = BACKEND.parent


def identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise ValueError("Unsafe database/table identifier")
    return f"`{value}`"


def connect(database: str | None = None):
    return pymysql.connect(**connection_options(), database=database,
                           cursorclass=pymysql.cursors.DictCursor)


def normalized_sql(value: str) -> str:
    # Preserve quoted literals while ignoring formatting outside them.
    parts = re.split(r"('(?:''|\\.|[^'])*')", value)
    return ''.join(part if index % 2 else re.sub(r'\s+|`', '', part).lower()
                   for index, part in enumerate(parts)).rstrip(';')


def schema_snapshot(connection) -> dict:
    with connection.cursor() as cursor:
        def rows(sql):
            cursor.execute(sql)
            return cursor.fetchall()
        tables = {
            row['TABLE_NAME']: {'engine': row['ENGINE'], 'collation': row['TABLE_COLLATION'],
                                'columns': {}, 'indexes': {}, 'foreign_keys': {}, 'checks': {}}
            for row in rows('SELECT TABLE_NAME,ENGINE,TABLE_COLLATION FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_TYPE="BASE TABLE"')
        }
        for row in rows('SELECT TABLE_NAME,COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_DEFAULT,EXTRA,CHARACTER_SET_NAME,COLLATION_NAME,GENERATION_EXPRESSION FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME,ORDINAL_POSITION'):
            table, name = row.pop('TABLE_NAME'), row.pop('COLUMN_NAME')
            tables[table]['columns'][name] = row
        for row in rows('SELECT TABLE_NAME,INDEX_NAME,NON_UNIQUE,COLUMN_NAME,SUB_PART,INDEX_TYPE,COLLATION,IS_VISIBLE FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() ORDER BY TABLE_NAME,INDEX_NAME,SEQ_IN_INDEX'):
            table, name = row.pop('TABLE_NAME'), row.pop('INDEX_NAME')
            tables[table]['indexes'].setdefault(name, []).append(row)
        for row in rows('''SELECT k.TABLE_NAME,k.CONSTRAINT_NAME,k.COLUMN_NAME,k.REFERENCED_TABLE_NAME,k.REFERENCED_COLUMN_NAME,r.UPDATE_RULE,r.DELETE_RULE
            FROM information_schema.KEY_COLUMN_USAGE k JOIN information_schema.REFERENTIAL_CONSTRAINTS r
            ON r.CONSTRAINT_SCHEMA=k.CONSTRAINT_SCHEMA AND r.CONSTRAINT_NAME=k.CONSTRAINT_NAME AND r.TABLE_NAME=k.TABLE_NAME
            WHERE k.TABLE_SCHEMA=DATABASE() AND k.REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY k.TABLE_NAME,k.CONSTRAINT_NAME,k.ORDINAL_POSITION'''):
            table, name = row.pop('TABLE_NAME'), row.pop('CONSTRAINT_NAME')
            tables[table]['foreign_keys'].setdefault(name, []).append(row)
        for row in rows('''SELECT t.TABLE_NAME,c.CONSTRAINT_NAME,c.CHECK_CLAUSE,t.ENFORCED
            FROM information_schema.CHECK_CONSTRAINTS c JOIN information_schema.TABLE_CONSTRAINTS t
            ON t.CONSTRAINT_SCHEMA=c.CONSTRAINT_SCHEMA AND t.CONSTRAINT_NAME=c.CONSTRAINT_NAME
            WHERE c.CONSTRAINT_SCHEMA=DATABASE()'''):
            tables[row['TABLE_NAME']]['checks'][row['CONSTRAINT_NAME']] = {
                'clause': normalized_sql(row['CHECK_CLAUSE']), 'enforced': row['ENFORCED']}
        triggers = {}
        for row in rows('SELECT TRIGGER_NAME,EVENT_MANIPULATION,EVENT_OBJECT_TABLE,ACTION_TIMING,ACTION_STATEMENT FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=DATABASE()'):
            name = row.pop('TRIGGER_NAME')
            row['ACTION_STATEMENT'] = normalized_sql(row['ACTION_STATEMENT'])
            triggers[name] = row
        return {'tables': tables, 'triggers': triggers}


def differences(expected: dict, actual: dict, path: str = '') -> list[dict]:
    results = []
    for key in sorted(expected.keys() | actual.keys()):
        location = f'{path}.{key}' if path else key
        if key not in actual:
            results.append({'path': location, 'kind': 'missing', 'expected': expected[key]})
        elif key not in expected:
            results.append({'path': location, 'kind': 'extra', 'actual': actual[key]})
        elif isinstance(expected[key], dict) and isinstance(actual[key], dict):
            results.extend(differences(expected[key], actual[key], location))
        elif expected[key] != actual[key]:
            results.append({'path': location, 'kind': 'different', 'expected': expected[key], 'actual': actual[key]})
    return results


def row_fingerprints(connection, tables: list[str]) -> dict:
    """Compare data preservation without exporting private row contents."""
    result = {}
    connection.rollback()
    with connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION READ ONLY')
        cursor.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT')
        try:
            for table in sorted(tables):
                cursor.execute(f'SELECT * FROM {identifier(table)}')
                hashes = sorted(hashlib.sha256(json.dumps(row, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()
                                for row in cursor.fetchall())
                result[table] = {'count': len(hashes), 'sha256': hashlib.sha256(''.join(hashes).encode()).hexdigest()}
        finally:
            connection.rollback()
    return result


def integrity_checks(connection, schema: dict) -> dict:
    results = {'foreign_keys_checked': 0, 'foreign_key_violations': [], 'case_orphans': []}
    with connection.cursor() as cursor:
        for table, meta in schema['tables'].items():
            for name, cols in meta['foreign_keys'].items():
                parent = cols[0]['REFERENCED_TABLE_NAME']
                join = ' AND '.join(f'c.{identifier(c["COLUMN_NAME"])}=p.{identifier(c["REFERENCED_COLUMN_NAME"])}' for c in cols)
                nonnull = ' AND '.join(f'c.{identifier(c["COLUMN_NAME"])} IS NOT NULL' for c in cols)
                cursor.execute(f'SELECT COUNT(*) n FROM {identifier(table)} c LEFT JOIN {identifier(parent)} p ON {join} WHERE {nonnull} AND p.{identifier(cols[0]["REFERENCED_COLUMN_NAME"])} IS NULL')
                count = cursor.fetchone()['n']
                results['foreign_keys_checked'] += 1
                if count:
                    results['foreign_key_violations'].append({'table': table, 'constraint': name, 'count': count})
            if table != 'cases' and 'case_id' in meta['columns']:
                cursor.execute(f'SELECT COUNT(*) n FROM {identifier(table)} t LEFT JOIN cases c ON c.case_id=t.case_id WHERE c.case_id IS NULL')
                count = cursor.fetchone()['n']
                if count:
                    results['case_orphans'].append({'table': table, 'count': count})
    return results
