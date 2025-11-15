import sqlite3
import os
import glob
from typing import List, Optional
from robot.global_config import GlobalConfig


def _createMigrationsTable(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at INTEGER
        )
    """
    )
    conn.commit()


def _getAppliedMigrations(conn: sqlite3.Connection) -> List[str]:
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
    return [row[0] for row in cursor.fetchall()]


def _getMigrationFiles() -> List[str]:
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    pattern = os.path.join(migrations_dir, "*.sql")
    migration_files = glob.glob(pattern)
    return sorted([os.path.basename(f) for f in migration_files])


def _applyMigration(conn: sqlite3.Connection, migration_file: str) -> None:
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    file_path = os.path.join(migrations_dir, migration_file)

    with open(file_path, "r") as f:
        sql_content = f.read()

    cursor = conn.cursor()
    cursor.executescript(sql_content)

    # Record that this migration was applied
    import time

    version = migration_file.replace(".sql", "")
    applied_at = int(time.time() * 1000)
    cursor.execute(
        "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
        (version, applied_at),
    )
    conn.commit()


def initializeDatabase(global_config: GlobalConfig) -> None:
    db_path = global_config["db_path"]
    conn = sqlite3.connect(db_path)

    # Create migrations tracking table
    _createMigrationsTable(conn)

    # Get list of applied migrations
    applied_migrations = _getAppliedMigrations(conn)

    # Get list of available migration files
    migration_files = _getMigrationFiles()

    # Apply any unapplied migrations
    for migration_file in migration_files:
        version = migration_file.replace(".sql", "")
        if version not in applied_migrations:
            print(f"Applying migration: {migration_file}")
            _applyMigration(conn, migration_file)

    conn.close()


def getDatabaseConnection(global_config: GlobalConfig) -> sqlite3.Connection:
    db_path = global_config["db_path"]
    return sqlite3.connect(db_path)
