"""
Admin Waitlist page: everyone who joined the waitlist.

  GET /api/control/waitlist         the list (search, paging) and totals
  GET /api/control/waitlist/export  every row as a CSV file, to open in
                                    Google Sheets (File > Import) or Excel

The `waitlist` table belongs to the waitlist app, which shares this database,
so it isn't one of our models: it is read with plain SQL, with whatever
columns it has. Each row also says whether that person has since made a
Lavoo account, and their plan. If the table doesn't exist, the page says so.
Nothing here changes data.
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


def _columns(db: Session) -> list[str]:
    """The waitlist table's columns, in table order ([] if there's no table)."""
    rows = db.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = 'waitlist' ORDER BY ordinal_position")).all()
    return [r[0] for r in rows if r[0] not in _HIDDEN]


def _plain(value):
    """A value the page and the CSV can show (dates as ISO text)."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _query(db: Session, columns: list[str], search: str | None, limit: int | None, offset: int):
    """The waitlist rows, newest first, with whether each person now has a
    Lavoo account and their plan. Returns (rows, total)."""
    # 1. The columns, plus the account match (by email, any capitals).
    picked = ", ".join(f'w."{c}"' for c in columns)
    where, params = "", {}
    if search and search.strip():
        searchable = [c for c in ("email", "name", "referral_code", "referrer_code", "referral_source") if c in columns]
        where = "WHERE " + " OR ".join(f'CAST(w."{c}" AS TEXT) ILIKE :q' for c in searchable)
        params["q"] = f"%{search.strip()}%"
    order = 'w."created_at" DESC' if "created_at" in columns else 'w."id" DESC'
    sql = (f'SELECT {picked}, (u.id IS NOT NULL) AS has_lavoo_account, u.subscription_status AS lavoo_plan '
           f'FROM waitlist w LEFT JOIN users u ON LOWER(u.email) = LOWER(w.email) {where} ORDER BY {order}')
    # 2. One page of it (or everything, for the file).
    if limit is not None:
        sql += " LIMIT :limit OFFSET :offset"
        params.update(limit=limit, offset=offset)
    rows = [{k: _plain(v) for k, v in r._mapping.items()} for r in db.execute(text(sql), params).all()]
    total = db.execute(text(f"SELECT COUNT(*) FROM waitlist w {where}"), params).scalar() or 0
    return rows, total


@router.get("")
def list_waitlist(search: str | None = None, limit: int = 50, offset: int = 0,
                  admin=Depends(admin_required), db: Session = Depends(get_db)):
    """One page of the waitlist, with totals."""
    # 1. No waitlist table in this database: say so plainly.
    columns = _columns(db)
    if not columns:
        return {"success": True, "data": {"available": False, "rows": [], "columns": [], "total": 0,
                                          "message": "There is no waitlist table in this database. It may have "
                                                     "been dropped by an old migration, or the waitlist app keeps "
                                                     "it in a different database."}}
    # 2. The page, and how many joined in all / have made an account.
    rows, total = _query(db, columns, search, max(1, min(limit, 200)), max(0, offset))
    everyone = db.execute(text("SELECT COUNT(*) FROM waitlist")).scalar() or 0
    with_account = db.execute(text(
        "SELECT COUNT(*) FROM waitlist w JOIN users u ON LOWER(u.email) = LOWER(w.email)")).scalar() or 0
    return {"success": True, "data": {"available": True, "rows": rows, "total": total, "everyone": everyone,
                                      "with_account": with_account,
                                      "columns": columns + ["has_lavoo_account", "lavoo_plan"]}}


@router.get("/export")
def export_waitlist(admin=Depends(admin_required), db: Session = Depends(get_db)):
    """Every waitlist row as a CSV file (opens in Google Sheets and Excel)."""
    columns = _columns(db)
    out = io.StringIO()
    out.write("﻿")  # so Excel reads names with accents correctly
    writer = csv.writer(out)
    if columns:
        rows, _ = _query(db, columns, None, None, 0)
        header = columns + ["has_lavoo_account", "lavoo_plan"]
        writer.writerow(header)
        for row in rows:
            writer.writerow(["yes" if row.get(c) is True else "no" if row.get(c) is False else row.get(c)
                             for c in header])
    else:
        writer.writerow(["There is no waitlist table in this database."])
    name = f"lavoo-waitlist-{date.today().isoformat()}.csv"
    return StreamingResponse(iter([out.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})
