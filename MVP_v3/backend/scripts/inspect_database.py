"""Export live schema metadata and counts, never application row contents."""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from scripts.schema_tools import MVP_ROOT, connect, schema_snapshot, differences, integrity_checks, identifier
from scripts.migration_manifest import ordered_migrations


def inspect(database: str) -> dict:
    with connect(database) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SET TRANSACTION READ ONLY')
            cursor.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT')
            schema = schema_snapshot(connection)
            counts = {}
            for table in sorted(schema['tables']):
                cursor.execute(f'SELECT COUNT(*) n FROM {identifier(table)}')
                counts[table] = cursor.fetchone()['n']
            cursor.execute('SELECT migration_name FROM schema_migrations ORDER BY migration_name')
            applied = [r['migration_name'] for r in cursor.fetchall()]
            integrity = integrity_checks(connection, schema)
            connection.rollback()
        files = [p.name for p in ordered_migrations()]
        return {'database': database, 'inspected_at_utc': datetime.now(timezone.utc).isoformat(),
                'schema': schema, 'counts': counts, 'integrity': integrity, 'applied': applied,
                'pending': sorted(set(files)-set(applied)), 'historical_records': sorted(set(applied)-set(files))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database')
    parser.add_argument('--output', type=Path, help='Metadata JSON only; no personal data')
    parser.add_argument('--reference', type=Path, help='Compare a previously exported metadata JSON')
    args = parser.parse_args()
    load_dotenv(MVP_ROOT / '.env')
    result = inspect(args.database or os.getenv('MYSQL_DATABASE', 'csr'))
    if args.reference:
        reference = json.loads(args.reference.read_text(encoding='utf-8'))
        result['schema_differences'] = differences(reference['schema'], result['schema'])
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str)+'\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'schema'}, ensure_ascii=False, default=str))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
