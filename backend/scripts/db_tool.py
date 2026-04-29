import argparse
import csv
import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


READ_ONLY_PREFIXES = ("select", "with", "show", "explain", "values")


def get_database_url(explicit_url: str | None) -> str:
    database_url = explicit_url or os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set. Pass --db-url or export DATABASE_URL first.")
    return database_url.replace("+psycopg", "")


def read_sql(sql: str | None, file_path: str | None) -> str:
    if bool(sql) == bool(file_path):
        raise SystemExit("Provide exactly one of --sql or --file.")
    if sql:
        return sql.strip()
    return Path(file_path).read_text(encoding="utf-8").strip()


def is_read_only_sql(sql: str) -> bool:
    return sql.lstrip().lower().startswith(READ_ONLY_PREFIXES)


def connect(database_url: str):
    return psycopg.connect(database_url, row_factory=dict_row)


def print_table(rows: list[dict]) -> None:
    if not rows:
        print("No rows.")
        return

    headers = list(rows[0].keys())
    widths = {header: len(header) for header in headers}
    normalized_rows = []
    for row in rows:
        normalized = {}
        for header in headers:
            value = row.get(header)
            text = "" if value is None else str(value)
            normalized[header] = text
            widths[header] = max(widths[header], len(text))
        normalized_rows.append(normalized)

    print(" | ".join(header.ljust(widths[header]) for header in headers))
    print("-+-".join("-" * widths[header] for header in headers))
    for row in normalized_rows:
        print(" | ".join(row[header].ljust(widths[header]) for header in headers))


def write_rows(rows: list[dict], output_format: str, output_path: str | None) -> None:
    if output_format == "table":
        if output_path:
            raise SystemExit("--output is supported only for csv/json formats.")
        print_table(rows)
        return

    if output_format == "json":
        payload = json.dumps(rows, ensure_ascii=False, indent=2, default=str)
        if output_path:
            Path(output_path).write_text(payload + "\n", encoding="utf-8")
        else:
            print(payload)
        return

    if output_format == "csv":
        if not rows:
            if output_path:
                Path(output_path).write_text("", encoding="utf-8")
            return

        headers = list(rows[0].keys())
        if output_path:
            with open(output_path, "w", encoding="utf-8", newline="") as file_obj:
                writer = csv.DictWriter(file_obj, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        return

    raise SystemExit(f"Unsupported format: {output_format}")


def cmd_tables(args) -> None:
    with connect(get_database_url(args.db_url)) as conn, conn.cursor() as cur:
        cur.execute(
            """
            select table_schema, table_name
            from information_schema.tables
            where table_type = 'BASE TABLE'
              and table_schema not in ('pg_catalog', 'information_schema')
            order by table_schema, table_name
            """
        )
        write_rows(cur.fetchall(), args.format, args.output)


def cmd_describe(args) -> None:
    with connect(get_database_url(args.db_url)) as conn, conn.cursor() as cur:
        cur.execute(
            """
            select column_name, data_type, is_nullable, column_default
            from information_schema.columns
            where table_schema = %s and table_name = %s
            order by ordinal_position
            """,
            (args.schema, args.table),
        )
        write_rows(cur.fetchall(), args.format, args.output)


def run_read_only_query(database_url: str, sql: str) -> list[dict]:
    if not is_read_only_sql(sql):
        raise SystemExit("This command accepts only read-only SQL. Use exec --allow-write for mutations.")
    with connect(database_url) as conn, conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def cmd_query(args) -> None:
    database_url = get_database_url(args.db_url)
    rows = run_read_only_query(database_url, read_sql(args.sql, args.file))
    write_rows(rows, args.format, args.output)


def cmd_export(args) -> None:
    database_url = get_database_url(args.db_url)
    sql = args.sql.strip() if args.sql else f"select * from {args.schema}.{args.table}"
    rows = run_read_only_query(database_url, sql)
    write_rows(rows, args.format, args.output)


def cmd_exec(args) -> None:
    if not args.allow_write:
        raise SystemExit("exec requires --allow-write so mutations are always explicit.")

    database_url = get_database_url(args.db_url)
    sql = read_sql(args.sql, args.file)
    with connect(database_url) as conn, conn.cursor() as cur:
        cur.execute(sql)
        rowcount = cur.rowcount
        if cur.description:
            rows = cur.fetchall()
            conn.commit()
            write_rows(rows, args.format, args.output)
            return
        conn.commit()
        print(f"Statement executed successfully. affected_rows={rowcount}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Work with PostgreSQL through DATABASE_URL.")
    parser.add_argument("--db-url", help="Override DATABASE_URL for this command.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    tables_parser = subparsers.add_parser("tables", help="List user tables.")
    tables_parser.add_argument("--format", choices=("table", "json", "csv"), default="table")
    tables_parser.add_argument("--output", help="Write json/csv output to a file.")
    tables_parser.set_defaults(func=cmd_tables)

    describe_parser = subparsers.add_parser("describe", help="Describe a table.")
    describe_parser.add_argument("table", help="Table name without schema.")
    describe_parser.add_argument("--schema", default="public", help="Schema name. Default: public.")
    describe_parser.add_argument("--format", choices=("table", "json", "csv"), default="table")
    describe_parser.add_argument("--output", help="Write json/csv output to a file.")
    describe_parser.set_defaults(func=cmd_describe)

    query_parser = subparsers.add_parser("query", help="Run a read-only SQL query.")
    query_parser.add_argument("--sql", help="Inline SQL to execute.")
    query_parser.add_argument("--file", help="Path to a .sql file.")
    query_parser.add_argument("--format", choices=("table", "json", "csv"), default="table")
    query_parser.add_argument("--output", help="Write json/csv output to a file.")
    query_parser.set_defaults(func=cmd_query)

    export_parser = subparsers.add_parser("export", help="Export table data or query results.")
    export_parser.add_argument("--table", help="Table name without schema.")
    export_parser.add_argument("--schema", default="public", help="Schema name. Default: public.")
    export_parser.add_argument("--sql", help="Optional custom read-only SQL instead of --table.")
    export_parser.add_argument("--format", choices=("json", "csv", "table"), default="csv")
    export_parser.add_argument("--output", help="Write output to a file.")
    export_parser.set_defaults(func=cmd_export)

    exec_parser = subparsers.add_parser("exec", help="Run SQL that may modify data.")
    exec_parser.add_argument("--sql", help="Inline SQL to execute.")
    exec_parser.add_argument("--file", help="Path to a .sql file.")
    exec_parser.add_argument("--allow-write", action="store_true", help="Required for INSERT/UPDATE/DELETE/DDL.")
    exec_parser.add_argument("--format", choices=("table", "json", "csv"), default="table")
    exec_parser.add_argument("--output", help="Write json/csv output to a file.")
    exec_parser.set_defaults(func=cmd_exec)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "export" and not args.sql and not args.table:
        parser.error("export requires either --table or --sql.")
    args.func(args)


if __name__ == "__main__":
    main()
