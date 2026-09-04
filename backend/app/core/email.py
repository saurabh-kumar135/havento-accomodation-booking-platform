import smtplib
import ssl
import base64
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

async def get_oauth2_access_token() -> str:
    """Fetch a fresh OAuth2 access token from Google using the refresh token."""
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": settings.GMAIL_CLIENT_ID,
        "client_secret": settings.GMAIL_CLIENT_SECRET,
        "refresh_token": settings.GMAIL_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=payload)
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            logger.error(f"Failed to refresh OAuth2 token: {response.text}")
            raise Exception(f"OAuth2 token refresh failed: {response.status_code}")

def build_oauth2_string(user: str, access_token: str) -> str:
    """Format string for XOAUTH2 authentication."""
    auth_string = f"user={user}\1auth=Bearer {access_token}\1\1"
    return base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

async def send_email_async(to_email: str, subject: str, html_content: str) -> bool:
    """Send an HTML email via Gmail OAuth2 or fallback to SMTP."""
    sender = settings.EMAIL_USER
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"HavenTo <{sender}>"
    msg["To"] = to_email
    
    part = MIMEText(html_content, "html")
    msg.attach(part)
    
    # Try OAuth2 first if configured
    if settings.GMAIL_CLIENT_ID and settings.GMAIL_REFRESH_TOKEN:
        try:
            access_token = await get_oauth2_access_token()
            # Send using Gmail REST API (most reliable across all cloud environments)
            raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
            gmail_send_url = f"https://gmail.googleapis.com/gmail/v1/users/{sender}/messages/send"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                res = await client.post(gmail_send_url, headers=headers, json={"raw": raw_msg})
                if res.status_code in [200, 201]:
                    logger.info(f"✅ Email sent successfully via Gmail OAuth2 REST API to {to_email}")
                    return True
                else:
                    logger.warning(f"OAuth2 REST API send returned {res.status_code}: {res.text}. Trying SMTP...")
        except Exception as e:
            logger.error(f"OAuth2 send error: {str(e)}. Falling back to SMTP.")
    
    # Fallback: SMTP with SSL
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(settings.EMAIL_USER, settings.EMAIL_PASS.replace(" ", ""))
            server.sendmail(sender, to_email, msg.as_string())
            logger.info(f"✅ Email sent successfully via SMTP to {to_email}")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to send email via SMTP to {to_email}: {str(e)}")
        return False

async def send_otp_email(email: str, otp: str, first_name: str = "there") -> bool:
    """Send registration verification OTP email."""
    subject = "Complete your HavenTo registration - Verification Code"
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Verify Your Email</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a202c; margin: 0; padding: 20px; background-color: #f7fafc;">
      <div style="max-width: 540px; margin: 0 auto; background: #ffffff; padding: 32px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); border: 1px solid #e2e8f0;">
        <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; padding: 28px; text-align: center; border-radius: 12px; margin-bottom: 24px;">
          <h1 style="margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px;">Welcome to HavenTo! 🏡</h1>
        </div>
        
        <p style="font-size: 16px;">Hi <strong>{first_name}</strong>,</p>
        <p style="font-size: 15px; color: #4a5568;">Thank you for joining HavenTo! Please use the 6-digit verification code below to complete your registration:</p>
        
        <div style="text-align: center; margin: 28px 0; padding: 20px; background: #f8fafc; border-radius: 12px; border: 2px dashed #cbd5e1;">
          <div style="font-size: 36px; font-weight: 800; letter-spacing: 8px; color: #4f46e5; font-family: 'Courier New', Courier, monospace;">{otp}</div>
          <p style="margin: 8px 0 0 0; font-size: 13px; color: #64748b;">Valid for 10 minutes</p>
        </div>
        
        <p style="font-size: 14px; color: #718096;">If you didn't create an account with HavenTo, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <div style="text-align: center; color: #94a3b8; font-size: 12px;">
          <p style="margin: 0;">© HavenTo Inc. All rights reserved.</p>
        </div>
      </div>
    </body>
    </html>
    """
    return await send_email_async(email, subject, html)

async def send_password_reset_email(email: str, reset_token: str, first_name: str = "there") -> bool:
    """Send password reset link email."""
    frontend_url = settings.FRONTEND_URL.rstrip('/')
    reset_link = f"{frontend_url}/reset-password/{reset_token}"
    subject = "Reset your HavenTo password"
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>Reset Your Password</title>
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1a202c; margin: 0; padding: 20px; background-color: #f7fafc;">
      <div style="max-width: 540px; margin: 0 auto; background: #ffffff; padding: 32px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); border: 1px solid #e2e8f0;">
        <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; padding: 28px; text-align: center; border-radius: 12px; margin-bottom: 24px;">
          <h1 style="margin: 0; font-size: 24px; font-weight: 700;">Password Reset 🔑</h1>
        </div>
        
        <p style="font-size: 16px;">Hi <strong>{first_name}</strong>,</p>
        <p style="font-size: 15px; color: #4a5568;">We received a request to reset your password for your HavenTo account.</p>
        
        <div style="text-align: center; margin: 28px 0;">
          <a href="{reset_link}" style="display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px; box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.3);">Reset My Password</a>
        </div>
        
        <p style="font-size: 13px; color: #64748b; margin-top: 20px;">Or copy and paste this link into your browser:</p>
        <div style="background: #f1f5f9; padding: 12px; border-radius: 8px; word-break: break-all; font-size: 12px; color: #475569;">
          <a href="{reset_link}" style="color: #4f46e5; text-decoration: none;">{reset_link}</a>
        </div>
        
        <p style="font-size: 13px; color: #e11d48; margin-top: 20px;"><strong>⏰ This link expires in 1 hour.</strong></p>
        <p style="font-size: 13px; color: #94a3b8;">If you didn't request this reset, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
        <div style="text-align: center; color: #94a3b8; font-size: 12px;">
          <p style="margin: 0;">© HavenTo Inc. All rights reserved.</p>
        </div>
      </div>
    </body>
    </html>
    """
    return await send_email_async(email, subject, html)
