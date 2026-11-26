"""
Admin Waitlist page: everyone who joined the waitlist.

  GET /api/control/waitlist         the list (search, paging) and totals
  GET /api/control/waitlist/export  every row as a CSV file, to open in
                                    Google Sheets (File > Import) or Excel
  GET /api/control/waitlist/scan    every table in the database the backend
                                    is connected to, with row counts, which
                                    server that is, and any table that looks
                                    like a waitlist (to find where it is)

The waitlist table belongs to the waitlist app, which shares the database,
so it isn't one of our models: it is read with plain SQL, with whatever
columns it has. It is looked for in EVERY schema, by any table name
containing "waitlist" (the exact name first, then the one with most rows).
Each row also says whether that person has since made a Lavoo account, and
their plan. Nothing here changes data.
"""
import csv
import io
from datetime import date, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.routes.dependencies import admin_required
from database.pg_connections import get_db

router = APIRouter(prefix="/control/waitlist", tags=["admin-waitlist"])

# Columns left out: internal sync bookkeeping, not useful to read.
_HIDDEN = {"mailerlite_subscriber_id", "mailerlite_sync_status", "mailerlite_sync_at", "mailerlite_synced_at",
           "last_checked_position"}
# Postgres's own schemas (never ours).
_NOT_OURS = "('pg_catalog', 'information_schema', 'pg_toast')"
BOM = "﻿"  # at the start of the CSV, so Excel reads accents correctly


def _ident(name: str) -> str:
    """A table, schema or column name, quoted for SQL (names come from the catalog)."""
    return '"' + name.replace('"', '""') + '"'


def _count(db: Session, schema: str, table: str) -> int | None:
    """Rows in one table (None if it can't be read)."""
    try:
        with db.begin_nested():
            return db.execute(text(f"SELECT COUNT(*) FROM {_ident(schema)}.{_ident(table)}")).scalar() or 0
    except Exception:
        return None


def _find_table(db: Session) -> tuple[str, str] | None:
    """(schema, table) of the waitlist, in any schema. None if there is none."""
    # 1. Every table whose name contains "waitlist" or "wait_list".
    found = db.execute(text(
        "SELECT table_schema, table_name FROM information_schema.tables "
        f"WHERE table_type = 'BASE TABLE' AND table_schema NOT IN {_NOT_OURS} "
        "AND (table_name ILIKE '%waitlist%' OR table_name ILIKE '%wait_list%')")).all()
    if not found:
        return None
    # 2. The exact name "waitlist" first, then the one with most rows.
    ranked = sorted(found, key=lambda r: (r[1].lower() != "waitlist", -(_count(db, r[0], r[1]) or 0)))
    return ranked[0][0], ranked[0][1]


def _columns(db: Session, where: tuple[str, str]) -> list[str]:
    """The waitlist table's columns, in table order (sync bookkeeping left out)."""
    rows = db.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = :schema AND table_name = :table ORDER BY ordinal_position"),
        {"schema": where[0], "table": where[1]}).all()
    return [r[0] for r in rows if r[0] not in _HIDDEN]


