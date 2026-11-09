"""
End-to-end simulation of Lavoo's payment and builder-payout system.

Runs a seeded population of referrers and referred subscribers through the
REAL payment code, against a throwaway Postgres database (lavoo_sim):

  - Stripe payments:      subscriptions/stripe.py  stripe_webhook
                          (invoice.payment_succeeded, first payments and
                          renewals, including duplicate webhook deliveries)
  - Flutterwave payments: subscriptions/flutterwave.py  verify_flutterwave_payment
                          (first payments and plan switches, with the
                          subaccount split decided before the charge)
  - Flutterwave renewals: api/main.py  _attempt_flutterwave_renewal
  - Payout retry jobs:    CommissionService.settle_pending_*_commissions

Only the outside world is simulated: Stripe (registered price catalog,
subscriptions, Connect accounts, transfers, balance), Flutterwave (verify,
tokenized charges, transfers, balance, fees), FX rates, email and
notifications. Every real network connection is blocked, so nothing can
reach a real provider or send a real email.

An independent "oracle" model of the business rules predicts every
outcome, and each event is checked against it:
  - price charged (registered founding/standard price, founding rules)
  - whether a commission exists, its rate and amount (6 paid months rule,
    referrer tier at payment time, Starter first-payment-only, staff pool)
  - how it is paid: Flutterwave split, Flutterwave transfer in NGN, Stripe
    Connect transfer in the referrer's currency (cross-currency via FX), or
    left pending (no payout account / not enough balance), and later paid
    by the retry jobs once the balance is topped up
  - no duplicate payments/commissions/transfers, no negative balance
  - admin revenue (dashboard = revenue page) equals payments minus bonuses

Usage (needs a LOCAL Postgres with pgvector; the URL's server is used to
create the lavoo_sim database, which is dropped and rebuilt each run):

    SIM_BASE_DATABASE_URL=postgresql://postgres@localhost/postgres \\
        venv/bin/python -m tests.simulation.payment_simulation --out /tmp/sim

It prints a summary, writes events.jsonl (every event and check),
report.json and report.md to --out, and exits 1 if any check failed.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import socket
import sys
from collections import Counter, defaultdict
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

SIM_DB_NAME = "lavoo_sim"
TIERS = ("pro", "premium")
PERIODS = ("monthly", "quarterly", "yearly")
MONTHS = {"monthly": 1, "quarterly": 3, "yearly": 12}
RATES = {"pro": Decimal("0.25"), "premium": Decimal("0.40"), "partner": Decimal("0.50"),
         "starter": Decimal("0.10"), "staff_pool": Decimal("0.30")}
CENT = Decimal("0.01")

# The simulated Stripe price catalog: what is "registered" in Stripe for
# this run. Test data only; the app itself reads prices from Stripe.
CATALOG = {
    "founding": {
        "pro": {"USD": (9, 18, 55), "GBP": (7, 14, 44), "NGN": (7500, 15000, 50000)},
        "premium": {"USD": (15, 30, 99), "GBP": (12, 24, 79), "NGN": (12500, 25000, 85000)},
    },
    "standard": {
        "pro": {"USD": (19, 51, 177), "GBP": (15, 40, 140), "NGN": (20000, 54000, 190000)},
        "premium": {"USD": (35, 94, 327), "GBP": (27, 72, 252), "NGN": (35000, 94500, 330000)},
    },
}
# Simulated FX rates (what Flutterwave's rate endpoint would return).
FX = {("USD", "NGN"): Decimal("1500"), ("GBP", "NGN"): Decimal("1900"),
      ("NGN", "GBP"): Decimal("0.000526"), ("NGN", "USD"): Decimal("0.000667"),
      ("USD", "GBP"): Decimal("0.79"), ("GBP", "USD"): Decimal("1.27")}
# Founding prices end here (first moment they no longer apply).
FOUNDING_ENDS = datetime(2027, 2, 1, tzinfo=UTC)
SIM_START = datetime(2026, 11, 9, tzinfo=UTC)


def catalog_price(price_type: str, tier: str, currency: str, period: str) -> Decimal:
    """A registered price from the simulated Stripe catalog."""
    return Decimal(CATALOG[price_type][tier][currency][PERIODS.index(period)])


def price_id(price_type: str, tier: str, currency: str, period: str) -> str:
    """The simulated Stripe Price ID for one catalog entry."""
    return f"price_sim_{price_type}_{tier}_{period}_{currency.lower()}"


def add_months(dt: datetime, months: int) -> datetime:
    """Same day `months` later (day clamped to 28 to keep it simple)."""
    y, m = divmod(dt.month - 1 + months, 12)
    return dt.replace(year=dt.year + y, month=m + 1, day=min(dt.day, 28))


# ── Database and environment ────────────────────────────────────────────────

def prepare_database(base_url: str) -> str:
    """Drop and recreate the lavoo_sim database on the same (local) server
    as base_url, with pgvector. Returns lavoo_sim's URL."""
    import psycopg2
    from sqlalchemy.engine import make_url

    url = make_url(base_url)
    host = url.host or (url.query.get("host") if url.query else "") or ""
    if host and not (host.startswith("/") or host in ("localhost", "127.0.0.1", "::1")):
        raise SystemExit("SIM_BASE_DATABASE_URL must be a LOCAL database; refusing to run.")
    dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                    (SIM_DB_NAME,))
        cur.execute(f"DROP DATABASE IF EXISTS {SIM_DB_NAME}")
        cur.execute(f"CREATE DATABASE {SIM_DB_NAME}")
    conn.close()
    sim_url = url.set(database=SIM_DB_NAME).render_as_string(hide_password=False)
    conn = psycopg2.connect(url.set(drivername="postgresql", database=SIM_DB_NAME).render_as_string(hide_password=False))
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.close()
    return sim_url


def set_environment(sim_url: str) -> None:
    """Point the app at lavoo_sim and at fake provider credentials, and
    register the simulated price IDs, BEFORE any app module is imported
    (the app reads these at import time; real values in .env are ignored
    because these are set first)."""
    os.environ.update({
        "DATABASE_URL": sim_url, "SECRET_KEY": "simulation-secret", "ENVIRONMENT": "development",
        "STRIPE_SECRET_KEY": "sk_test_simulation", "NEXT_PUBLIC_FLUTTERWAVE_SECRET_KEY": "FLWSECK_TEST-simulation",
        "REDIS_URL": "", "BASE_URL": "http://localhost",
    })
    for price_type in ("founding", "standard"):
        for tier in TIERS:
            for currency in ("USD", "GBP", "NGN"):
                for period in PERIODS:
                    middle = "_STANDARD" if price_type == "standard" else ""
                    os.environ[f"STRIPE_{tier.upper()}_{period.upper()}{middle}_PRICE_ID_{currency}"] = \
                        price_id(price_type, tier, currency, period)


