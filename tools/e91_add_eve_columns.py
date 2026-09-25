"""
Adds the two columns multiplayer E91 needs for a real Eve — ``eve_angles`` and
``eve_bits`` on the round table — to an existing SQLite database, keeping every
row that is already there.

Why a script and not a Django migration: this project's databases were built
with ``migrate --run-syncdb`` and have no migration history (migrations are
git-ignored), so ``migrate`` cannot add a column to an existing table, and
``--run-syncdb`` never does. Tracked for later: a real migration strategy.

Safe to run more than once: it adds only what is missing, and does nothing at
all when both columns exist. Before changing anything it saves a consistent
snapshot of the database next to it (``db.sqlite3.backup-<timestamp>``).

Run BEFORE starting the new code, which reads these columns:
    python tools/e91_add_eve_columns.py              # ./db.sqlite3
    python tools/e91_add_eve_columns.py /path/to/db.sqlite3
"""

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

TABLE = 'e91_e91iteration'
COLUMNS = {                       # the same as the model's CharField(max_length=30, null=True)
    'eve_angles': 'varchar(30) NULL',
    'eve_bits': 'varchar(30) NULL',
}


def columns_of(connection):
    return [row[1] for row in connection.execute(f'PRAGMA table_info({TABLE})')]


def main():
    db = Path(sys.argv[1] if len(sys.argv) > 1 else 'db.sqlite3').resolve()
    if not db.is_file():
        sys.exit(f'No database at {db}')

    connection = sqlite3.connect(db)
    existing = columns_of(connection)
    if not existing:
        sys.exit(f'No table {TABLE} in {db} — is this the QuantumCrypto database?')

    missing = [name for name in COLUMNS if name not in existing]
    if not missing:
        print(f'Nothing to do: {TABLE} already has {", ".join(COLUMNS)}.')
        return

    backup = db.with_name(f'{db.name}.backup-{datetime.now():%Y%m%d-%H%M%S}')
    with sqlite3.connect(backup) as target:
        connection.backup(target)     # a consistent snapshot, even if the server is running
    print(f'Backup saved: {backup}')

    rows = connection.execute(f'SELECT COUNT(*) FROM {TABLE}').fetchone()[0]
    for name in missing:
        connection.execute(f'ALTER TABLE {TABLE} ADD COLUMN {name} {COLUMNS[name]}')
    connection.commit()

    after = connection.execute(f'SELECT COUNT(*) FROM {TABLE}').fetchone()[0]
    print(f'Added {", ".join(missing)} to {TABLE}. Rows before: {rows}, after: {after}.')
    print(f'Columns now: {", ".join(columns_of(connection))}')
    connection.close()


if __name__ == '__main__':
    main()