def _plain(value):
    """A value the page and the CSV can show (dates as ISO text)."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _query(db: Session, where_table: tuple[str, str], columns: list[str], search: str | None,
           limit: int | None, offset: int) -> tuple[list[dict], int]:
    """The waitlist rows, newest first, with whether each person now has a
    Lavoo account and their plan. Returns (rows, total matching)."""
    table = f"{_ident(where_table[0])}.{_ident(where_table[1])}"
    # 1. The columns, plus the account match by email (any capitals), if there is an email column.
    picked = ", ".join(f"w.{_ident(c)}" for c in columns)
    if "email" in columns:
        extra = ", (u.id IS NOT NULL) AS has_lavoo_account, u.subscription_status AS lavoo_plan"
        join = "LEFT JOIN users u ON LOWER(u.email) = LOWER(w.email)"
    else:
        extra, join = "", ""
    # 2. Search by email, name or referral code.
    where, params = "", {}
    if search and search.strip():
        searchable = [c for c in ("email", "name", "referral_code", "referrer_code", "referral_source") if c in columns]
        if searchable:
            where = "WHERE " + " OR ".join(f"CAST(w.{_ident(c)} AS TEXT) ILIKE :q" for c in searchable)
            params["q"] = f"%{search.strip()}%"
    order = "w.created_at DESC" if "created_at" in columns else ("w.id DESC" if "id" in columns else "1")
    sql = f"SELECT {picked}{extra} FROM {table} w {join} {where} ORDER BY {order}"
    # 3. One page of it (or everything, for the file).
    if limit is not None:
        sql += " LIMIT :limit OFFSET :offset"
        params.update(limit=limit, offset=offset)
    rows = [{k: _plain(v) for k, v in r._mapping.items()} for r in db.execute(text(sql), params).all()]
    total = db.execute(text(f"SELECT COUNT(*) FROM {table} w {where}"), params).scalar() or 0
    return rows, total


def _shown_columns(columns: list[str]) -> list[str]:
    """The columns the page and the file show (the account match only with an email column)."""
    return columns + (["has_lavoo_account", "lavoo_plan"] if "email" in columns else [])


@router.get("")
def list_waitlist(search: str | None = None, limit: int = 50, offset: int = 0,
                  admin=Depends(admin_required), db: Session = Depends(get_db)):
    """One page of the waitlist, with totals."""
    # 1. Where the waitlist is; none found: say so and point to the scan.
    where = _find_table(db)
    if where is None:
        return {"success": True, "data": {
            "available": False, "rows": [], "columns": [], "total": 0,
            "message": "No waitlist table was found in the database this backend is connected to (every schema "
                       "was searched). Use “Scan the database” to see every table it has: the waitlist app may "
                       "keep its data in a different database (for example the old Neon one)."}}
    # 2. The page, and how many joined in all / have made an account.
    columns = _columns(db, where)
    rows, total = _query(db, where, columns, search, max(1, min(limit, 200)), max(0, offset))
    table = f"{_ident(where[0])}.{_ident(where[1])}"
    everyone = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
    with_account = db.execute(text(
        f"SELECT COUNT(*) FROM {table} w JOIN users u ON LOWER(u.email) = LOWER(w.email)")).scalar() or 0 \
        if "email" in columns else 0
    return {"success": True, "data": {"available": True, "table": f"{where[0]}.{where[1]}", "rows": rows,
                                      "total": total, "everyone": everyone, "with_account": with_account,
                                      "columns": _shown_columns(columns)}}


@router.get("/export")
def export_waitlist(admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Every waitlist row as a CSV file (opens in Google Sheets and Excel)."""
    out = io.StringIO()
    out.write(BOM)
    writer = csv.writer(out)
    where = _find_table(db)
    if where is not None:
        # 1. A heading row, then every row (true/false as yes/no).
        columns = _columns(db, where)
        rows, _ = _query(db, where, columns, None, None, 0)
        header = _shown_columns(columns)
        writer.writerow(header)
        for row in rows:
            writer.writerow(["yes" if row.get(c) is True else "no" if row.get(c) is False else row.get(c)
                             for c in header])
    else:
        writer.writerow(["No waitlist table was found in this database."])
    name = f"lavoo-waitlist-{date.today().isoformat()}.csv"
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/scan")
def scan_database(admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Every table in the database the backend uses, with row counts, and
    which database server that is, so you can see where the waitlist is."""
    # 1. Which database this is (name, server, and the host it runs on).
    info = db.execute(text("SELECT current_database(), inet_server_addr()::text, split_part(version(), ' ', 2)")).one()
    # 2. Every table, with whether it has an email column.
    tables = db.execute(text(
        "SELECT t.table_schema, t.table_name, "
        "  EXISTS (SELECT 1 FROM information_schema.columns c WHERE c.table_schema = t.table_schema "
        "          AND c.table_name = t.table_name AND c.column_name ILIKE '%email%') AS has_email "
        "FROM information_schema.tables t "
        f"WHERE t.table_type = 'BASE TABLE' AND t.table_schema NOT IN {_NOT_OURS} "
        "ORDER BY t.table_schema, t.table_name")).all()
    rows = []
    for schema, name, has_email in tables:
        looks_like_waitlist = "wait" in name.lower()
        rows.append({"schema": schema, "table": name, "rows": _count(db, schema, name),
                     "has_email": bool(has_email), "looks_like_waitlist": looks_like_waitlist})
    # 3. Waitlist-like tables first, then the rest by name.
    rows.sort(key=lambda r: (not r["looks_like_waitlist"], r["schema"], r["table"]))
    where = _find_table(db)
    return {"success": True, "data": {
        "database": info[0], "server": info[1], "postgres_version": info[2], "tables": rows,
        "waitlist_table": f"{where[0]}.{where[1]}" if where else None}}
