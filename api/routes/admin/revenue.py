
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, case
from datetime import datetime, timezone
from decimal import Decimal

from database.pg_connections import get_db
from database.pg_models import User, Subscriptions, Commission, Payout, ApproveCommissionsRequest
from api.routes.auth.login import get_current_user
from subscriptions.commission_service import CommissionService
from subscriptions.payout_service import PayoutService
import json

router = APIRouter(prefix="/control/revenue", tags=["admin-revenue"])


def verify_admin(current_user):
    """Verify user is admin"""
    if isinstance(current_user, dict):
        if "user" in current_user:
            user_data = current_user["user"]
            if isinstance(user_data, dict):
                is_admin = user_data.get("is_admin", False)
            elif hasattr(user_data, 'is_admin'):
                is_admin = user_data.is_admin
            else:
                is_admin = False
        else:
            is_admin = current_user.get("is_admin", False)
    else:
        is_admin = current_user.is_admin if hasattr(current_user, 'is_admin') else False
    
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/stats")
async def get_revenue_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Overall revenue statistics, broken out per currency.

    Subscriptions and Payouts are both genuinely multi-currency (NGN/USD/
    GBP — see api/routes/user/stats.py's own comments on this). The
    previous version summed every currency into one number labelled
    "currency": "USD", which silently blended incompatible currencies into
    a meaningless total (e.g. a NGN payout and a USD subscription added
    together). This groups by the row's actual currency instead.
    """
    verify_admin(current_user)

    try:
        now = datetime.now(timezone.utc)
        current_month_start = datetime(now.year, now.month, 1)
        last_month = now.month - 1 if now.month > 1 else 12
        last_year = now.year if now.month > 1 else now.year - 1
        last_month_start = datetime(last_year, last_month, 1)

        def sum_by_currency(amount_col, currency_col, *filters):
            rows = db.query(
                currency_col.label('currency'),
                func.coalesce(func.sum(amount_col), 0).label('total')
            ).filter(*filters).group_by(currency_col).all()
            return {(row.currency or 'USD'): float(row.total) for row in rows}

        monthly_by_ccy = sum_by_currency(
            Subscriptions.amount, Subscriptions.currency,
            Subscriptions.status.in_(['active', 'completed']),
            Subscriptions.created_at >= current_month_start,
        )
        last_month_by_ccy = sum_by_currency(
            Subscriptions.amount, Subscriptions.currency,
            Subscriptions.status.in_(['active', 'completed']),
            Subscriptions.created_at >= last_month_start,
            Subscriptions.created_at < current_month_start,
        )
        total_subscription_by_ccy = sum_by_currency(
            Subscriptions.amount, Subscriptions.currency,
            Subscriptions.status.in_(['active', 'completed']),
        )
        commissions_paid_by_ccy = sum_by_currency(
            Payout.amount, Payout.currency,
            Payout.status == 'completed',
        )
        refunds_by_ccy = sum_by_currency(
            Subscriptions.amount, Subscriptions.currency,
            Subscriptions.status == 'refunded',
        )

        currencies = sorted(
            set(monthly_by_ccy) | set(total_subscription_by_ccy)
            | set(commissions_paid_by_ccy) | set(refunds_by_ccy)
        )

        by_currency = {}
        for ccy in currencies:
            this_month = monthly_by_ccy.get(ccy, 0.0)
            prior_month = last_month_by_ccy.get(ccy, 0.0)
            if prior_month > 0:
                growth = ((this_month - prior_month) / prior_month) * 100
            else:
                growth = 100.0 if this_month > 0 else 0.0
            by_currency[ccy] = {
                "monthly_revenue": this_month,
                "total_subscription_revenue": total_subscription_by_ccy.get(ccy, 0.0),
                "referral_commissions_paid": commissions_paid_by_ccy.get(ccy, 0.0),
                "refunds": refunds_by_ccy.get(ccy, 0.0),
                "growth_rate": round(growth, 1),
            }

        return {"by_currency": by_currency, "currencies": currencies}

    except Exception as e:
        print(f"Error in revenue stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions")
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all subscription transactions with user details"""
    verify_admin(current_user)
    
    try:
        transactions = db.query(
            Subscriptions.id,
            Subscriptions.transaction_id,
            Subscriptions.user_id,
            User.name.label('user_name'),
            User.email.label('user_email'),
            Subscriptions.subscription_plan,
            Subscriptions.amount,
            Subscriptions.currency,
            Subscriptions.status,
            Subscriptions.payment_provider,
            Subscriptions.created_at
        ).join(
            User, Subscriptions.user_id == User.id
        ).order_by(
            Subscriptions.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        total = db.query(func.count(Subscriptions.id)).scalar()
        
        result = []
        for txn in transactions:
            result.append({
                "id": f"TXN-{txn.id}",
                "transaction_id": txn.transaction_id,
                "user": txn.user_name,
                "user_email": txn.user_email,
                "plan": txn.subscription_plan,
                "amount": float(txn.amount),
                "currency": txn.currency,
                "type": "subscription",
                "status": txn.status,
                "method": txn.payment_provider,
                "date": txn.created_at.strftime("%Y-%m-%d %H:%M")
            })
        
        return {
            "transactions": result,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        print(f"Error in transactions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/commissions")
async def get_commissions(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get commission data grouped by user with payment methods.

    Commission.status actually has five live values, not three:
    pending, approved (set by CommissionService.approve_commission /
    auto_approve_commissions — see commission_service.py — but never acted
    on by this file's own /commissions/approve/{user_id} below, which only
    ever reads 'pending' rows directly; that gap is real and unresolved,
    flagged rather than silently worked around here), processing, paid,
    and auto_settled (paid automatically at charge time or via immediate
    FX payout, never touched by an admin). The previous version only
    summed pending/processing/paid, so any approved or auto_settled
    commission was invisible in every total below even though it's real
    money already committed or already paid.
    """
    verify_admin(current_user)

    try:
        from database.pg_models import PayoutAccount

        def status_sum(status: str):
            return func.coalesce(
                func.sum(case((Commission.status == status, Commission.amount), else_=0)), 0
            )

        commission_data = db.query(
            Commission.user_id,
            User.name.label('user_name'),
            User.email.label('user_email'),
            func.coalesce(func.sum(Commission.amount), 0).label('total_commissions'),
            status_sum('pending').label('pending_commissions'),
            status_sum('approved').label('approved_commissions'),
            status_sum('processing').label('processing_commissions'),
            status_sum('paid').label('paid_commissions'),
            status_sum('auto_settled').label('auto_settled_commissions'),
            func.max(Commission.created_at).label('last_commission_date'),
            func.count(Commission.id).label('commission_count')
        ).join(
            User, Commission.user_id == User.id
        ).group_by(
            Commission.user_id, User.name, User.email
        ).order_by(
            func.max(Commission.created_at).desc()
        ).limit(limit).offset(offset).all()
        
        # Get total unique users with commissions
        total = db.query(
            func.count(func.distinct(Commission.user_id))
        ).scalar()
        
        result = []
        for data in commission_data:
            # Calculate amounts for each status
            pending = float(data.pending_commissions)
            approved = float(data.approved_commissions)
            processing = float(data.processing_commissions)
            paid = float(data.paid_commissions)
            auto_settled = float(data.auto_settled_commissions)

            # Determine overall payout status — ordered so the status needing
            # the most urgent admin attention wins when a user has a mix.
            if pending > 0:
                payout_status = "pending"  # Has pending commissions to approve
            elif processing > 0:
                payout_status = "processing"  # Awaiting payout confirmation
            elif approved > 0:
                # Approved by CommissionService but /commissions/approve
                # below can't act on it yet (see docstring) — surfaced
                # distinctly so this isn't mistaken for "nothing owed."
                payout_status = "approved"
            elif auto_settled > 0:
                payout_status = "auto_settled"  # Already paid, no admin action was needed
            elif paid > 0:
                payout_status = "paid"  # All paid
            else:
                payout_status = "pending"
            
            # Get payout account for this user
            payout_account = db.query(PayoutAccount).filter(
                PayoutAccount.user_id == data.user_id
            ).first()
            
            available_methods = []
            if payout_account:
                if payout_account.stripe_account_id:
                    available_methods.append("stripe")
                if payout_account.bank_name and payout_account.account_number:
                    available_methods.append("flutterwave")
            
            result.append({
                "user_id": data.user_id,
                "user": data.user_name,
                "user_email": data.user_email,
                "total_commissions": float(data.total_commissions),
                "pending_commissions": pending,
                "approved_commissions": approved,
                "processing_commissions": processing,
                "paid_commissions": paid,
                "auto_settled_commissions": auto_settled,
                "payout_status": payout_status,
                "last_commission_date": data.last_commission_date.strftime("%Y-%m-%d %H:%M") if data.last_commission_date else None,
                "commission_count": data.commission_count,
                "available_payment_methods": available_methods,
                "has_payout_account": len(available_methods) > 0
            })
        
        return {
            "commissions": result,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        print(f"Error in commissions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/commissions/approve/{user_id}")
async def approve_user_commissions(
    user_id: int,
    request: ApproveCommissionsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve and pay user commissions.
    
    Flow:
    1. pending → commission awaiting admin approval
    2. processing → admin approved, payout initiated, waiting for provider
    3. paid → payout completed successfully
    
    On failure: commissions stay 'pending', payout marked as 'failed'
    """
    verify_admin(current_user)
    
    try:
        from database.pg_models import PayoutAccount
        
        # Get pending commissions
        pending_commissions = db.query(Commission).filter(
            Commission.user_id == user_id,
            Commission.status == 'pending'
        ).all()
        
        if not pending_commissions:
            return {"status": "info", "message": "No pending commissions to approve", "count": 0}

        total_pending = sum(Decimal(str(c.amount)) for c in pending_commissions)

        # Use requested amount or full pending amount
        payout_amount = Decimal(str(request.amount)) if request.amount is not None else total_pending

        if payout_amount > total_pending:
            raise HTTPException(
                status_code=400, 
                detail=f"Requested ${payout_amount} exceeds available ${total_pending}"
            )

        if payout_amount < Decimal("5.00"):
            raise HTTPException(status_code=400, detail="Minimum payout is $5.00")

        # Check payout account BEFORE making any changes
        payout_account = db.query(PayoutAccount).filter(
            PayoutAccount.user_id == user_id
        ).first()
        
        if not payout_account:
            raise HTTPException(
                status_code=400, 
                detail="User has no payout account configured. Cannot process payout."
            )

        # Check available payment methods
        available_methods = []
        if payout_account.stripe_account_id:
            available_methods.append('stripe')
        if payout_account.bank_name and payout_account.account_number:
            available_methods.append('flutterwave')

        if not available_methods:
            raise HTTPException(
                status_code=400, 
                detail="User has no valid payout method configured (no Stripe account or bank details)."
            )

        # Use admin-selected method or default
        payment_method = request.payment_method or available_methods[0]
        
        if payment_method not in available_methods:
            raise HTTPException(
                status_code=400, 
                detail=f"Payment method '{payment_method}' is not available for this user."
            )

        # Select and potentially split commissions for this payout
        # If payout amount is less than total pending, we need to split commissions
        selected_commissions = []
        amount_to_allocate = payout_amount
        
        for comm in sorted(pending_commissions, key=lambda x: x.created_at):
            if amount_to_allocate <= Decimal("0.0"):
                break
                
            comm_amount = Decimal(str(comm.amount))
            
            if comm_amount <= amount_to_allocate:
                # Use entire commission
                selected_commissions.append(comm)
                amount_to_allocate -= comm_amount
                print(f"[Admin] Using full commission {comm.id}: ${comm_amount}")
            else:
                # Need to split this commission
                paid_portion = amount_to_allocate
                remaining_portion = comm_amount - paid_portion
                
                print(f"[Admin] Splitting commission {comm.id}: ${paid_portion} to pay, ${remaining_portion} remains pending")
                
                # Create a NEW commission for the REMAINING/unpaid portion (stays pending)
                new_pending_commission = Commission(
                    user_id=comm.user_id,
                    referred_user_id=comm.referred_user_id,
                    subscription_id=comm.subscription_id,
                    amount=remaining_portion,  # The portion NOT being paid
                    original_amount=comm.original_amount,
                    currency=comm.currency,
                    commission_rate=comm.commission_rate,
                    status='pending',  # Stays pending for future payouts
                    created_at=comm.created_at,  # Keep original date for FIFO ordering
                    approved_at=None,
                    paid_at=None,
                    payout_id=None
                )
                db.add(new_pending_commission)
                db.flush()  # Ensure the new commission is written with its own ID
                
                # Update the ORIGINAL commission to the PAID amount
                comm.amount = paid_portion
                selected_commissions.append(comm)
                amount_to_allocate = Decimal("0.00")
                
                print(f"[Admin] New pending commission created with ID {new_pending_commission.id}, amount ${remaining_portion}")

        actual_payout_amount = payout_amount
        linked_amount = sum(Decimal(str(c.amount)) for c in selected_commissions)

        print(f"[Admin] Processing ${actual_payout_amount} payout for user {user_id} via {payment_method}")
        print(f"[Admin] Linked commissions total: ${linked_amount}")

        # A Flutterwave transfer is always a plain NGN bank transfer — see
        # payout_service.py's process_flutterwave_payout, which debits
        # Lavoo's NGN balance for whatever currency `payout.currency` says
        # and has no FX-conversion step of its own. This endpoint used to
        # hardcode currency='USD' on every payout regardless of method, so
        # an admin-approved Flutterwave payout for a non-NGN commission was
        # silently sent to Flutterwave's transfer API tagged "USD" — a
        # currency Lavoo doesn't hold any Flutterwave balance in, and a
        # plausible real cause of payouts failing outright. The automatic
        # immediate-payout path (commission_service.py) already converts
        # non-NGN commissions to NGN via a live FX rate before creating its
        # Payout row; this endpoint has no such conversion, so rather than
        # silently mislabel the currency, block the one case that would
        # actually be wrong and require the FX-aware automatic flow instead.
        commission_currency = (selected_commissions[0].currency or 'USD').upper()
        if payment_method == 'flutterwave' and commission_currency != 'NGN':
            raise HTTPException(
                status_code=400,
                detail=(
                    f"This commission is in {commission_currency}; a Flutterwave payout can only "
                    "send NGN. FX-converting an admin-approved payout isn't supported here — this "
                    "happens automatically when the commission is first earned if the referrer has "
                    "Flutterwave bank details on file, or have them add Stripe payout details instead."
                ),
            )
        payout_currency = 'NGN' if payment_method == 'flutterwave' else commission_currency

        # Create payout record with status 'pending'
        user = db.query(User).filter(User.id == user_id).first()

        # Build account details string for the payout record
        if payment_method == 'stripe':
            account_details = f"Stripe Connect: {payout_account.stripe_account_id}"
        else:
            account_details = f"Bank: {payout_account.bank_name}, Account: ****{payout_account.account_number[-4:] if payout_account.account_number else 'N/A'}"

        payout = Payout(
            user_id=user_id,
            amount=actual_payout_amount,  # Use exact requested amount
            currency=payout_currency,
            payment_method=payment_method,
            status='pending',
            recipient_email=user.email,
            recipient_name=user.name,
            account_details=account_details,
            failure_reason='',  # Initialize as empty string (will be populated on failure)
            requested_at=datetime.now(timezone.utc)
        )
        db.add(payout)
        db.flush()  # Get payout ID

        # Link selected commissions to this payout and mark as 'processing'
        for comm in selected_commissions:
            comm.payout_id = payout.id
            comm.status = 'processing'
            comm.approved_at = datetime.now(timezone.utc)
        
        db.flush()

        # Now process the payout with the provider
        try:
            if payment_method == 'stripe':
                result = PayoutService.process_stripe_payout(payout, background_tasks, db)
                # Stripe is synchronous - on success, commissions are marked 'paid' inside the service
                # Update: Explicitly mark commissions as paid because payout_service might only set payout status
                for comm in selected_commissions:
                    comm.status = 'paid'
                    comm.paid_at = datetime.now(timezone.utc)
                
                db.commit()
                
                return {
                    "status": "success",
                    "message": f"Paid ${actual_payout_amount} via Stripe",
                    "payout_amount": float(actual_payout_amount),
                    "payout_id": payout.id,
                    "payout_status": payout.status,
                    "transfer_id": result.get("transfer_id"),
                    "method": payment_method,
                    "provider_response": json.loads(payout.provider_response) if payout.provider_response else None
                }
            else:
                # Flutterwave is async - payout goes to 'processing', webhook will complete
                result = PayoutService.process_flutterwave_payout(payout, db)
                
                db.commit()
                
                return {
                    "status": "processing",
                    "message": f"Payout of ${actual_payout_amount} initiated via Flutterwave. Awaiting confirmation.",
                    "payout_amount": float(actual_payout_amount),
                    "payout_id": payout.id,
                    "payout_status": payout.status,
                    "transfer_id": result.get("transfer_id"),
                    "method": payment_method
                }

        except Exception as payout_error:
            # Payout failed - revert commission status to 'pending'
            print(f"[Admin] Payout failed: {str(payout_error)}")
            
            for comm in selected_commissions:
                comm.payout_id = None
                comm.status = 'pending'
                comm.approved_at = None
            
            # Mark payout as failed
            payout.status = 'failed'
            payout.failure_reason = str(payout_error)
            payout.failed_at = datetime.now(timezone.utc)
            
            db.commit()
            
            return {
                "status": "failed",
                "message": f"Payout failed: {str(payout_error)}",
                "payout_id": payout.id,
                "payout_status": "failed",
                "failure_reason": str(payout_error),
                "commissions_reverted": True
            }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[Admin] Error in approve_user_commissions: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
        

@router.get("/commissions/user/{user_id}")
async def get_user_commission_details(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed commission breakdown for a specific user"""
    verify_admin(current_user)
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get payout account info
        from database.pg_models import PayoutAccount
        payout_account = db.query(PayoutAccount).filter(
            PayoutAccount.user_id == user_id
        ).first()
        
        # Check available payment methods
        available_methods = []
        if payout_account:
            if payout_account.stripe_account_id:
                available_methods.append({
                    "method": "stripe",
                    "label": "Stripe Connect",
                    "account_id": payout_account.stripe_account_id,
                    "is_default": payout_account.payment_method == "stripe"
                })
            if payout_account.bank_name and payout_account.account_number:
                available_methods.append({
                    "method": "flutterwave",
                    "label": f"Flutterwave ({payout_account.bank_name})",
                    "account_last_4": payout_account.account_number[-4:] if payout_account.account_number else None,
                    "is_default": payout_account.payment_method == "flutterwave"
                })
        
        commissions = db.query(
            Commission.id,
            Commission.amount,
            Commission.status,
            Commission.created_at,
            Commission.approved_at,
            Commission.paid_at,
            User.name.label('referred_user_name'),
            User.email.label('referred_user_email'),
            Subscriptions.subscription_plan,
            Payout.payment_method,
            Payout.id.label('payout_id')
        ).join(
            User, Commission.referred_user_id == User.id
        ).join(
            Subscriptions, Commission.subscription_id == Subscriptions.id
        ).outerjoin(
            Payout, Commission.payout_id == Payout.id
        ).filter(
            Commission.user_id == user_id
        ).order_by(
            Commission.created_at.desc()
        ).all()
        
        result = []
        for comm in commissions:
            result.append({
                "commission_id": comm.id,
                "amount": float(comm.amount),
                "status": comm.status,
                "created_at": comm.created_at.strftime("%Y-%m-%d %H:%M"),
                "approved_at": comm.approved_at.strftime("%Y-%m-%d %H:%M") if comm.approved_at else None,
                "paid_at": comm.paid_at.strftime("%Y-%m-%d %H:%M") if comm.paid_at else None,
                "referred_user": comm.referred_user_name,
                "referred_user_email": comm.referred_user_email,
                "subscription_plan": comm.subscription_plan,
                "payout_method": comm.payment_method,
                "payout_id": comm.payout_id
            })
        
        return {
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email
            },
            "available_payment_methods": available_methods,
            "has_payout_account": payout_account is not None,
            "commissions": result,
            "total": len(result)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting user commission details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/platform-balance")
async def get_platform_balance(
    provider: str = "flutterwave",
    currency: str = "NGN",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Latest platform payout-provider balance snapshot, written by
    run_flutterwave_balance_monitor_job (api/main.py) every 10 minutes.
    Returns a "no_data_yet" status if the job hasn't run since this table
    was added, rather than a confusing empty/zeroed response.
    """
    verify_admin(current_user)

    try:
        from database.pg_models import PlatformBalanceSnapshot

        snapshot = db.query(PlatformBalanceSnapshot).filter(
            PlatformBalanceSnapshot.provider == provider,
            PlatformBalanceSnapshot.currency == currency,
        ).order_by(PlatformBalanceSnapshot.checked_at.desc()).first()

        if not snapshot:
            return {
                "status": "no_data_yet",
                "provider": provider,
                "currency": currency,
            }

        return {
            "status": "ok",
            "provider": snapshot.provider,
            "currency": snapshot.currency,
            "available_balance": float(snapshot.available_balance) if snapshot.available_balance is not None else None,
            "ledger_balance": float(snapshot.ledger_balance) if snapshot.ledger_balance is not None else None,
            "pending_obligations": float(snapshot.pending_obligations) if snapshot.pending_obligations is not None else None,
            "threshold": float(snapshot.threshold) if snapshot.threshold is not None else None,
            "below_threshold": snapshot.below_threshold,
            "check_failed": snapshot.check_failed,
            "error_message": snapshot.error_message,
            "checked_at": snapshot.checked_at.isoformat() if snapshot.checked_at else None,
        }

    except Exception as e:
        print(f"Error fetching platform balance: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payouts")
async def get_all_payouts(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all payout records"""
    verify_admin(current_user)
    
    try:
        payouts = db.query(
            Payout.id,
            Payout.user_id,
            User.name.label('user_name'),
            User.email.label('user_email'),
            Payout.amount,
            Payout.currency,
            Payout.status,
            Payout.payment_method,
            Payout.requested_at,
            Payout.completed_at,
            Payout.failure_reason,
            Payout.provider_payout_id
        ).join(
            User, Payout.user_id == User.id
        ).order_by(
            Payout.requested_at.desc()
        ).limit(limit).offset(offset).all()
        
        total = db.query(func.count(Payout.id)).scalar()
        
        result = []
        for payout in payouts:
            result.append({
                "id": payout.id,
                "user": payout.user_name,
                "user_email": payout.user_email,
                "amount": float(payout.amount),
                "currency": payout.currency,
                "status": payout.status,
                "method": payout.payment_method,
                "requested_at": payout.requested_at.strftime("%Y-%m-%d %H:%M") if payout.requested_at else None,
                "completed_at": payout.completed_at.strftime("%Y-%m-%d %H:%M") if payout.completed_at else None,
                "failure_reason": payout.failure_reason if payout.status == 'failed' else None,
                "provider_payout_id": payout.provider_payout_id
            })
        
        return {
            "payouts": result,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        print(f"Error fetching payouts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payouts/retry/{payout_id}")
async def retry_failed_payout(
    payout_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retry a failed payout"""
    verify_admin(current_user)
    
    try:
        payout = db.query(Payout).filter(Payout.id == payout_id).first()
        
        if not payout:
            raise HTTPException(status_code=404, detail="Payout not found")
        
        if payout.status != 'failed':
            raise HTTPException(
                status_code=400,
                detail=f"Payout is not failed (status: {payout.status})"
            )
        
        # Reset status and retry
        payout.status = 'pending'
        payout.failure_reason = ''
        db.commit()
        
        # Process again
        if payout.payment_method == 'stripe':
            result = PayoutService.process_stripe_payout(payout, background_tasks, db)
        elif payout.payment_method == 'flutterwave':
            result = PayoutService.process_flutterwave_payout(payout, db)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported payment method: {payout.payment_method}"
            )
        
        return {
            "status": "success",
            "message": "Payout retry initiated",
            "payout_id": payout.id,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/payouts/simulate-complete/{payout_id}")
async def simulate_payout_completion(
    payout_id: int,
    background_tasks: BackgroundTasks,
    success: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    TEST ENDPOINT: Simulate payout completion (for testing without real webhooks).
    
    Use this in development/test mode to verify the payout completion flow.
    
    Args:
        payout_id: ID of the payout to complete
        success: True to simulate success, False to simulate failure
    """
    verify_admin(current_user)
    
    try:
        payout = db.query(Payout).filter(Payout.id == payout_id).first()
        
        if not payout:
            raise HTTPException(status_code=404, detail="Payout not found")
        
        if payout.status not in ['pending', 'processing']:
            raise HTTPException(
                status_code=400,
                detail=f"Payout is already {payout.status}"
            )
        
        # Simulate webhook completion based on payment method
        if payout.payment_method == 'stripe':
            stripe_status = "paid" if success else "failed"
            PayoutService.complete_stripe_payout(payout_id, background_tasks, stripe_status, db)
            status_text = "completed" if success else "failed"
            return {
                "status": "success",
                "message": f"Simulated {stripe_status} completion for Stripe payout {payout_id}",
                "payout_status": status_text
            }
        else:
            # Default to Flutterwave (current behavior)
            fw_status = "successful" if success else "failed"
            PayoutService.complete_flutterwave_payout(payout_id, background_tasks, fw_status, db)
            status_text = "completed" if success else "failed"
            return {
                "status": "success",
                "message": f"Simulated {fw_status} completion for payout {payout_id}",
                "payout_status": status_text
            }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))