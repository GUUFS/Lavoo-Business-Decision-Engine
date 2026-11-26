"""
Admin Waitlist page (api/routes/admin/waitlist.py) and where a refund is now
(subscriptions/admin_refunds.refund_status).
"""
import asyncio
from unittest.mock import patch

from sqlalchemy import text

from api.routes.admin import waitlist
from api.services import admin_access
from database.pg_models import User
from subscriptions import admin_refunds


def _waitlist_table(db):
    """The waitlist app's table, as it is in production (rolled back after the test)."""
    db.execute(text("DROP TABLE IF EXISTS waitlist"))
    db.execute(text("""CREATE TABLE waitlist (id SERIAL PRIMARY KEY, email VARCHAR(255) NOT NULL, name VARCHAR(255),
        created_at TIMESTAMP NOT NULL DEFAULT now(), referral_code VARCHAR, referral_count INTEGER DEFAULT 0,
        mailerlite_subscriber_id VARCHAR(100))"""))
    db.execute(text("""INSERT INTO waitlist (email, name, created_at, referral_code, mailerlite_subscriber_id) VALUES
        ('ada@wait.test', 'Ada', '2026-01-02', 'ADA1', 'ml-1'),
        ('Bola@Wait.test', 'Bola', '2026-01-05', 'BOL2', 'ml-2')"""))
    db.add(User(name="Bola", email="bola@wait.test", password="x", confirm_password="x", subscription_status="active"))
    db.flush()


def test_waitlist_lists_everyone_newest_first_with_their_account(db):
    _waitlist_table(db)
    data = waitlist.list_waitlist(admin=None, db=db)["data"]
    assert data["available"] and data["everyone"] == 2 and data["with_account"] == 1
    assert [r["email"] for r in data["rows"]] == ["Bola@Wait.test", "ada@wait.test"]
    bola, ada = data["rows"]
    assert bola["has_lavoo_account"] is True and bola["lavoo_plan"] == "active"
    assert ada["has_lavoo_account"] is False
    # Internal sync bookkeeping is left out.
    assert "mailerlite_subscriber_id" not in data["columns"]


def test_waitlist_search(db):
    _waitlist_table(db)
    data = waitlist.list_waitlist(search="ada", admin=None, db=db)["data"]
    assert data["total"] == 1 and data["rows"][0]["name"] == "Ada"


def test_waitlist_file_has_every_row(db):
    _waitlist_table(db)
    response = waitlist.export_waitlist(admin=None, db=db)


    async def read():
        """The streamed file's text."""
        return "".join([c if isinstance(c, str) else c.decode() async for c in response.body_iterator])
    body = asyncio.run(read())
    lines = body.lstrip("﻿").strip().splitlines()
    assert lines[0].startswith("id,email,name,created_at") and lines[0].endswith("has_lavoo_account,lavoo_plan")
    assert len(lines) == 3 and "yes,active" in lines[1]
    assert "attachment" in response.headers["content-disposition"]


def test_no_waitlist_table_is_said_plainly(db):
    db.execute(text("DROP TABLE IF EXISTS waitlist"))
    data = waitlist.list_waitlist(admin=None, db=db)["data"]
    assert data["available"] is False and "no waitlist table" in data["message"]


def test_waitlist_is_its_own_admin_area():
    assert admin_access.area_for("/api/control/waitlist/export") == "waitlist"


def test_refund_status_in_plain_words_with_the_bank_reference(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test")
    refund = {"id": "re_1", "status": "succeeded",
              "destination_details": {"card": {"reference": "74987654321098765432109", "reference_status": "available"}}}
    with patch("stripe.Refund.retrieve", return_value=refund):
        status = admin_refunds.refund_status("re_1")
    assert status["status"] == "succeeded" and "5 to 10 business days" in status["meaning"]
    assert status["bank_reference"] == "74987654321098765432109"
    assert admin_refunds.refund_status(None) is None
