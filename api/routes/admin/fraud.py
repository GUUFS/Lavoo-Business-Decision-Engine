"""
Referral/payout fraud detection — surfaces signals that someone is farming
referrals through multiple accounts to collect payouts they shouldn't,
built entirely from data Lavoo already has (no new tracking required to
start getting value from this).

Three independent signals, from sharpest to broadest:

1. Self-referral payout match: a referrer and the person they referred
   share the same real payout destination (bank account or Stripe Connect
   account) — the single highest-confidence signal there is. A real
   referred user has their OWN bank account; if it's the same one the
   referrer uses, it's almost certainly one person running both ends.

2. Payout destination collisions: the same bank account/Stripe account is
   the payout destination for more than one Lavoo user account at all,
   referral-linked or not — one real person controlling several accounts.

3. Email pattern collisions: different-looking emails that normalize to
   the same real inbox (Gmail's dot-insensitivity, "+" sub-addressing used
   by any provider) — the classic way to make "different" signups that all
   land in one mailbox.

None of this auto-blocks anything. It's a review surface for an admin —
false positives are real (a founder and their cofounder/spouse can
legitimately share a bank account; a referred user understandably reusing
a known-good card is not proof of fraud on its own), so a human decides
what to do with a match, not this code.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import re

from database.pg_connections import get_db
from database.pg_models import User, Referral, PayoutAccount
from api.routes.dependencies import admin_required

router = APIRouter(prefix="/control/fraud", tags=["admin-fraud"])


def normalize_email(email: str) -> str:
    """Collapses the cosmetic tricks used to make one inbox look like many
    signups: Gmail (and Google Workspace) ignores dots in the local part
    and treats everything after a '+' as a discardable tag — a behavior
    the SMTP spec leaves provider-specific, so this only applies it to
    gmail.com/googlemail.com, not every domain (an ISP that actually
    delivers to a literal "+"-containing mailbox would otherwise collide
    unrelated real users)."""
    email = (email or "").strip().lower()
    if "@" not in email:
        return email
    local, _, domain = email.partition("@")
    local = local.split("+", 1)[0]
    if domain in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")
    return f"{local}@{domain}"


def _payout_destination_key(account: PayoutAccount) -> "str | None":
    """A single comparable string for 'where does this account's money
    actually go' — bank account wins when present (it's the harder-to-fake
    identity: a real bank requires real KYC), falling back to the Stripe
    Connect account id. None if neither is on file yet."""
    if account.account_number and account.bank_code:
        return f"bank:{account.bank_code}:{account.account_number}"
    if account.stripe_account_id:
        return f"stripe:{account.stripe_account_id}"
    return None


def _user_summary(user: "User | None") -> dict:
    if not user:
        return {"id": None, "name": None, "email": None}
    return {"id": user.id, "name": user.name, "email": user.email}


@router.get("/review")
async def get_fraud_review(
    current_user: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Everything this file can currently detect, in one response — see
    this module's own docstring for what each section means and why it's
    a review surface, not an auto-block list."""

    users_by_id = {u.id: u for u in db.query(User).all()}
    payout_accounts = db.query(PayoutAccount).all()
    dest_by_user_id = {}
    for acct in payout_accounts:
        key = _payout_destination_key(acct)
        if key:
            dest_by_user_id[acct.user_id] = key

    # --- 1. Self-referral payout matches ---
    self_referral_matches = []
    for ref in db.query(Referral).filter(Referral.via_staff_pool.is_(False)).all():
        referrer_dest = dest_by_user_id.get(ref.referrer_id)
        referred_dest = dest_by_user_id.get(ref.referred_user_id)
        if referrer_dest and referred_dest and referrer_dest == referred_dest:
            self_referral_matches.append({
                "referral_id": ref.id,
                "referrer": _user_summary(users_by_id.get(ref.referrer_id)),
                "referred": _user_summary(users_by_id.get(ref.referred_user_id)),
                "shared_destination": referrer_dest,
                "referred_at": ref.created_at.isoformat() if ref.created_at else None,
            })

    # --- 2. Payout destination collisions (any users, not just referral pairs) ---
    users_by_dest: dict = {}
    for user_id, dest in dest_by_user_id.items():
        users_by_dest.setdefault(dest, []).append(user_id)

    payout_collisions = []
    for dest, user_ids in users_by_dest.items():
        if len(user_ids) > 1:
            payout_collisions.append({
                "destination": dest,
                "users": [_user_summary(users_by_id.get(uid)) for uid in user_ids],
            })
    payout_collisions.sort(key=lambda c: len(c["users"]), reverse=True)

    # --- 3. Email pattern collisions ---
    users_by_normalized_email: dict = {}
    for user in users_by_id.values():
        norm = normalize_email(user.email)
        users_by_normalized_email.setdefault(norm, []).append(user.id)

    email_pattern_groups = []
    for norm, user_ids in users_by_normalized_email.items():
        if len(user_ids) > 1:
            email_pattern_groups.append({
                "normalized_email": norm,
                "users": [_user_summary(users_by_id.get(uid)) for uid in user_ids],
            })
    email_pattern_groups.sort(key=lambda g: len(g["users"]), reverse=True)

    return {
        "self_referral_matches": self_referral_matches,
        "payout_collisions": payout_collisions,
        "email_pattern_groups": email_pattern_groups,
        "summary": {
            "self_referral_matches": len(self_referral_matches),
            "payout_collisions": len(payout_collisions),
            "email_pattern_groups": len(email_pattern_groups),
        },
    }