BLOCKED_CONNECTIONS: list[str] = []


def install_network_guard() -> None:
    """Refuse every network connection except to this machine (Postgres
    runs on a local socket), so the simulation can never reach Stripe,
    Flutterwave, an email provider or anything else for real."""
    real_connect, real_getaddrinfo = socket.socket.connect, socket.getaddrinfo
    local = {"127.0.0.1", "::1", "localhost"}

    def guarded_connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6) and address[0] not in local:
            BLOCKED_CONNECTIONS.append(f"{address[0]}:{address[1]}")
            raise ConnectionRefusedError("network blocked by payment simulation")
        return real_connect(sock, address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if host not in local and host is not None:
            BLOCKED_CONNECTIONS.append(f"dns:{host}")
            raise socket.gaierror("network blocked by payment simulation")
        return real_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = guarded_connect
    socket.getaddrinfo = guarded_getaddrinfo


# ── The simulated outside world ─────────────────────────────────────────────

class FakeResponse:
    """Just enough of requests.Response for the app's provider calls."""

    def __init__(self, status_code: int, payload: dict):
        self.status_code, self._payload = status_code, payload
        self.text = json.dumps(payload, default=str)

    def json(self):
        return self._payload


class Providers:
    """Simulated Stripe + Flutterwave: balances, catalog, subscriptions,
    charges and transfers. Every transfer is recorded for the checks."""

    def __init__(self, stripe_balance_minor: dict, flw_balance: Decimal):
        self.stripe_balance = dict(stripe_balance_minor)   # {"GBP": pence, "USD": cents}
        self.flw_balance = flw_balance                       # NGN, whole units
        self.stripe_subs: dict[str, dict] = {}
        self.flw_tx: dict[str, dict] = {}
        self.transfers: list[dict] = []
        self.charges: list[dict] = []
        self.modifies: list[dict] = []
        self.emails: list[str] = []
        self.alerts: list[str] = []
        self.notifications = 0
        self.unexpected: list[str] = []
        self.subaccounts: dict[tuple, str] = {}     # (account, bank) -> subaccount id
        self.subaccount_creates = 0
        self.subaccount_duplicates = 0
        self._ids = iter(range(1, 10**9))

    # Stripe ---------------------------------------------------------------
    def stripe_obj(self, data):
        import stripe
        return stripe.StripeObject.construct_from(data, None)

    def price_retrieve(self, pid, **_):
        """stripe.Price.retrieve over the simulated catalog."""
        for price_type in ("founding", "standard"):
            for tier in TIERS:
                for currency in ("USD", "GBP", "NGN"):
                    for period in PERIODS:
                        if price_id(price_type, tier, currency, period) == pid:
                            amount = catalog_price(price_type, tier, currency, period)
                            return self.stripe_obj({"id": pid, "unit_amount": int(amount * 100),
                                                    "currency": currency.lower()})
        raise RuntimeError(f"unknown simulated price {pid}")

    def subscription_object(self, sub_id):
        """The current state of a simulated Stripe subscription."""
        s = self.stripe_subs[sub_id]
        return self.stripe_obj({
            "id": sub_id, "object": "subscription", "status": "active", "customer": s["customer"],
            "metadata": {"user_id": str(s["user_id"]), "plan_type": s["period"], "plan_tier": s["tier"]},
            "items": {"data": [{"id": f"si_{sub_id}", "price": {"id": s["price_id"]},
                                "current_period_end": s["period_end"]}]},
            "current_period_start": s["period_start"], "current_period_end": s["period_end"],
        })

    def subscription_retrieve(self, sub_id, **_):
        return self.subscription_object(sub_id)

    def subscription_modify(self, sub_id, **kwargs):
        """founding.move_to_standard_if_due switching the price."""
        new_price = kwargs["items"][0]["price"]
        self.modifies.append({"sub": sub_id, "price": new_price})
        self.stripe_subs[sub_id]["price_id"] = new_price
        return self.subscription_object(sub_id)

    def account_retrieve(self, acct_id, **_):
        currency = acct_id.split("_")[-1]
        return {"id": acct_id, "capabilities": {"transfers": "active"}, "default_currency": currency}

    def transfer_list(self, transfer_group=None, **_):
        found = [{"id": t["id"], "reversed": False, "amount": t["amount_minor"], "currency": t["currency"].lower()}
                 for t in self.transfers if t["provider"] == "stripe" and t.get("group") == transfer_group]
        return self.stripe_obj({"data": found})

    def transfer_create(self, amount, currency, destination, transfer_group=None, idempotency_key=None, **_):
        """A Stripe Connect transfer: needs balance; the same idempotency key
        returns the first transfer instead of sending money twice."""
        for t in self.transfers:
            if t["provider"] == "stripe" and t["key"] == idempotency_key:
                return {"id": t["id"]}
        cur = currency.upper()
        if self.stripe_balance.get(cur, 0) < amount:
            raise RuntimeError(f"insufficient Stripe {cur} balance")
        self.stripe_balance[cur] -= amount
        tid = f"tr_sim_{next(self._ids)}"
        self.transfers.append({"provider": "stripe", "id": tid, "amount_minor": amount, "currency": cur,
                               "amount": Decimal(amount) / 100, "destination": destination,
                               "group": transfer_group, "key": idempotency_key})
        return {"id": tid}

    def stripe_available(self, currency):
        return self.stripe_balance.get(currency.upper(), 0)

    # Flutterwave ----------------------------------------------------------
    def flw_available(self, currency="NGN"):
        return {"available": self.flw_balance, "ledger": self.flw_balance}

    def requests_get(self, url, *args, **kwargs):
        if "/transactions/verify_by_reference" in url:
            tx_ref = parse_qs(urlparse(url).query)["tx_ref"][0]
            if tx_ref in self.flw_tx:
                return FakeResponse(200, {"status": "success", "data": self.flw_tx[tx_ref]})
            return FakeResponse(404, {"status": "error", "message": "not found"})
        if url.endswith("/subaccounts"):
            # Flutterwave's subaccount list (used to recover an existing one).
            rows = [{"subaccount_id": sid, "account_number": acct, "account_bank": bank}
                    for (acct, bank), sid in self.subaccounts.items()]
            return FakeResponse(200, {"status": "success", "data": rows,
                                      "meta": {"page_info": {"total_pages": 1}}})
        self.unexpected.append(f"GET {url}")
        return FakeResponse(500, {"status": "error", "message": "unexpected call in simulation"})

    def requests_post(self, url, *args, json=None, **kwargs):
        body = json or {}
        if "/charges?type=token" in url:
            # A tokenized renewal charge. With a split, Lavoo keeps
            # transaction_charge of it and the referrer's subaccount the rest.
            amount = Decimal(str(body["amount"]))
            split = (body.get("subaccounts") or [None])[0]
            lavoo_share = amount * Decimal(str(split["transaction_charge"])) if split else amount
            self.flw_balance += lavoo_share
            self.charges.append({"tx_ref": body.get("tx_ref"), "amount": amount, "split": split})
            return FakeResponse(200, {"status": "success", "data": {
                "status": "successful", "id": next(self._ids), "tx_ref": body.get("tx_ref"),
                "amount": float(amount), "currency": body.get("currency")}})
        if url.endswith("/subaccounts"):
            # Creating a split subaccount for a referrer's bank account; a
            # second one for the same account is refused, as Flutterwave does.
            key = (str(body["account_number"]), str(body["account_bank"]))
            if key in self.subaccounts:
                self.subaccount_duplicates += 1
                return FakeResponse(400, {"status": "error",
                                          "message": "A subaccount with the account number and bank already exists"})
            sid = f"RS_SELFHEAL_{next(self._ids)}"
            self.subaccounts[key] = sid
            self.subaccount_creates += 1
            return FakeResponse(200, {"status": "success", "data": {"subaccount_id": sid}})
        if url.endswith("/transfers"):
            amount = Decimal(str(body["amount"]))
            if self.flw_balance < amount:
                return FakeResponse(400, {"status": "error", "message": "Insufficient funds"})
            self.flw_balance -= amount
            tid = next(self._ids)
            self.transfers.append({"provider": "flutterwave", "id": tid, "amount": amount,
                                   "currency": body["currency"], "account": body["account_number"],
                                   "reference": body["reference"]})
            return FakeResponse(200, {"status": "success", "data": {"id": tid, "status": "NEW"}})
        self.unexpected.append(f"POST {url}")
        return FakeResponse(500, {"status": "error", "message": "unexpected call in simulation"})

    # Patches --------------------------------------------------------------
    def install(self, stack: ExitStack) -> None:
        """Patch the app's provider boundaries to this simulated world."""
        import stripe

        from api.services.notification_service import NotificationService
        from emailing.email_service import EmailService
        from subscriptions.commission_service import CommissionService
        from subscriptions.payout_service import PayoutService

        def count_notification(*a, **k):
            self.notifications += 1

        patches = [
            patch.object(stripe.Price, "retrieve", side_effect=self.price_retrieve),
            patch.object(stripe.Subscription, "retrieve", side_effect=self.subscription_retrieve),
            patch.object(stripe.Subscription, "modify", side_effect=self.subscription_modify),
            patch.object(stripe.Subscription, "list", side_effect=lambda **k: self.stripe_obj({"data": []})),
            patch.object(stripe.Account, "retrieve", side_effect=self.account_retrieve),
            patch.object(stripe.Transfer, "list", side_effect=self.transfer_list),
            patch.object(stripe.Transfer, "create", side_effect=self.transfer_create),
            patch.object(PayoutService, "get_platform_stripe_available", side_effect=self.stripe_available),
            patch.object(PayoutService, "get_platform_flutterwave_available", side_effect=self.flw_available),
            patch("subscriptions.flutterwave_split.get_flutterwave_fx_rate", side_effect=lambda s, d: FX[(s.upper(), d.upper())]),
            patch("subscriptions.flutterwave_split.get_flutterwave_processing_fee",
                  side_effect=lambda amount, currency, payment_type="card": (Decimal(str(amount)) * Decimal("0.014")).quantize(CENT)),
            patch("requests.get", side_effect=self.requests_get),
            patch("requests.post", side_effect=self.requests_post),
            patch.object(EmailService, "_send_email", side_effect=lambda *a, **k: self.emails.append(str(k.get("subject") or a[2:3])) or True),
            patch.object(CommissionService, "_alert_admin", side_effect=lambda subject, body: self.alerts.append(subject)),
            patch.object(NotificationService, "create_notification", side_effect=count_notification),
        ]
        for p in patches:
            stack.enter_context(p)


# ── The world being simulated, and the oracle's expectations ───────────────

@dataclass
class Referrer:
    """A user who refers others. tier: pro/premium/starter/partner;
    rail: how they get paid (flw_subaccount, flw_bank, stripe_gbp, stripe_usd, none)."""
    key: str
    tier: str
    rail: str
    user_id: int = 0
    active: bool = True          # oracle: actively subscribed right now
    lapse: str | None = None     # "free" or "expired" partway through
    earned: Counter = field(default_factory=Counter)


@dataclass
class Referral:
    """A referred subscriber and the payments they will make."""
    key: str
    referrer: Referrer
    provider: str                # stripe or flutterwave
    currency: str
    tier: str
    steps: list[str]             # billing period of each payment, in order
    pattern: str
    staff_pool: bool = False
    duplicate_webhooks: bool = False
    user_id: int = 0
    email: str = ""
    paid_periods: list[str] = field(default_factory=list)   # oracle: recorded payments
    founding_paid: set = field(default_factory=set)          # oracle: periods paid at founding price
    stripe_sub: str | None = None
    stripe_period: str | None = None


PATTERNS = {
    "monthly_x8": ["monthly"] * 8,
    "quarterly_x3": ["quarterly"] * 3,
    "yearly_x2": ["yearly", "yearly"],
    "monthly_then_yearly": ["monthly", "monthly", "yearly", "yearly"],
    "six_monthly_then_yearly": ["monthly"] * 6 + ["yearly"],
    "monthly_then_quarterly": ["monthly"] * 4 + ["quarterly", "quarterly"],
    "monthly_x3": ["monthly"] * 3,
}


def build_world(seed: int, n_referrers: int, referrals_each: int) -> tuple[list[Referrer], list[Referral]]:
    """A deterministic random population covering every tier, payout rail,
    provider/currency combination and payment pattern."""
    rng = random.Random(seed)
    tiers = ["pro", "premium", "starter", "partner"]
    rails = ["flw_subaccount", "flw_bank", "stripe_gbp", "stripe_usd", "none"]
    referrers, referrals = [], []
    for i in range(n_referrers):
        lapse = rng.choice([None, None, None, "free", "expired"]) if tiers[i % 4] in ("pro", "premium") else None
        referrers.append(Referrer(key=f"R{i + 1}", tier=tiers[i % 4], rail=rails[(i // 4 + i) % 5], lapse=lapse))
    n = 0
    for r in referrers:
        for _ in range(referrals_each):
            n += 1
            provider = rng.choice(["stripe", "flutterwave"])
            currency = rng.choice(["USD", "GBP"]) if provider == "stripe" else "NGN"
            pattern = rng.choice(list(PATTERNS))
            referrals.append(Referral(
                key=f"F{n}", referrer=r, provider=provider, currency=currency, tier=rng.choice(TIERS),
                steps=list(PATTERNS[pattern]), pattern=pattern,
                duplicate_webhooks=provider == "stripe" and rng.random() < 0.3))
    # Staff-pool sign-ups (no referral code): flat 30%, any number of payments.
    staff = [Referrer(key=f"S{i + 1}", tier="staff", rail=rail) for i, rail in enumerate(["flw_bank", "stripe_gbp"])]
    referrers += staff
    for s in staff:
        for provider, currency in (("stripe", "USD"), ("flutterwave", "NGN")):
            n += 1
            referrals.append(Referral(key=f"F{n}", referrer=s, provider=provider, currency=currency, tier="pro",
                                      steps=["monthly"] * 8, pattern="staff_pool_monthly_x8", staff_pool=True))
    return referrers, referrals


class Oracle:
    """Predicts what the system should do, from the business rules alone."""

    @staticmethod
    def commission(referral: Referral) -> tuple[bool, Decimal, str]:
        """(eligible, rate, tier used) for the referral's NEXT payment."""
        if referral.staff_pool:
            return True, RATES["staff_pool"], "staff_pool"
        r = referral.referrer
        tier = r.tier if (r.tier == "partner" or r.active) else "starter"
        if tier == "starter":
            return not referral.paid_periods, RATES["starter"], "starter"
        months_before = sum(MONTHS[p] for p in referral.paid_periods)
        return months_before < 6, RATES[tier], tier

    @staticmethod
    def flw_price_type(referral: Referral, period: str) -> str:
        """founding.price_type_for, with today's date before the founding end:
        monthly always founding; quarterly/yearly founding only the first time."""
        if period == "monthly":
            return "founding"
        return "standard" if period in referral.founding_paid else "founding"

    @staticmethod
    def payout(referral: Referral, commission_exact: Decimal, split: bool, providers) -> dict:
        """How the commission should be paid right now."""
        if split:
            return {"status": "auto_settled", "provider": None}
        rail, ccy = referral.referrer.rail, referral.currency
        if rail in ("flw_subaccount", "flw_bank"):
            amount = commission_exact if ccy == "NGN" else (commission_exact * FX[(ccy, "NGN")]).quantize(CENT)
            if providers.flw_balance >= amount:
                return {"status": "auto_settled", "provider": "flutterwave", "currency": "NGN", "amount": amount}
            return {"status": "pending", "provider": None, "waiting": "flutterwave balance"}
        if rail in ("stripe_gbp", "stripe_usd"):
            target = rail.split("_")[1].upper()
            amount = commission_exact if ccy == target else (commission_exact * FX[(ccy, target)]).quantize(CENT)
            minor = int(amount * 100)
            if minor < 1:
                return {"status": "pending", "provider": None, "waiting": "below 0.01"}
            if providers.stripe_balance.get(target, 0) >= minor:
                return {"status": "auto_settled", "provider": "stripe", "currency": target, "amount": amount}
            return {"status": "pending", "provider": None, "waiting": f"stripe {target} balance"}
        return {"status": "pending", "provider": None, "waiting": "no payout account"}


# ── Running it ──────────────────────────────────────────────────────────────

class Simulation:
    """Drives the real payment code event by event and checks each result."""

    def __init__(self, seed: int, n_referrers: int, referrals_each: int, out: Path):
        self.rng = random.Random(seed + 1)
        self.referrers, self.referrals = build_world(seed, n_referrers, referrals_each)
        # Deliberately tight balances so some payouts must wait for a top-up.
        self.providers = Providers({"GBP": 3000, "USD": 3000}, Decimal("20000"))
        self.out = out
        self.events: list[dict] = []
        self.violations: list[dict] = []
        self.coverage: Counter = Counter()
        self.pending: dict[int, dict] = {}    # commission id -> expected payout when settled
        self.seq = 0
        self.ids = iter(range(1, 10**9))

    # helpers --------------------------------------------------------------
    def check(self, ok: bool, event: dict, what: str, expected=None, actual=None) -> None:
        """Record one check; a failure becomes a violation."""
        event["checks"].append({"check": what, "ok": bool(ok)})
        if not ok:
            self.violations.append({"event": event["n"], "summary": event["summary"], "check": what,
                                    "expected": str(expected), "actual": str(actual)})

    def session(self):
        from database.pg_connections import SessionLocal
        return SessionLocal()

    def new_event(self, kind: str, summary: str) -> dict:
        self.seq += 1
        event = {"n": self.seq, "kind": kind, "summary": summary, "checks": [], "result": {}}
        self.events.append(event)
        return event

    # setup ----------------------------------------------------------------
    def setup_users(self) -> None:
        """Create referrers (with their own plan and payout account) and referrals."""
        from sqlalchemy.types import NullType, UserDefinedType

        from database.pg_models import Base, PayoutAccount, Subscriptions, User
        from database.pg_models import Referral as ReferralRow

        class Vector384(UserDefinedType):
            cache_ok = True

            def get_col_spec(self, **kw):
                return "vector(384)"
        for table in Base.metadata.tables.values():
            for column in table.columns:
                if isinstance(column.type, NullType):
                    column.type = Vector384()
        from database.pg_connections import engine
        Base.metadata.create_all(engine)

        now = datetime.now(UTC)
        with self.session() as db:
            for r in self.referrers:
                user = User(name=f"Referrer {r.key}", email=f"{r.key.lower()}@sim.local", password="x",
                            confirm_password="x", is_partner=r.tier == "partner", is_staff=r.tier == "staff",
                            subscription_status="active" if r.tier in ("pro", "premium") else "Free",
                            subscription_expires_at=now + timedelta(days=400) if r.tier in ("pro", "premium") else None)
                db.add(user)
                db.flush()
                r.user_id = user.id
                if r.tier in ("pro", "premium"):
                    price = catalog_price("founding", r.tier, "USD", "yearly")
                    db.add(Subscriptions(user_id=user.id, subscription_plan="yearly", plan_tier=r.tier,
                                         transaction_id=f"own-{r.key}", tx_ref=f"own-{r.key}", amount=price,
                                         currency="USD", status="completed", subscription_status="active",
                                         payment_provider="stripe", start_date=now, end_date=now + timedelta(days=365)))
                    self.coverage["referrer_own_plan_rows"] += 1
                if r.rail in ("flw_subaccount", "flw_bank"):
                    db.add(PayoutAccount(user_id=user.id, payment_method="flutterwave", bank_name="Sim Bank",
                                         bank_code="044", account_number=f"01{user.id:08d}", account_name=f"Referrer {r.key}",
                                         is_verified=True,
                                         flutterwave_subaccount_id=f"RS_SIM_{r.key}" if r.rail == "flw_subaccount" else None,
                                         subaccount_status="active" if r.rail == "flw_subaccount" else None))
                elif r.rail in ("stripe_gbp", "stripe_usd"):
                    db.add(PayoutAccount(user_id=user.id, payment_method="stripe", is_verified=True,
                                         stripe_account_id=f"acct_sim_{r.key.lower()}_{r.rail.split('_')[1]}",
                                         stripe_account_status="active"))
            for f in self.referrals:
                f.email = f"{f.key.lower()}@sim.local"
                user = User(name=f"Subscriber {f.key}", email=f.email, password="x", confirm_password="x",
                            stripe_customer_id=f"cus_sim_{f.key.lower()}")
                db.add(user)
                db.flush()
                f.user_id = user.id
                db.add(ReferralRow(referrer_id=f.referrer.user_id, referred_user_id=user.id, via_staff_pool=f.staff_pool))
            db.commit()

    # payment events -------------------------------------------------------
    def snapshot(self, user_id: int) -> int:
        """The highest Subscriptions id for this user (to find rows an event adds)."""
        from sqlalchemy import func

        from database.pg_models import Subscriptions
        with self.session() as db:
            return db.query(func.coalesce(func.max(Subscriptions.id), 0)).filter(Subscriptions.user_id == user_id).scalar()

    def stripe_payment(self, f: Referral, period: str, step: int, sim_date: datetime) -> dict:
        """Charge on Stripe and deliver invoice.payment_succeeded (twice if
        this referral's webhooks are duplicated)."""
        from starlette.requests import Request

        from subscriptions.stripe import stripe_webhook

        first_of_sub = f.stripe_sub is None or f.stripe_period != period
        if first_of_sub:
            f.stripe_sub, f.stripe_period = f"sub_sim_{f.key.lower()}_{step}", period
            self.providers.stripe_subs[f.stripe_sub] = {
                "user_id": f.user_id, "customer": f"cus_sim_{f.key.lower()}", "period": period, "tier": f.tier,
                "price_id": price_id("founding", f.tier, f.currency, period)}
        sub = self.providers.stripe_subs[f.stripe_sub]
        end = add_months(sim_date, MONTHS[period])
        sub["period_start"], sub["period_end"] = int(sim_date.timestamp()), int(end.timestamp())
        # Stripe charges whatever price is on the subscription now.
        price_type = "standard" if "standard" in sub["price_id"] else "founding"
        amount = catalog_price(price_type, f.tier, f.currency, period)
        pi = f"pi_sim_{f.key.lower()}_{step}"
        event = {"id": f"evt_{pi}", "object": "event", "type": "invoice.payment_succeeded", "data": {"object": {
            "id": f"in_{pi}", "object": "invoice", "subscription": f.stripe_sub, "payment_intent": pi,
            "billing_reason": "subscription_create" if first_of_sub else "subscription_cycle",
            "amount_paid": int(amount * 100), "currency": f.currency.lower(), "customer": sub["customer"],
            "metadata": {"user_id": str(f.user_id)},
            "lines": {"data": [{"period": {"start": sub["period_start"], "end": sub["period_end"]}}]}}}}
        body = json.dumps(event).encode()

        async def deliver():
            async def receive():
                return {"type": "http.request", "body": body, "more_body": False}
            request = Request({"type": "http", "method": "POST", "path": "/api/stripe/webhook", "headers": []}, receive)
            with self.session() as db:
                return await stripe_webhook(request, None, db)
        asyncio.run(deliver())
        deliveries = 1
        if f.duplicate_webhooks:
            asyncio.run(deliver())   # Stripe retries the same event
            deliveries = 2
        return {"amount": amount, "price_type": price_type, "split": False, "deliveries": deliveries,
                "period_end": end}

    def flutterwave_checkout(self, f: Referral, period: str, step: int, underpay: bool = False) -> dict:
        """A Flutterwave checkout: the frontend asks for the split first,
        the customer pays, then the app verifies the transaction."""
        from fastapi import BackgroundTasks, HTTPException

        from database.pg_models import User
        from subscriptions.flutterwave import (
            PaymentVerifyRequest,
            get_flutterwave_split_info,
            verify_flutterwave_payment,
        )
        from subscriptions.flutterwave_split import SPLIT_META_KEY

        price_type = Oracle.flw_price_type(f, period)
        amount = catalog_price(price_type, f.tier, "NGN", period)
        # The frontend's split-info request (GET /api/payments/flutterwave/
        # split-info), through the real endpoint, so whatever it saves (a
        # self-healed subaccount) is saved here too.
        with self.session() as db:
            user = db.get(User, f.user_id)
            info = asyncio.run(get_flutterwave_split_info(db, user))["data"]
            split = info if info.get("subaccount_id") else None
        paid = amount - 100 if underpay else amount
        tx_ref = f"TX-SIM-{f.key}-{step}{'-under' if underpay else ''}"
        meta = {SPLIT_META_KEY: split["subaccount_id"]} if split else {}
        lavoo_share = paid * Decimal(str(split["main_account_charge_percentage"])) if split else paid
        self.providers.flw_balance += lavoo_share
        self.providers.flw_tx[tx_ref] = {
            "status": "successful", "id": next(self.ids), "tx_ref": tx_ref, "amount": float(paid), "currency": "NGN",
            "meta": meta, "card": {"token": f"flw-token-{f.key}", "last_4digits": "4242", "type": "VISA"},
            "customer": {"email": f.email}}
        status = 200
        try:
            with self.session() as db:
                asyncio.run(verify_flutterwave_payment(
                    PaymentVerifyRequest(transaction_id=tx_ref, user_email=f.email, plan_type=period, plan_tier=f.tier),
                    BackgroundTasks(), db))
        except HTTPException as e:
            status = e.status_code
        return {"amount": amount, "price_type": price_type, "split": bool(split), "status": status, "deliveries": 1}

    def flutterwave_renewal(self, f: Referral, period: str) -> dict:
        """The scheduled renewal job charging the saved card."""
        from api.main import _attempt_flutterwave_renewal
        price_type = Oracle.flw_price_type(f, period)
        amount = catalog_price(price_type, f.tier, "NGN", period)
        before = len(self.providers.charges)
        ok = _attempt_flutterwave_renewal(f.user_id, period, float(amount), "NGN", f.tier)
        split = bool(self.providers.charges[before]["split"]) if len(self.providers.charges) > before else False
        return {"amount": amount, "price_type": price_type, "split": split, "renewed": ok, "deliveries": 1}

    def run_payment(self, f: Referral, step: int, sim_date: datetime) -> None:
        """One payment by one referral, then every check on what happened."""
        from database.pg_models import Commission, Payout, Subscriptions
        period = f.steps[step]
        eligible, rate, tier_used = Oracle.commission(f)
        same_plan_renewal = step > 0 and f.steps[step - 1] == period
        if f.provider == "stripe":
            how = "Stripe " + ("renewal" if same_plan_renewal else "first payment")
        else:
            how = "Flutterwave " + ("renewal (saved card)" if same_plan_renewal else "checkout")
        event = self.new_event("payment", f"{how} | {f.key} ({f.tier} {period} {f.currency}, pattern {f.pattern}) "
                                          f"referred by {f.referrer.key} ({f.referrer.tier}, {f.referrer.rail}"
                                          f"{'' if f.referrer.active or f.referrer.tier in ('partner', 'staff') else ', lapsed'})")
        before_id = self.snapshot(f.user_id)
        transfers_before = len(self.providers.transfers)

        if f.provider == "stripe":
            outcome = self.stripe_payment(f, period, step, sim_date)
        elif same_plan_renewal:
            outcome = self.flutterwave_renewal(f, period)
            self.check(outcome["renewed"], event, "renewal charge succeeded", True, outcome["renewed"])
        else:
            outcome = self.flutterwave_checkout(f, period, step)
            self.check(outcome["status"] == 200, event, "checkout verified", 200, outcome["status"])

        with self.session() as db:
            rows = db.query(Subscriptions).filter(Subscriptions.user_id == f.user_id, Subscriptions.id > before_id).all()
            self.check(len(rows) == 1, event, f"exactly one payment recorded ({outcome['deliveries']} delivery/ies)", 1, len(rows))
            if not rows:
                return
            sub = rows[0]
            expected_amount = outcome["amount"]
            self.check(Decimal(sub.amount) == expected_amount, event, "amount = registered price", expected_amount, sub.amount)
            self.check(sub.subscription_plan == period, event, "billing period recorded", period, sub.subscription_plan)
            if f.provider == "flutterwave":
                self.check(outcome["price_type"] == ("founding" if period == "monthly" or period not in f.founding_paid else "standard"),
                           event, "founding rules (Flutterwave)", True, outcome["price_type"])

            commissions = db.query(Commission).filter(Commission.subscription_id == sub.id).all()
            # A referrer with a Nigerian bank account gets a split subaccount
            # (created on the spot if missing: the app's self-heal).
            split_expected = (f.provider == "flutterwave" and eligible and f.referrer.rail in ("flw_subaccount", "flw_bank"))
            self.check(outcome["split"] == split_expected, event, "Flutterwave split used iff eligible + Nigerian bank account",
                       split_expected, outcome["split"])
            self.check(len(commissions) == (1 if eligible else 0), event,
                       f"commission {'created' if eligible else 'not created'} ({tier_used}, "
                       f"{sum(MONTHS[p] for p in f.paid_periods)} paid months before)", int(eligible), len(commissions))

            new_transfers = self.providers.transfers[transfers_before:]
            result = {"amount": str(sub.amount), "currency": sub.currency, "eligible": eligible, "rate": str(rate),
                      "split": outcome["split"]}
            if eligible and commissions:
                c = commissions[0]
                exact = expected_amount * rate
                self.check(abs(Decimal(c.amount) - exact.quantize(CENT, ROUND_HALF_UP)) <= CENT, event,
                           "commission amount = rate x payment", exact, c.amount)
                self.check(Decimal(c.commission_rate) == rate * 100, event, "commission rate", rate * 100, c.commission_rate)
                self.check(c.currency == f.currency, event, "commission in payment currency", f.currency, c.currency)
                expect = Oracle.payout(f, exact, outcome["split"], BalanceBeforePayout(self.providers, new_transfers))
                self.check(c.status == expect["status"], event, f"commission status ({expect.get('waiting') or expect['provider'] or 'split'})",
                           expect["status"], c.status)
                if expect.get("provider"):
                    ok = len(new_transfers) == 1 and new_transfers[0]["provider"] == expect["provider"] \
                        and new_transfers[0]["currency"] == expect["currency"] \
                        and abs(new_transfers[0]["amount"] - expect["amount"]) <= CENT
                    self.check(ok, event, f"{expect['provider']} transfer {expect['amount']} {expect['currency']}",
                               expect, new_transfers)
                    if new_transfers and c.payout_id:
                        payout = db.get(Payout, c.payout_id)
                        self.check(payout is not None and payout.currency == expect["currency"], event,
                                   "payout row matches transfer", expect["currency"], getattr(payout, "currency", None))
                    self.coverage[f"payout_{expect['provider']}_{f.currency}_to_{expect['currency']}"] += 1
                else:
                    self.check(not new_transfers, event, "no transfer", [], new_transfers)
                    if expect["status"] == "pending":
                        self.pending[c.id] = {"referral": f, "exact": exact, "event": event["n"]}
                        self.coverage[f"pending_{expect['waiting'].replace(' ', '_')}"] += 1
                    else:
                        self.coverage["paid_by_split"] += 1
                f.referrer.earned[f.currency] += exact
                result.update({"commission": str(c.amount), "status": c.status,
                               "transfer": [{k: str(v) for k, v in t.items() if k in ("provider", "amount", "currency")}
                                            for t in new_transfers]})
                self.coverage[f"commission_{tier_used}"] += 1
            else:
                self.check(not new_transfers, event, "no transfer for an ineligible payment", [], new_transfers)
                self.coverage[f"no_commission_{tier_used}"] += 1
            event["result"] = result

        # Update the oracle's model of the world.
        f.paid_periods.append(period)
        if outcome["price_type"] == "founding":
            f.founding_paid.add(period)
        self.coverage[f"{f.provider}_{'renewal' if same_plan_renewal else 'first'}"] += 1
        if outcome.get("deliveries", 1) > 1:
            self.coverage["duplicate_webhook_ignored"] += 1
        if f.provider == "stripe":
            # founding.move_to_standard_if_due: quarterly/yearly move after
            # their first payment; monthly once the next payment is past
            # the founding end date.
            sub_state = self.providers.stripe_subs[f.stripe_sub]
            moved = "standard" in sub_state["price_id"]
            should_move = period != "monthly" or outcome["period_end"] >= FOUNDING_ENDS
            self.check(moved == should_move, event, "Stripe founding -> standard move", should_move, moved)

    def underpaid_checkout(self, f: Referral) -> None:
        """A Flutterwave checkout that paid less than the registered price:
        the plan must not be given and no commission created."""
        from database.pg_models import Commission, Subscriptions
        event = self.new_event("underpaid", f"Underpaid Flutterwave checkout | {f.key} pays registered price - 100")
        before_id = self.snapshot(f.user_id)
        period = f.steps[0]
        outcome = self.flutterwave_checkout(f, period, 99, underpay=True)
        with self.session() as db:
            rows = db.query(Subscriptions).filter(Subscriptions.user_id == f.user_id, Subscriptions.id > before_id).all()
            self.check(outcome["status"] == 400, event, "underpayment refused (HTTP 400)", 400, outcome["status"])
            self.check(not rows, event, "no payment recorded", 0, len(rows))
            self.check(db.query(Commission).filter(Commission.referred_user_id == f.user_id).count() == 0, event,
                       "no commission", 0, None)
        self.coverage["underpayment_refused"] += 1

    def lapse(self, r: Referrer) -> None:
        """A referrer stops being actively subscribed (cancelled, or the
        paid period ran out while the status still says active)."""
        from database.pg_models import User
        event = self.new_event("lapse", f"Referrer {r.key} ({r.tier}) lapses: {r.lapse}")
        with self.session() as db:
            user = db.get(User, r.user_id)
            if r.lapse == "free":
                user.subscription_status = "Free"
            else:
                user.subscription_expires_at = datetime.now(UTC) - timedelta(days=10)
            db.commit()
        r.active = False
        event["checks"].append({"check": "lapsed", "ok": True})
        self.coverage[f"referrer_lapse_{r.lapse}"] += 1

    def top_up_and_settle(self) -> None:
        """Top up both platform balances and run the payout retry jobs: every
        commission that was waiting for balance must now be paid, correctly
        converted, exactly once."""
        from database.pg_models import Commission, Payout
        from subscriptions.commission_service import CommissionService
        event = self.new_event("settle", "Top up balances (+NGN 5,000,000, +GBP/USD 2,000) and run payout retry jobs")
        self.providers.flw_balance += Decimal("5000000")
        for cur in ("GBP", "USD"):
            self.providers.stripe_balance[cur] += 200000
        transfers_before = len(self.providers.transfers)
        with self.session() as db:
            CommissionService.settle_pending_flutterwave_commissions(db, lookback_days=3650, limit=1000)
        with self.session() as db:
            CommissionService.settle_pending_stripe_commissions(db, lookback_days=3650, limit=1000)
        new_transfers = self.providers.transfers[transfers_before:]
        settled = 0
        with self.session() as db:
            for cid, info in list(self.pending.items()):
                f, exact = info["referral"], info["exact"]
                c = db.get(Commission, cid)
                expect = Oracle.payout(f, exact, False, self.providers)
                if f.referrer.rail == "none":
                    self.check(c.status == "pending" and c.payout_id is None, event,
                               f"commission #{cid} ({f.key}) stays pending: no payout account", "pending", c.status)
                    continue
                payout = db.get(Payout, c.payout_id) if c.payout_id else None
                ok = c.status == "auto_settled" and payout is not None
                if ok:
                    target = expect.get("currency") or ("NGN" if f.referrer.rail.startswith("flw") else f.referrer.rail[-3:].upper())
                    ok = payout.currency == target and abs(Decimal(payout.amount) - expect["amount"]) <= CENT
                self.check(ok, event, f"commission #{cid} ({f.key}, {exact:.2f} {f.currency}) paid after top-up",
                           expect, (c.status, getattr(payout, "amount", None), getattr(payout, "currency", None)))
                if ok:
                    settled += 1
                    del self.pending[cid]
        self.coverage["settled_after_top_up"] += settled
        event["result"] = {"settled": settled, "transfers": len(new_transfers)}

    # final checks ---------------------------------------------------------
    def final_checks(self) -> None:
        """Whole-system invariants after every event has run."""
        from sqlalchemy import func

        from api.routes.admin.dashboard import get_dashboard_stats
        from database.pg_models import Commission, Payout, Subscriptions
        event = self.new_event("final", "Whole-system checks")
        with self.session() as db:
            dupes = db.query(Commission.subscription_id).group_by(Commission.subscription_id).having(func.count() > 1).count()
            self.check(dupes == 0, event, "at most one commission per payment", 0, dupes)
            tx_dupes = db.query(Subscriptions.transaction_id).group_by(Subscriptions.transaction_id).having(func.count() > 1).count()
            self.check(tx_dupes == 0, event, "no payment recorded twice", 0, tx_dupes)
            payouts = db.query(Payout).filter(Payout.status.in_(["completed", "processing"])).count()
            self.check(payouts == len(self.providers.transfers), event, "one payout row per real transfer",
                       len(self.providers.transfers), payouts)
            linked = db.query(Commission).filter(Commission.payout_id.isnot(None)).count()
            self.check(linked == len(self.providers.transfers), event, "every transfer belongs to exactly one commission",
                       len(self.providers.transfers), linked)
            # A self-healed subaccount must be saved the first time: trying to
            # create it again means a checkout threw the new id away.
            self.check(self.providers.subaccount_duplicates == 0, event,
                       "no Flutterwave subaccount created twice", 0, self.providers.subaccount_duplicates)
            self.check(self.providers.flw_balance >= 0 and all(v >= 0 for v in self.providers.stripe_balance.values()),
                       event, "no balance went negative", ">= 0", (self.providers.flw_balance, self.providers.stripe_balance))
            self.check(not self.providers.unexpected, event, "no unexpected provider calls", [], self.providers.unexpected)
            self.check(not BLOCKED_CONNECTIONS, event, "no real network connection attempted", [], BLOCKED_CONNECTIONS)

            # Admin revenue: payments minus bonuses, per currency, and the
            # dashboard shows exactly the revenue page's figure.
            gross = dict(db.query(Subscriptions.currency, func.sum(Subscriptions.amount)).group_by(Subscriptions.currency).all())
            bonus = dict(db.query(Commission.currency, func.sum(Commission.amount)).group_by(Commission.currency).all())
            dashboard = asyncio.run(get_dashboard_stats(current_user=None, db=db))["total_revenue_by_currency"]
            for ccy, total in gross.items():
                expected = float(Decimal(total) - Decimal(bonus.get(ccy) or 0))
                self.check(abs(dashboard.get(ccy, 0) - expected) < 0.01, event,
                           f"admin revenue {ccy} = payments - builder bonuses", expected, dashboard.get(ccy))
                self.check(dashboard.get(ccy, 0) >= 0, event, f"admin revenue {ccy} not negative", ">= 0", dashboard.get(ccy))
            event["result"] = {"revenue_by_currency": dashboard}

    # main loop ------------------------------------------------------------
    def run(self) -> dict:
        """Build the world, interleave every referral's payments in time
        order (with referrer lapses, an underpayment test and a mid-run
        top-up), run them all, then the final checks."""
        self.setup_users()
        timeline = []
        for f in self.referrals:
            date = SIM_START + timedelta(days=self.rng.randint(0, 20))
            for step, period in enumerate(f.steps):
                timeline.append((date, self.rng.random(), "pay", f, step))
                date = add_months(date, MONTHS[period])
        for r in self.referrers:
            if r.lapse:
                timeline.append((add_months(SIM_START, 3), self.rng.random(), "lapse", r, 0))
        flw = [f for f in self.referrals if f.provider == "flutterwave" and not f.staff_pool]
        for f in flw[:3]:
            # Before anyone pays, so it always runs (a first payment, underpaid).
            timeline.append((SIM_START - timedelta(days=1), self.rng.random(), "underpay", f, 0))
        timeline.append((add_months(SIM_START, 5), 0.0, "settle", None, 0))
        timeline.append((add_months(SIM_START, 30), 0.0, "settle", None, 0))
        timeline.sort(key=lambda t: (t[0], t[1]))

        with ExitStack() as stack:
            self.providers.install(stack)
            for date, _, kind, obj, step in timeline:
                if kind == "pay":
                    self.run_payment(obj, step, date)
                elif kind == "lapse":
                    self.lapse(obj)
                elif kind == "underpay":
                    if not obj.paid_periods:
                        self.underpaid_checkout(obj)
                elif kind == "settle":
                    self.top_up_and_settle()
            self.final_checks()
        return self.report()

    # reporting ------------------------------------------------------------
    def report(self) -> dict:
        """Write events.jsonl, report.json and report.md; return the summary."""
        self.out.mkdir(parents=True, exist_ok=True)
        with open(self.out / "events.jsonl", "w") as fh:
            for e in self.events:
                fh.write(json.dumps(e, default=str) + "\n")
        checks = sum(len(e["checks"]) for e in self.events)
        transfers = Counter(f"{t['provider']} {t['currency']}" for t in self.providers.transfers)
        totals = defaultdict(Decimal)
        for t in self.providers.transfers:
            totals[f"{t['provider']} {t['currency']}"] += t["amount"]
        summary = {
            "events": len(self.events), "checks": checks, "violations": len(self.violations),
            "payments": sum(1 for e in self.events if e["kind"] == "payment"),
            "referrers": len(self.referrers), "referrals": len(self.referrals),
            "transfers": {k: {"count": v, "total": str(totals[k])} for k, v in transfers.items()},
            "split_renewal_charges": sum(1 for c in self.providers.charges if c["split"]),
            "subaccounts_self_healed": self.providers.subaccount_creates,
            "subaccount_duplicate_create_attempts": self.providers.subaccount_duplicates,
            "founding_to_standard_moves": len(self.providers.modifies),
            "emails_suppressed": len(self.providers.emails), "admin_alerts": len(self.providers.alerts),
            "notifications": self.providers.notifications,
            "still_pending_no_payout_account": len(self.pending),
            "coverage": dict(sorted(self.coverage.items())),
            "final_balances": {"flutterwave_NGN": str(self.providers.flw_balance),
                               "stripe_minor": self.providers.stripe_balance},
        }
        (self.out / "report.json").write_text(json.dumps({"summary": summary, "violations": self.violations}, indent=1, default=str))
        lines = ["# Payment simulation report", "",
                 f"- Events: {summary['events']} ({summary['payments']} payments), checks: {checks}, "
                 f"**violations: {len(self.violations)}**",
                 f"- Referrers: {summary['referrers']}, referred subscribers: {summary['referrals']}", "",
                 "## Transfers", "", "| Rail and currency | Count | Total |", "|---|---|---|"]
        lines += [f"| {k} | {v['count']} | {v['total']} |" for k, v in summary["transfers"].items()]
        lines += ["", "## Coverage", "", "| Scenario | Times |", "|---|---|"]
        lines += [f"| {k} | {v} |" for k, v in summary["coverage"].items()]
        lines += ["", "## Violations", ""]
        lines += [f"- event {v['event']}: {v['check']} | expected {v['expected']} got {v['actual']} | {v['summary']}"
                  for v in self.violations] or ["None."]
        lines += ["", "## Event log (first 60)", ""]
        for e in self.events[:60]:
            failed = [c["check"] for c in e["checks"] if not c["ok"]]
            lines.append(f"{e['n']}. {e['summary']} -> {json.dumps(e['result'], default=str)}"
                         f"{' FAILED: ' + '; '.join(failed) if failed else ''}")
        (self.out / "report.md").write_text("\n".join(lines) + "\n")
        return summary


class BalanceBeforePayout:
    """The balances just before this event's payout was attempted: the
    balance now plus whatever this event transferred out. (Lavoo's share of
    a Flutterwave charge lands before the payout, so it is included.)"""

    def __init__(self, providers: Providers, new_transfers: list[dict]):
        self.flw_balance = providers.flw_balance + sum(
            (t["amount"] for t in new_transfers if t["provider"] == "flutterwave"), Decimal(0))
        self.stripe_balance = dict(providers.stripe_balance)
        for t in new_transfers:
            if t["provider"] == "stripe":
                self.stripe_balance[t["currency"]] += t["amount_minor"]


def main() -> int:
    """Command-line entry point (see the module docstring)."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--referrers", type=int, default=20)
    parser.add_argument("--referrals-each", type=int, default=3)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = os.environ.get("SIM_BASE_DATABASE_URL")
    if not base:
        raise SystemExit("Set SIM_BASE_DATABASE_URL to a LOCAL Postgres (with pgvector).")

    sim_url = prepare_database(base)
    set_environment(sim_url)
    install_network_guard()
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    import api.routes.auth  # noqa: F401  (import order that avoids an existing circular import)

    summary = Simulation(args.seed, args.referrers, args.referrals_each, args.out).run()
    print(json.dumps(summary, indent=1, default=str))
    print(f"\nReport: {args.out / 'report.md'}")
    return 1 if summary["violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
