import os
import sqlite3

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Show SQLite schema and sample rows from the project database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            help="Only display a single table by name.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Number of rows to show per table (default: 5).",
        )

    def handle(self, *args, **options):
        db_name = settings.DATABASES["default"]["NAME"]
        if not os.path.exists(db_name):
            self.stderr.write(f"Database not found at: {db_name}")
            return

        limit = max(options["limit"], 0)
        target_table = options.get("table")

        with sqlite3.connect(db_name) as conn:
            conn.row_factory = sqlite3.Row
            tables = self._get_tables(conn, target_table)
            if not tables:
                self.stdout.write("No tables found.")
                return

            for table in tables:
                self._print_table(conn, table, limit)

    def _get_tables(self, conn, target_table):
        if target_table:
            return [target_table]

        cursor = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type IN ('table', 'view')
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        )
        return [row[0] for row in cursor.fetchall()]

    def _print_table(self, conn, table, limit):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"{table}")
        self.stdout.write("-" * 80)

        columns = self._get_columns(conn, table)
        if columns:
            self.stdout.write("Columns: " + ", ".join(columns))
        else:
            self.stdout.write("Columns: (none)")

        if limit == 0:
            self.stdout.write("Rows: (skipped by --limit 0)")
            return

        query = f'SELECT * FROM "{table}" LIMIT {limit}'
        rows = conn.execute(query).fetchall()
        if not rows:
            self.stdout.write("Rows: (none)")
            return

        for row in rows:
            self.stdout.write("- " + ", ".join(f"{key}={row[key]}" for key in row.keys()))

    def _get_columns(self, conn, table):
        cursor = conn.execute(f'PRAGMA table_info("{table}");')
        return [row[1] for row in cursor.fetchall()]
