
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
from datetime import datetime
import os
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrevoEmailService:
    def __init__(self):
        # Configure Brevo API
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")
        
        # Initialize API instances
        self.transactional_api = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        self.contacts_api = sib_api_v3_sdk.ContactsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )
        
        self.from_email = os.getenv("BREVO_FROM_EMAIL")
        self.from_name = os.getenv("BREVO_FROM_NAME")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        self.support_email = os.getenv("SUPPORT_EMAIL", "support@yourapp.com")
    
    def _send_transactional_email(self, to_email: str, to_name: str, subject: str, 
                                  html_content: str, text_content: Optional[str] = None):
        """Internal method to send transactional email with retry logic"""
        import time
        max_retries = 3
        retry_delay = 1 # second
        
        last_error = None
        for attempt in range(max_retries):
            try:
                print(f"INFO - Attempt {attempt+1}/{max_retries}: Sending email to {to_email} with subject: '{subject}'")
                send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                    to=[{"email": to_email, "name": to_name}],
                    sender={"email": self.from_email, "name": self.from_name},
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content
                )
                
                api_response = self.transactional_api.send_transac_email(send_smtp_email)
                print(f"INFO - Email sent successfully to {to_email}. Message ID: {api_response.message_id}")
                logger.info(f"Email sent successfully. Message ID: {api_response.message_id}")
                
                return {
                    "success": True,
                    "message_id": api_response.message_id,
                    "status": "sent"
                }
                
            except (ApiException, Exception) as e:
                last_error = e
                error_msg = f"Attempt {attempt+1} failed: {str(e)}"
                print(f"WARNING - {error_msg}")
                logger.warning(error_msg)
                
                # Check for specific network errors that deserve a retry
                error_str = str(e).lower()
                if "connection aborted" in error_str or "remotedisconnected" in error_str or "timeout" in error_str:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                
                # If not a retryable error or last attempt
                if isinstance(e, ApiException):
                    raise Exception(f"Brevo API Error: {str(e)}")
                raise e
                
        raise Exception(f"Failed to send email after {max_retries} attempts: {str(last_error)}")
    
    def send_welcome_email(self, user_email: str, name: str):
        """Send welcome email on signup"""
        subject = "Welcome to Lavoo Business Intelligence Engine!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ 
                    background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); 
                    color: white; padding: 30px; text-align: center; 
                    border-radius: 10px 10px 0 0; 
                }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .button {{ 
                    display: inline-block; padding: 12px 30px; background: #f97316; 
                    color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; 
                }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
                ul {{ padding-left: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">Welcome to AI Analyst Engine!</h1>
                </div>
                <div class="content">
                    <h2>Hi {name},</h2>
                    <p>We're thrilled to have you on board! Your account has been successfully created.</p>
                    <p><strong>With AI Analyst Engine, you can:</strong></p>
                    <ul>
                        <li>Run powerful AI-driven analyses</li>
                        <li>Generate comprehensive reports</li>
                        <li>Earn commissions through referrals</li>
                        <li>Access premium features</li>
                    </ul>
                    <p style="text-align: center;">
                        <a href="{self.frontend_url}" class="button">Get Started</a>
                    </p>
                    <p>If you have any questions, feel free to reach out to our support team.</p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.now().year} Lavoo Business Intelligence Engine. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"Welcome to Lavoo Business Intelligence Engine!\n\nHi {name},\n\nWe're thrilled to have you on board!"
        
        return self._send_transactional_email(user_email, name, subject, html_content, text_content)
    
    def send_payout_email(self, user_email: str, name: str, amount: float,
                         commission_from: str, transaction_id: str):
        """Send payout notification email"""
        subject = "Commission Payout Received!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ 
                    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                    color: white; padding: 30px; text-align: center; 
                    border-radius: 10px 10px 0 0; 
                }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .payout-box {{ 
                    background: white; border-left: 4px solid #11998e; 
                    padding: 20px; margin: 20px 0; 
                }}
                .amount {{ font-size: 32px; font-weight: bold; color: #11998e; }}
                .button {{ 
                    display: inline-block; padding: 12px 30px; background: #11998e; 
                    color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">💰 Commission Payout Received!</h1>
                </div>
                <div class="content">
                    <h2>Great news, {name}!</h2>
                    <p>You've received a commission payout.</p>
                    <div class="payout-box">
                        <p><strong>Amount:</strong> <span class="amount">${amount:.2f}</span></p>
                        <p><strong>From:</strong> {commission_from}</p>
                        <p><strong>Transaction ID:</strong> {transaction_id}</p>
                        <p><strong>Date:</strong> {datetime.now().strftime("%B %d, %Y")}</p>
                    </div>
                    <p style="text-align: center;">
                        <a href="{self.frontend_url}/dashboard/earnings" class="button">View Commission Details</a>
                    </p>
                    <p>Keep up the great work!</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"Commission Payout Received!\n\nAmount: ${amount:.2f}\nFrom: {commission_from}\nTransaction ID: {transaction_id}"
        
        return self._send_transactional_email(user_email, name, subject, html_content, text_content)
    
    def send_payment_success_email(self, user_email: str, name: str, amount: float,
                                   plan_name: str, next_billing_date: str):
        """Send payment success email"""
        subject = "Payment Successful - Subscription Active"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ 
                    background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); 
                    color: white; padding: 30px; text-align: center; 
                    border-radius: 10px 10px 0 0; 
                }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .payment-box {{ 
                    background: white; border-left: 4px solid #f97316; 
                    padding: 20px; margin: 20px 0; 
                }}
                .button {{ 
                    display: inline-block; padding: 12px 30px; background: #f97316; 
                    color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">✓ Payment Successful</h1>
                </div>
                <div class="content">
                    <h2>Thank you, {name}!</h2>
                    <p>Your subscription payment has been processed successfully.</p>
                    <div class="payment-box">
                        <p><strong>Amount Paid:</strong> ${amount:.2f}</p>
                        <p><strong>Plan:</strong> {plan_name}</p>
                        <p><strong>Payment Date:</strong> {datetime.now().strftime("%B %d, %Y")}</p>
                        <p><strong>Next Billing Date:</strong> {next_billing_date}</p>
                    </div>
                    <p style="text-align: center;">
                        <a href="{self.frontend_url}/dashboard/billing" class="button">View Invoice</a>
                    </p>
                    <p>Your subscription is now active!</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"Payment Successful!\n\nAmount: ${amount:.2f}\nPlan: {plan_name}\nNext Billing: {next_billing_date}"
        
        return self._send_transactional_email(user_email, name, subject, html_content, text_content)
    
    def send_payout_success_email(self, user_id: int, amount: float,
                                 currency: str, payout_id: int, processed_at: datetime):
        """Send payout success email"""
        from db.pg_connections import SessionLocal
        from db.pg_models import User
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                print(f"ERROR - User {user_id} not found for payout success email")
                return
            
            user_email = user.email
            name = user.name
            subject = "Payout Successful - Funds Dispatched"
            
            processed_date = processed_at.strftime("%B %d, %Y") if processed_at else datetime.now().strftime("%B %d, %Y")
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ 
                        background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); 
                        color: white; padding: 30px; text-align: center; 
                        border-radius: 10px 10px 0 0; 
                    }}
                    .content {{ background: #f9f9f9; padding: 30px; }}
                    .payout-box {{ 
                        background: white; border-left: 4px solid #f97316; 
                        padding: 20px; margin: 20px 0; 
                    }}
                    .amount {{ font-size: 32px; font-weight: bold; color: #f97316; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1 style="margin: 0;">💰 Payout Successful!</h1>
                    </div>
                    <div class="content">
                        <h2>Hi {name},</h2>
                        <p>Good news! Your payout has been successfully processed and dispatched.</p>
                        <div class="payout-box">
                            <p><strong>Amount:</strong> <span class="amount">{currency} {amount:.2f}</span></p>
                            <p><strong>Payout ID:</strong> #{payout_id}</p>
                            <p><strong>Processed Date:</strong> {processed_date}</p>
                        </div>
                        <p>The funds should reflect in your account shortly, depending on your bank's processing time.</p>
                        <p>Thank you for being a part of our platform!</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_content = f"Payout Successful!\n\nHi {name},\nYour payout of {currency} {amount:.2f} has been processed.\nPayout ID: #{payout_id}"
            
            return self._send_transactional_email(user_email, name, subject, html_content, text_content)
        finally:
            db.close()
    
    def send_payment_failed_email(self, user_email: str, name: str, amount: float, reason: str):
        """Send payment failed email"""
        subject = "Payment Failed - Action Required"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ 
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                    color: white; padding: 30px; text-align: center; 
                    border-radius: 10px 10px 0 0; 
                }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .alert-box {{ 
                    background: #fff3cd; border-left: 4px solid #f5576c; 
                    padding: 20px; margin: 20px 0; 
                }}
                .button {{ 
                    display: inline-block; padding: 12px 30px; background: #f5576c; 
                    color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">⚠️ Payment Failed</h1>
                </div>
                <div class="content">
                    <h2>Hi {name},</h2>
                    <p>We were unable to process your subscription payment.</p>
                    <div class="alert-box">
                        <p><strong>Amount:</strong> ${amount:.2f}</p>
                        <p><strong>Reason:</strong> {reason}</p>
                    </div>
                    <p>Please update your payment method to continue.</p>
                    <p style="text-align: center;">
                        <a href="{self.frontend_url}/dashboard/upgrade" class="button">Update Payment Method</a>
                    </p>
                    <p>Need help? Contact us at {self.support_email}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"Payment Failed\n\nAmount: ${amount:.2f}\nReason: {reason}\n\nPlease update your payment method."
        
        return self._send_transactional_email(user_email, name, subject, html_content, text_content)
    
    def send_report_download_email(self, user_email: str, name: str, 
                                   report_name: str, analysis_type: str, download_url: str):
        """Send report download email"""
        subject = "Your Analysis Report is Ready"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ 
                    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); 
                    color: white; padding: 30px; text-align: center; 
                    border-radius: 10px 10px 0 0; 
                }}
                .content {{ background: #f9f9f9; padding: 30px; }}
                .report-box {{ 
                    background: white; border-left: 4px solid #4facfe; 
                    padding: 20px; margin: 20px 0; 
                }}
                .button {{ 
                    display: inline-block; padding: 12px 30px; background: #4facfe; 
                    color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; 
                }}
                .note {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0;">📊 Your Report is Ready!</h1>
                </div>
                <div class="content">
                    <h2>Hi {name},</h2>
                    <p>Your analysis report has been generated.</p>
                    <div class="report-box">
                        <p><strong>Report Name:</strong> {report_name}</p>
                        <p><strong>Analysis Type:</strong> {analysis_type}</p>
                        <p><strong>Generated:</strong> {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>
                    </div>
                    <p style="text-align: center;">
                        <a href="{download_url}" class="button">Download Report</a>
                    </p>
                    <div class="note">
                        <p><strong>Note:</strong> This download link will expire in 7 days.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"Your Report is Ready!\n\nReport: {report_name}\nType: {analysis_type}\n\nDownload: {download_url}"
        
        return self._send_transactional_email(user_email, name, subject, html_content, text_content)
    

# Initialize service
email_service = BrevoEmailService()

# Module-level functions for direct access
def send_payout_success_email(user_id: int, amount: float,
                             currency: str, payout_id: int, processed_at: datetime):
    return email_service.send_payout_success_email(user_id, amount, currency, payout_id, processed_at)

# FastAPI Routes
router = APIRouter(prefix="/api/emails", tags=["emails"])

# Request models
class WelcomeEmailRequest(BaseModel):
    user_email: EmailStr
    user_name: str

class PayoutEmailRequest(BaseModel):
    user_email: EmailStr
    user_name: str
    amount: float
    commission_from: str
    transaction_id: str

class PaymentSuccessRequest(BaseModel):
    user_email: EmailStr
    user_name: str
    amount: float
    plan_name: str
    next_billing_date: str

class PaymentFailedRequest(BaseModel):
    user_email: EmailStr
    user_name: str
    amount: float
    reason: str

class ReportDownloadRequest(BaseModel):
    user_email: EmailStr
    user_name: str
    report_name: str
    analysis_type: str
    download_url: str

class WaitlistRequest(BaseModel):
    email: EmailStr
    name: str
    source: Optional[str] = "website"

# Transactional email endpoints
@router.post("/welcome")
async def send_welcome(request: WelcomeEmailRequest, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(
            email_service.send_welcome_email,
            request.user_email,
            request.user_name
        )
        return {"message": "Welcome email queued", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payout")
async def send_payout(request: PayoutEmailRequest, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(
            email_service.send_payout_email,
            request.user_email,
            request.user_name,
            request.amount,
            request.commission_from,
            request.transaction_id
        )
        return {"message": "Payout email queued", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment-success")
async def send_payment_success(request: PaymentSuccessRequest, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(
            email_service.send_payment_success_email,
            request.user_email,
            request.user_name,
            request.amount,
            request.plan_name,
            request.next_billing_date
        )
        return {"message": "Payment success email queued", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/payment-failed")
async def send_payment_failed(request: PaymentFailedRequest, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(
            email_service.send_payment_failed_email,
            request.user_email,
            request.user_name,
            request.amount,
            request.reason
        )
        return {"message": "Payment failed email queued", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/report-download")
async def send_report_download(request: ReportDownloadRequest, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(
            email_service.send_report_download_email,
            request.user_email,
            request.user_name,
            request.report_name,
            request.analysis_type,
            request.download_url
        )
        return {"message": "Report email queued", "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

