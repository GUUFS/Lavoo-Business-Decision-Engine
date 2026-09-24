
"""
Payout service for handling commission payouts via Stripe and Flutterwave
"""
import os
import stripe
import requests
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import logging
import json

from sqlalchemy import func
from sqlalchemy.orm import Session
from database.pg_models import (
    User, Commission, Payout, PayoutAccount, 
    CommissionSummary, NotificationType
)
from api.services.notification_service import NotificationService
from fastapi import BackgroundTasks
from emailing import email_service

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Flutterwave config (using NEXT_PUBLIC_ prefix to match .env)
FLUTTERWAVE_SECRET_KEY = os.getenv("NEXT_PUBLIC_FLUTTERWAVE_SECRET_KEY")
FLUTTERWAVE_BASE_URL = "https://api.flutterwave.com/v3"


class PayoutService:
    """
    Handles payouts to users via Stripe Connect or Flutterwave Transfers
    """
    
    MIN_PAYOUT_AMOUNT = Decimal("5.00")  # Minimum $10 for payout

    @staticmethod
    def _send_payout_success_email(user_id: int, amount, currency: str, payout_id: int, processed_at) -> None:
        """
        Adapter for the payout-completed notification. Every payout path used
        to queue `email_service.send_payout_success_email`, a function that
        was never defined anywhere — evaluating that attribute raised
        AttributeError inside the completion functions *before* their
        db.commit(), so a payout that genuinely succeeded (money already
        moved) could never be recorded as completed. Opens its own session
        because it runs as a background task, after the request's session
        has closed.
        """
        try:
            from database.pg_connections import SessionLocal
            with SessionLocal() as s:
                user = s.query(User).filter(User.id == user_id).first()
                payout = s.query(Payout).filter(Payout.id == payout_id).first()
                if not user or not user.email:
                    return
                email_service.email_service.send_payout_processed(
                    user_email=user.email,
                    name=user.name or "there",
                    amount=float(amount),
                    currency=currency,
                    payment_method=(payout.payment_method if payout else None) or "bank transfer",
                    transaction_id=str(payout.provider_payout_id if payout and payout.provider_payout_id else payout_id),
                    processing_date=(processed_at or datetime.now(timezone.utc)).strftime("%B %d, %Y"),
                )
        except Exception as e:
            logger.error(f"Could not send payout success email for payout {payout_id}: {e}")
    
    @staticmethod
    def create_payout_request(user_id: int, amount: Decimal, payment_method: str,  # 'stripe' or 'flutterwave'   
        db: Session) -> Payout:
        """
        Create a payout request
        
        Args:
            user_id: User requesting payout
            amount: Amount to payout
            payment_method: 'stripe' or 'flutterwave'
            db: Database session
        
        Returns:
            Payout object
        """
        # Validate user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check available balance
        available = db.query(
            func.sum(Commission.amount)
        ).filter(
            Commission.user_id == user_id,
            Commission.status == 'approved',
            Commission.payout_id.is_(None)
        ).scalar() or Decimal("0.00")
        
        if available < amount:
            raise ValueError(
                f"Insufficient balance. Available: ${available}, Requested: ${amount}"
            )
        
        if amount < PayoutService.MIN_PAYOUT_AMOUNT:
            raise ValueError(
                f"Minimum payout amount is ${PayoutService.MIN_PAYOUT_AMOUNT}"
            )
        
        # Check payout account exists
        payout_account = db.query(PayoutAccount).filter(
            PayoutAccount.user_id == user_id
        ).first()
        
        if not payout_account:
            raise ValueError("No payout account configured. Please set up your payout method.")
        
        # Validate payment method
        if payment_method == 'stripe':
            if not payout_account.stripe_account_id:
                raise ValueError("Stripe account not connected")
        elif payment_method == 'flutterwave':
            if not payout_account.bank_name or not payout_account.account_number:
                raise ValueError("Bank details not configured")
        else:
            raise ValueError(f"Invalid payment method: {payment_method}")
        
        # Create payout record
        payout = Payout(
            user_id=user_id,
            amount=amount,
            currency='USD',  # Default to USD
            payment_method=payment_method,
            status='pending',
            recipient_email=user.email,
            recipient_name=user.name,
            requested_at=datetime.now(timezone.utc)
        )
        
        db.add(payout)
        db.flush()
        
        # Link commissions to this payout
        commissions = db.query(Commission).filter(
            Commission.user_id == user_id,
            Commission.status == 'approved',
            Commission.payout_id.is_(None)
        ).order_by(Commission.created_at).all()
        
        total_linked = Decimal("0.00")
        for commission in commissions:
            if total_linked + commission.amount <= amount:
                commission.payout_id = payout.id
                total_linked += commission.amount
            if total_linked >= amount:
                break
        
        db.commit()
        db.refresh(payout)
        
        logger.info(f"Payout request created: {payout.id} for user {user_id}")
        return payout
    

    @staticmethod
    def process_stripe_payout(payout: Payout, background_tasks: BackgroundTasks, db: Session) -> Dict[str, Any]:
        """
        Process payout via Stripe Connect
        
        NOTE: This requires Stripe Connect to be set up.
        For testing, you can use Stripe's test mode.
        """
        try:
            payout_account = db.query(PayoutAccount).filter(
                PayoutAccount.user_id == payout.user_id
            ).first()
            
            if not payout_account or not payout_account.stripe_account_id:
                raise ValueError("Stripe account not configured")
            
            # Convert amount to cents
            amount_cents = int(payout.amount * 100)
            
            # Create Stripe transfer
            # Note: This requires the connected account to be set up
            transfer = stripe.Transfer.create(
                amount=amount_cents,
                currency=payout.currency.lower(),
                destination=payout_account.stripe_account_id,
                description=f"Commission payout for {payout.recipient_name}",
                metadata={
                    "stripe_connect_payout_id": str(payout.id),
                    "user_id": str(payout.user_id)
                }
            )
            # Create Stripe payout
            payment = stripe.Payout.create(
                        amount=amount_cents,
                        currency=payout.currency.lower(),
                        stripe_account=payout_account.stripe_account_id,
                        metadata={
                            "stripe_connect_payout_id": str(payout.id),
                            "user_id": str(payout.user_id)
                        }
            )

            # Update payout record to completed immediately (synchronous flow)
            payout.status = 'completed'
            payout.provider_transfer_id = transfer.id
            payout.provider_payout_id = payment.id
            payout.provider_response = json.dumps({
                                        "transfer": transfer.to_dict(),
                                        "payout": payment.to_dict(),
            })
            payout.processed_at = datetime.now(timezone.utc)
            payout.completed_at = datetime.now(timezone.utc)

            # Update commissions linked to this payout
            commissions = db.query(Commission).filter(
                Commission.payout_id == payout.id
            ).all()
            
            for commission in commissions:
                commission.status = 'paid'
                commission.paid_at = datetime.now(timezone.utc)
            
            # Update user's commission summary
            PayoutService._update_summary_on_payout(payout, db)

            db.flush()

            logger.info(
                f"Stripe payout completed synchronously | payout={payout.id} "
                f"transfer={transfer.id} payment={payment.id}"
            )
            
            background_tasks.add_task(
                PayoutService._send_payout_success_email,
                payout.user_id,
                payout.amount,
                payout.currency,
                payout.id,
                payout.processed_at
            )
            
            return {
                "status": "success",
                "payout_id": payout.id,
                "stripe_transfer_id": transfer.id,
                "stripe_payout_id": payment.id,
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe payout initiation failed: {str(e)}")
            payout.status = "failed"
            payout.failure_reason = str(e)
            db.flush()
            raise

        
    

    @staticmethod
    def process_flutterwave_payout(payout: Payout, db: Session, manage_transaction: bool = True) -> Dict[str, Any]:
        """
        Process payout via Flutterwave Transfer API.

        manage_transaction=True (the default, used by every standalone
        admin/manual payout call site) means this function owns its own
        commit/rollback boundary — the caller queried `payout` and nothing
        else of value is pending on `db`.

        manage_transaction=False is for a caller (commission_service.py's
        immediate-payout path) that already has OTHER uncommitted work of
        its own on this same shared session — a freshly-created Subscriptions
        and Commission row, in that case — which a failed *optional* payout
        attempt must never destroy. In that mode this function only
        db.flush()es its own changes into the caller's still-open
        transaction instead of committing or rolling back, so the caller
        decides the fate of everything together, atomically.
        """
        logger.info(
            f"[FLW payout] START | payout={payout.id} user={payout.user_id} "
            f"amount={payout.amount} {payout.currency}"
            + (f" (converted from {payout.original_amount} {payout.original_currency} @ rate {payout.fx_rate})"
               if payout.original_currency else "")
        )
        try:
            payout_account = db.query(PayoutAccount).filter(
                PayoutAccount.user_id == payout.user_id
            ).first()

            if not payout_account:
                raise ValueError("Payout account not configured")

            if not payout_account.bank_name or not payout_account.account_number:
                raise ValueError("Bank details not configured")

            logger.info(
                f"[FLW payout] destination | payout={payout.id} bank={payout_account.bank_name} "
                f"bank_code={payout_account.bank_code} account=***{payout_account.account_number[-4:]} "
                f"name={payout_account.account_name}"
            )

            # Prepare transfer payload. No debit_currency override: Flutterwave
            # debits the balance matching the transfer `currency` by default,
            # which is correct here since payout.currency is always set to
            # NGN for a Flutterwave bank transfer (commission_service.py
            # converts any non-NGN commission to NGN before creating this
            # Payout row). A hardcoded "debit_currency": "USD" here
            # previously tried to debit a USD balance Lavoo doesn't actually
            # hold in Flutterwave (dollar/pound revenue arrives via Stripe,
            # not Flutterwave) for what should just be a plain NGN transfer
            # from Lavoo's existing, well-funded NGN balance — the direct
            # cause of a reported payout never arriving.
            payload = {
                "account_bank": payout_account.bank_code or payout_account.bank_name,
                "account_number": payout_account.account_number,
                "amount": float(payout.amount),
                "currency": payout.currency,
                "narration": f"Lavoo Builder Bonus payout #{payout.id}",
                "reference": f"PAYOUT-{payout.id}-{int(datetime.now(timezone.utc).timestamp())}",
                "callback_url": f"{os.getenv('BASE_URL')}/api/payments/flutterwave/callback",
                "beneficiary_name": payout_account.account_name or payout.recipient_name
            }
            
            headers = {
                "Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            logger.info(
                f"[FLW payout] request | payout={payout.id} POST {FLUTTERWAVE_BASE_URL}/transfers "
                f"account_bank={payload['account_bank']} amount={payload['amount']} currency={payload['currency']} "
                f"reference={payload['reference']}"
            )

            # Make transfer request
            response = requests.post(
                f"{FLUTTERWAVE_BASE_URL}/transfers",
                json=payload,
                headers=headers
            )

            logger.info(
                f"[FLW payout] response | payout={payout.id} status={response.status_code} "
                f"body={response.text[:500]}"
            )

            if response.status_code != 200:
                raise ValueError(f"Flutterwave API error: {response.text}")

            data = response.json()

            if data.get("status") != "success":
                raise ValueError(f"Transfer failed: {data.get('message')}")

            transfer_data = data.get("data", {})

            # Update payout record
            payout.status = 'processing'  # Flutterwave transfers are async
            payout.provider_payout_id = str(transfer_data.get("id"))
            payout.provider_response = json.dumps(data)
            payout.processed_at = datetime.now(timezone.utc)

            if manage_transaction:
                db.commit()
                db.refresh(payout)
            else:
                db.flush()

            logger.info(
                f"[FLW payout] SUCCESS | payout={payout.id} transfer_id={transfer_data.get('id')} "
                f"amount={payout.amount} {payout.currency} status={payout.status} — "
                f"Flutterwave transfers are async, watch for the /flutterwave/callback webhook "
                f"to confirm final completion vs. failure"
            )

            return {
                "status": "processing",
                "payout_id": payout.id,
                "transfer_id": transfer_data.get("id"),
                "amount": float(payout.amount),
                "message": "Payout is being processed"
            }

        except Exception as e:
            # Broadened from requests.RequestException only: a non-200 or a
            # non-"success" Flutterwave response (by far the most likely
            # real-world failure — bad account details, insufficient
            # balance, unsupported bank, or the server's outbound IP not
            # being whitelisted in the Flutterwave dashboard) raises plain
            # ValueError above, which this previously did NOT catch at all —
            # the payout row was left stuck at status='pending' forever with
            # no failure_reason recorded, indistinguishable from "still in
            # progress."
            #
            # The db.rollback() an earlier fix added here was itself broken
            # two ways: (1) rolling back BEFORE mutating payout.status/
            # failure_reason detaches the object from the session, so the
            # mutation that follows doesn't actually get saved by the
            # db.commit() after it — SQLAlchemy raises "Instance ... is not
            # persistent within this Session" the moment it tries, which is
            # exactly the 400 confirm-subscription surfaced to the frontend.
            # (2) when called with manage_transaction=False (from
            # commission_service.py's immediate-payout attempt, sharing a
            # session with an already-pending Subscriptions + Commission
            # row from the SAME request), that rollback silently destroyed
            # both of those too — an optional, best-effort payout attempt
            # failing should never take an already-successful subscription
            # payment down with it.
            payout.status = 'failed'
            payout.failure_reason = str(e)
            if manage_transaction:
                db.commit()
                db.refresh(payout)
            else:
                db.flush()

            logger.error(f"[FLW payout] FAILED | payout={payout.id} error={e}", exc_info=True)
            raise ValueError(f"Payout failed: {str(e)}")


    @staticmethod
    def complete_flutterwave_payout(
        payout_id: int, background_tasks: BackgroundTasks, transfer_status: str, db: Session,
        settled_amount: float | None = None, fee: float | None = None,
        failure_reason: str | None = None,
    ) -> None:
        """
        Complete Flutterwave payout after webhook confirmation.

        settled_amount/fee come straight from Flutterwave's webhook payload
        (see flutterwave.py's flutterwave_payout_callback) — recorded as-is
        so a gap between what was requested (payout.amount) and what
        actually arrived is visible after the fact, instead of silently
        lost the way it previously was (a referrer reported receiving
        119.73 NGN for a requested 120 NGN payout with nothing on file to
        explain it).
        """
        payout = db.query(Payout).filter(Payout.id == payout_id).first()

        if not payout:
            logger.error(f"Payout {payout_id} not found")
            return

        # The same outcome can now arrive twice (Flutterwave's webhook AND the
        # polling reconciler below) — counting a success twice would add the
        # amount to commission_summaries.paid_commissions twice.
        if transfer_status == "successful" and payout.status == "completed":
            logger.info(f"Flutterwave payout {payout_id} already completed — ignoring duplicate success")
            return

        if transfer_status == "successful":
            payout.status = 'completed'
            payout.completed_at = datetime.now(timezone.utc)
            if settled_amount is not None:
                payout.provider_settled_amount = Decimal(str(settled_amount))
            if fee is not None:
                payout.provider_fee = Decimal(str(fee))
            if settled_amount is not None and Decimal(str(settled_amount)) != payout.amount:
                logger.warning(
                    f"[FLW payout] requested={payout.amount} {payout.currency} but Flutterwave "
                    f"settled={settled_amount} (fee={fee}) for payout {payout_id} — dashboard/email "
                    f"still show the requested amount; provider_settled_amount now has the real figure"
                )

            payout.failure_reason = None

            # A payout that failed and was later retried successfully has no
            # commissions linked anymore (failure detached them). Re-link the
            # ones it was covering — otherwise the referrer would be paid by
            # this transfer AND their still-'pending' commission paid again.
            commissions = db.query(Commission).filter(
                Commission.payout_id == payout.id
            ).all()
            if not commissions:
                commissions = PayoutService._relink_commissions_from_history(payout, db)
                if not commissions:
                    PayoutService._queue_admin_alert(
                        background_tasks,
                        subject=f"⚠️ Flutterwave payout #{payout_id} succeeded but has no commission to settle",
                        body=(
                            f"Flutterwave reports payout #{payout_id} ({payout.amount} {payout.currency}, "
                            f"user {payout.user_id}) as SUCCESSFUL, but no pending commission is linked to it "
                            f"(already settled another way, or this was a duplicate transfer). "
                            f"Money has left the Flutterwave wallet — please check this one manually."
                        ),
                    )

            for commission in commissions:
                commission.status = 'paid'
                commission.paid_at = datetime.now(timezone.utc)
            db.flush()  # session has autoflush off; the summary query below reads the DB

            # Update summary
            PayoutService._update_summary_on_payout(payout, db)
            background_tasks.add_task(
                PayoutService._send_payout_success_email,
                payout.user_id,
                payout.amount,
                payout.currency,
                payout.id,
                payout.processed_at
            )
        elif transfer_status == "failed":
            # Delegate to reverse_payout rather than duplicating its revert
            # logic here: this branch used to set status/failure_reason and
            # revert commissions to 'pending' inline, but never touched
            # commission_summaries — the pre-aggregated table the Earnings
            # page's monthly totals actually read from. That left a paid
            # commission's amount stuck counted as "paid" in the summary
            # forever after the payout that was supposed to fund it failed,
            # with no code path that ever corrected it back to "pending".
            PayoutService.reverse_payout(payout_id, failure_reason, db)
            logger.info(f"Flutterwave payout {payout_id} marked as {transfer_status}")
            return

        db.commit()
        logger.info(f"Flutterwave payout {payout_id} marked as {transfer_status}")
    

    @staticmethod
    def _queue_admin_alert(background_tasks: BackgroundTasks, subject: str, body: str) -> None:
        admin_email = os.getenv("ADMIN_ALERT_EMAIL", os.getenv("SUPPORT_EMAIL", "support@lavoo.io"))
        background_tasks.add_task(
            email_service.email_service._send_email,
            to_email=admin_email,
            to_name="Lavoo Admin",
            subject=subject,
            html_content=f"<p>{body}</p>",
            text_content=body,
        )

    # The linkage is kept inside the payout's existing provider_response JSON
    # (under a "lavoo" key) rather than a new column: a new column on this hot
    # table would make every Payout query fail on a deploy where the migration
    # hadn't landed yet. provider_response is diagnostic-only and its one
    # external reader (admin/revenue.py) just parses and returns the JSON.
    @staticmethod
    def _response_blob(payout: Payout) -> Dict[str, Any]:
        try:
            blob = json.loads(payout.provider_response or "{}")
        except (TypeError, ValueError):
            blob = {"raw": payout.provider_response}
        return blob if isinstance(blob, dict) else {"raw": blob}

    @staticmethod
    def _remember_commissions(payout: Payout, commission_ids: list) -> None:
        blob = PayoutService._response_blob(payout)
        blob.setdefault("lavoo", {})["commission_ids"] = [int(i) for i in commission_ids]
        payout.provider_response = json.dumps(blob)

    @staticmethod
    def _remembered_commission_ids(payout: Payout) -> list:
        ids = (PayoutService._response_blob(payout).get("lavoo") or {}).get("commission_ids") or []
        return [int(i) for i in ids]

    @staticmethod
    def _record_provider_attempt(payout: Payout, attempt: Dict[str, Any]) -> None:
        """Store the transfer attempt that decided this payout, keeping our linkage."""
        keep = PayoutService._response_blob(payout).get("lavoo")
        blob: Dict[str, Any] = {"status": "success", "data": attempt}
        if keep:
            blob["lavoo"] = keep
        payout.provider_response = json.dumps(blob)

    @staticmethod
    def _relink_commissions_from_history(payout: Payout, db: Session) -> list:
        """
        Re-attach the commissions a failed payout remembered (see
        reverse_payout), but only those still waiting: pending and unlinked. A
        commission that was paid some other way in the meantime is left alone
        so it can't be settled twice.
        """
        ids = PayoutService._remembered_commission_ids(payout)
        if not ids:
            return []
        commissions = db.query(Commission).filter(
            Commission.id.in_(ids),
            Commission.payout_id.is_(None),
            Commission.status == 'pending',
        ).all()
        for commission in commissions:
            commission.payout_id = payout.id
        db.flush()
        return commissions

    @staticmethod
    def _flw_get(path: str) -> Optional[Dict[str, Any]]:
        resp = requests.get(
            f"{FLUTTERWAVE_BASE_URL}{path}",
            headers={"Authorization": f"Bearer {FLUTTERWAVE_SECRET_KEY}"},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning(f"[FLW reconcile] GET {path} -> {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json()

    @staticmethod
    def _latest_flutterwave_attempt(transfer_id: str) -> Optional[Dict[str, Any]]:
        """
        The freshest view of a transfer. Retrying a failed transfer from
        Flutterwave's dashboard doesn't change the original transfer (it stays
        FAILED forever) — it creates a new attempt listed under
        GET /transfers/:id/retries. So the truth is the latest retry if there
        is one, otherwise the original itself.
        """
        retries = (PayoutService._flw_get(f"/transfers/{transfer_id}/retries") or {}).get("data") or []
        attempts = [r for r in retries if isinstance(r, dict) and (r.get("id") or r.get("status"))]
        if attempts:
            latest = sorted(
                attempts, key=lambda r: (str(r.get("created_at") or ""), int(r.get("id") or 0))
            )[-1]
            if not latest.get("status") and latest.get("id"):
                latest = (PayoutService._flw_get(f"/transfers/{latest['id']}") or {}).get("data") or latest
            return latest
        return (PayoutService._flw_get(f"/transfers/{transfer_id}") or {}).get("data")

    @staticmethod
    def reconcile_flutterwave_payouts(
        db: Session, background_tasks: BackgroundTasks, min_age_seconds: int = 90,
        retry_lookback_days: int = 14, processing_lookback_days: int = 30,
        payout_ids: Optional[list] = None,
    ) -> Dict[str, int]:
        """
        Ask Flutterwave directly for the real outcome of our transfers, instead
        of relying on its webhook alone. Covers two cases:

        1. Payouts still 'processing': a transfer being *accepted* says nothing
           about whether it later succeeds (e.g. it can still fail with
           "Insufficient funds"). When the webhook doesn't reach us, the payout
           and its 'auto_settled' commission sat there forever (payouts
           #29/#30/#31) while Flutterwave's dashboard showed FAILED.
        2. Payouts we already marked 'failed': when someone clicks "Retry
           transfer" in Flutterwave's dashboard after funding the wallet, the
           retry succeeds there but nothing tells us. This follows retries so
           the payout completes and its commission is settled, or shows as
           'processing' again while the retry is in flight.

        Emails/alerts are queued onto `background_tasks`; the caller runs them.
        """
        now = datetime.now(timezone.utc)
        counts = {"checked": 0, "completed": 0, "failed": 0, "retrying": 0, "still_pending": 0, "errors": 0}

        processing = db.query(Payout).filter(
            Payout.payment_method == 'flutterwave',
            Payout.status == 'processing',
            Payout.provider_payout_id.isnot(None),
            Payout.processed_at <= now - timedelta(seconds=min_age_seconds),
            # Old sandbox-era payouts (e.g. December test transfers) sit at
            # 'processing' forever and can't be looked up on the live API —
            # polling them every cycle would only ever error.
            Payout.processed_at >= now - timedelta(days=processing_lookback_days),
        )
        failed_recent = db.query(Payout).filter(
            Payout.payment_method == 'flutterwave',
            Payout.status == 'failed',
            Payout.provider_payout_id.isnot(None),
            Payout.created_at >= now - timedelta(days=retry_lookback_days),
        )
        if payout_ids is not None:
            processing = processing.filter(Payout.id.in_(payout_ids))
            failed_recent = failed_recent.filter(Payout.id.in_(payout_ids))
        processing = processing.all()
        failed_recent = failed_recent.limit(50).all()

        for payout in [*processing, *failed_recent]:
            counts["checked"] += 1
            payout_id = payout.id
            was_failed = payout.status == 'failed'
            try:
                attempt = PayoutService._latest_flutterwave_attempt(payout.provider_payout_id)
                if not attempt:
                    counts["errors"] += 1
                    continue
                status = str(attempt.get("status") or "").upper()

                if status == "SUCCESSFUL":
                    PayoutService._record_provider_attempt(payout, attempt)
                    PayoutService.complete_flutterwave_payout(
                        payout_id, background_tasks, "successful", db,
                        settled_amount=attempt.get("amount"), fee=attempt.get("fee"),
                    )
                    counts["completed"] += 1
                    logger.info(
                        f"[FLW reconcile] payout={payout_id} -> completed"
                        + (f" (via retry transfer {attempt.get('id')})" if was_failed else "")
                    )
                elif status == "FAILED":
                    if was_failed:
                        continue  # nothing new — still the failure we already recorded
                    reason = attempt.get("complete_message") or "Transfer failed at Flutterwave"
                    PayoutService.complete_flutterwave_payout(
                        payout_id, background_tasks, "failed", db, failure_reason=reason,
                    )
                    counts["failed"] += 1
                    logger.warning(f"[FLW reconcile] payout={payout_id} -> failed: {reason}")
                    PayoutService._queue_admin_alert(
                        background_tasks,
                        subject=f"⚠️ Flutterwave payout #{payout_id} failed — {reason}",
                        body=(
                            f"Flutterwave reports transfer {payout.provider_payout_id} (payout #{payout_id}, "
                            f"{payout.amount} {payout.currency}, user {payout.user_id}) as FAILED: {reason}. "
                            f"The commission is back to pending. Once the cause is fixed (e.g. the Flutterwave "
                            f"NGN wallet is funded) use 'Retry transfer' on Flutterwave's dashboard — Lavoo will "
                            f"pick the retry up automatically."
                        ),
                    )
                else:
                    # NEW / PENDING / QUEUED — the transfer (or its retry) is still in flight.
                    if was_failed:
                        payout.status = 'processing'
                        payout.failure_reason = "Retry in progress at Flutterwave"
                        db.commit()
                        counts["retrying"] += 1
                        logger.info(f"[FLW reconcile] payout={payout_id} retry in flight -> processing")
                    else:
                        counts["still_pending"] += 1
            except Exception as e:
                counts["errors"] += 1
                db.rollback()
                logger.error(f"[FLW reconcile] payout={payout_id} error: {e}", exc_info=True)

        return counts

    @staticmethod
    def complete_stripe_payout(payout_id: int, background_tasks: BackgroundTasks, status: str, db: Session) -> None:
        """
        Complete Stripe payout (simulated or via potential webhook)
        """
        payout = db.query(Payout).filter(Payout.id == payout_id).first()
        
        if not payout:
            logger.error(f"Payout {payout_id} not found")
            return
        
        if status == "paid":
            payout.status = 'completed'
            payout.completed_at = datetime.now(timezone.utc)
            
            # Update commissions
            commissions = db.query(Commission).filter(
                Commission.payout_id == payout.id
            ).all()
            
            for commission in commissions:
                commission.status = 'paid'
                commission.paid_at = datetime.now(timezone.utc)
            
            # Update summary
            PayoutService._update_summary_on_payout(payout, db)
            
            background_tasks.add_task(
                PayoutService._send_payout_success_email,
                payout.user_id,
                payout.amount,
                payout.currency,
                payout.id,
                payout.processed_at
            )
        elif status == "failed":
            payout.status = 'failed'
            payout.failed_at = datetime.now(timezone.utc)
            
            # Revert commissions
            commissions = db.query(Commission).filter(
                Commission.payout_id == payout.id
            ).all()
            
            for commission in commissions:
                commission.payout_id = None
                commission.status = 'approved' # Keep as approved so they can be re-payout
        
        db.commit()
        logger.info(f"Stripe payout {payout_id} marked as {status}")
    

    @staticmethod
    def _update_summary_on_payout(payout: Payout, db: Session) -> None:
        """
        Update commission summary when payout is completed
        """
        now = datetime.now(timezone.utc)
        
        # Get all months affected by the commissions in this payout
        commissions = db.query(Commission).filter(
            Commission.payout_id == payout.id
        ).all()
        
        # Group by month
        monthly_amounts = {}
        for commission in commissions:
            year = commission.created_at.year
            month = commission.created_at.month
            key = (year, month)
            
            if key not in monthly_amounts:
                monthly_amounts[key] = Decimal("0.00")
            monthly_amounts[key] += commission.amount
        
        # Update each affected month
        for (year, month), amount in monthly_amounts.items():
            summary = db.query(CommissionSummary).filter(
                CommissionSummary.user_id == payout.user_id,
                CommissionSummary.year == year,
                CommissionSummary.month == month
            ).first()
            
            if summary:
                summary.paid_commissions += amount
                summary.pending_commissions -= amount
                summary.updated_at = now

    @staticmethod
    def reverse_payout(payout_id: int, failure_reason: str, db: Session) -> None:
        """
        Handle a payout that was previously marked as completed but has now failed.
        """
        payout = db.query(Payout).filter(Payout.id == payout_id).first()
        if not payout:
            return

        if payout.status == "failed":
            return

        payout.status = "failed"
        payout.failure_reason = failure_reason or "Funds returned/Reversed"

        commissions = db.query(Commission).filter(
            Commission.payout_id == payout.id
        ).all()

        # Remember which commissions this payout was covering before they're
        # detached, so a later successful RETRY of this same transfer (from
        # Flutterwave's dashboard) can settle exactly these instead of being
        # paid out again. Only overwrite when there is something to record: a
        # payout revived for a retry and failing again has nothing linked
        # anymore, and must not erase what it remembered the first time.
        if commissions:
            PayoutService._remember_commissions(payout, [c.id for c in commissions])

        for commission in commissions:
            commission.payout_id = None
            commission.status = 'pending'
            commission.paid_at = None

        PayoutService._reverse_summary_on_payout(payout, db)
        db.commit()

    @staticmethod
    def _reverse_summary_on_payout(payout: Payout, db: Session) -> None:
        now = datetime.now(timezone.utc)
        commissions = db.query(Commission).filter(
            Commission.payout_id == payout.id
        ).all()

        monthly_amounts = {}
        for commission in commissions:
            year = commission.created_at.year
            month = commission.created_at.month
            key = (year, month)
            if key not in monthly_amounts:
                monthly_amounts[key] = Decimal("0.00")
            monthly_amounts[key] += commission.amount

        for (year, month), amount in monthly_amounts.items():
            summary = db.query(CommissionSummary).filter(
                CommissionSummary.user_id == payout.user_id,
                CommissionSummary.year == year,
                CommissionSummary.month == month
            ).first()
            if summary:
                summary.paid_commissions -= amount
                summary.pending_commissions += amount
                summary.updated_at = now