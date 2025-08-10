"""
Email service for sending authentication and notification emails.
"""

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME

        # Initialize Jinja2 environment for email templates
        self.jinja_env = Environment(
            loader=FileSystemLoader("app/templates/email"),
            autoescape=select_autoescape(["html", "xml"]),
        )

    async def send_verification_email(
        self, email: str, token: str, display_name: Optional[str] = None
    ) -> bool:
        """
        Send email verification email.

        Args:
            email: Recipient email address
            token: Email verification token
            display_name: User's display name (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Generate verification URL
            verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

            # Render email template
            template = self.jinja_env.get_template("email_verification.html")
            html_content = template.render(
                display_name=display_name or "User",
                verification_url=verification_url,
                app_name="Project Kessan",
                support_email=settings.SUPPORT_EMAIL,
            )

            # Create plain text version
            text_content = f"""
Hello {display_name or "User"},

Thank you for registering with Project Kessan!

Please verify your email address by clicking the link below:
{verification_url}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.

Best regards,
The Project Kessan Team

Support: {settings.SUPPORT_EMAIL}
            """.strip()

            # Send email
            success = await self._send_email(
                to_email=email,
                subject="Verify your email address - Project Kessan",
                text_content=text_content,
                html_content=html_content,
            )

            if success:
                logger.info(f"Verification email sent successfully to: {email}")
            else:
                logger.error(f"Failed to send verification email to: {email}")

            return success

        except Exception as e:
            logger.error(f"Error sending verification email to {email}: {e}")
            return False

    async def send_password_reset_email(
        self, email: str, token: str, display_name: Optional[str] = None
    ) -> bool:
        """
        Send password reset email.

        Args:
            email: Recipient email address
            token: Password reset token
            display_name: User's display name (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Generate reset URL
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

            # Render email template
            template = self.jinja_env.get_template("password_reset.html")
            html_content = template.render(
                display_name=display_name or "User",
                reset_url=reset_url,
                app_name="Project Kessan",
                support_email=settings.SUPPORT_EMAIL,
            )

            # Create plain text version
            text_content = f"""
Hello {display_name or "User"},

You requested a password reset for your Project Kessan account.

Please reset your password by clicking the link below:
{reset_url}

This link will expire in 1 hour.

If you didn't request a password reset, please ignore this email.

Best regards,
The Project Kessan Team

Support: {settings.SUPPORT_EMAIL}
            """.strip()

            # Send email
            success = await self._send_email(
                to_email=email,
                subject="Reset your password - Project Kessan",
                text_content=text_content,
                html_content=html_content,
            )

            if success:
                logger.info(f"Password reset email sent successfully to: {email}")
            else:
                logger.error(f"Failed to send password reset email to: {email}")

            return success

        except Exception as e:
            logger.error(f"Error sending password reset email to {email}: {e}")
            return False

    async def send_welcome_email(
        self, email: str, display_name: Optional[str] = None
    ) -> bool:
        """
        Send welcome email after successful registration.

        Args:
            email: Recipient email address
            display_name: User's display name (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Render email template
            template = self.jinja_env.get_template("welcome.html")
            html_content = template.render(
                display_name=display_name or "User",
                app_name="Project Kessan",
                dashboard_url=f"{settings.FRONTEND_URL}/dashboard",
                support_email=settings.SUPPORT_EMAIL,
            )

            # Create plain text version
            text_content = f"""
Welcome to Project Kessan, {display_name or "User"}!

Thank you for joining our AI-powered Japanese stock analysis platform.

Get started by visiting your dashboard:
{settings.FRONTEND_URL}/dashboard

Here's what you can do:
- Search and analyze Japanese stocks
- Create personalized watchlists
- Get AI-powered investment insights
- Track market trends and news

If you have any questions, feel free to contact our support team at {settings.SUPPORT_EMAIL}.

Best regards,
The Project Kessan Team
            """.strip()

            # Send email
            success = await self._send_email(
                to_email=email,
                subject="Welcome to Project Kessan!",
                text_content=text_content,
                html_content=html_content,
            )

            if success:
                logger.info(f"Welcome email sent successfully to: {email}")
            else:
                logger.error(f"Failed to send welcome email to: {email}")

            return success

        except Exception as e:
            logger.error(f"Error sending welcome email to {email}: {e}")
            return False

    async def send_subscription_notification(
        self,
        email: str,
        notification_type: str,
        display_name: Optional[str] = None,
        **kwargs,
    ) -> bool:
        """
        Send subscription-related notification email.

        Args:
            email: Recipient email address
            notification_type: Type of notification (upgrade, downgrade, expiry, etc.)
            display_name: User's display name (optional)
            **kwargs: Additional template variables

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Map notification types to templates and subjects
            notification_config = {
                "upgrade": {
                    "template": "subscription_upgrade.html",
                    "subject": "Subscription Upgraded - Project Kessan",
                },
                "downgrade": {
                    "template": "subscription_downgrade.html",
                    "subject": "Subscription Changed - Project Kessan",
                },
                "expiry_warning": {
                    "template": "subscription_expiry_warning.html",
                    "subject": "Subscription Expiring Soon - Project Kessan",
                },
                "expired": {
                    "template": "subscription_expired.html",
                    "subject": "Subscription Expired - Project Kessan",
                },
                "payment_failed": {
                    "template": "payment_failed.html",
                    "subject": "Payment Failed - Project Kessan",
                },
            }

            config = notification_config.get(notification_type)
            if not config:
                logger.error(f"Unknown notification type: {notification_type}")
                return False

            # Render email template
            template = self.jinja_env.get_template(config["template"])
            html_content = template.render(
                display_name=display_name or "User",
                app_name="Project Kessan",
                dashboard_url=f"{settings.FRONTEND_URL}/dashboard",
                billing_url=f"{settings.FRONTEND_URL}/billing",
                support_email=settings.SUPPORT_EMAIL,
                **kwargs,
            )

            # Create basic plain text version
            text_content = f"""
Hello {display_name or "User"},

This is a notification about your Project Kessan subscription.

Please visit your dashboard for more details:
{settings.FRONTEND_URL}/dashboard

If you have any questions, contact us at {settings.SUPPORT_EMAIL}.

Best regards,
The Project Kessan Team
            """.strip()

            # Send email
            success = await self._send_email(
                to_email=email,
                subject=config["subject"],
                text_content=text_content,
                html_content=html_content,
            )

            if success:
                logger.info(
                    f"Subscription notification ({notification_type}) sent to: {email}"
                )
            else:
                logger.error(f"Failed to send subscription notification to: {email}")

            return success

        except Exception as e:
            logger.error(f"Error sending subscription notification to {email}: {e}")
            return False

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        text_content: str,
        html_content: Optional[str] = None,
    ) -> bool:
        """
        Send email using SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            text_content: Plain text email content
            html_content: HTML email content (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Add text part
            text_part = MIMEText(text_content, "plain", "utf-8")
            message.attach(text_part)

            # Add HTML part if provided
            if html_content:
                html_part = MIMEText(html_content, "html", "utf-8")
                message.attach(html_part)

            # Send email
            if settings.ENVIRONMENT == "development":
                # In development, just log the email instead of sending
                logger.info(f"[DEV] Email would be sent to {to_email}: {subject}")
                logger.debug(f"[DEV] Email content: {text_content}")
                return True

            # Create secure connection and send email
            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)

            return True

        except Exception as e:
            logger.error(f"SMTP error sending email to {to_email}: {e}")
            return False

    async def send_test_email(self, to_email: str) -> bool:
        """
        Send a test email to verify email configuration.

        Args:
            to_email: Recipient email address

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            text_content = """
This is a test email from Project Kessan.

If you received this email, the email configuration is working correctly.

Best regards,
The Project Kessan Team
            """.strip()

            success = await self._send_email(
                to_email=to_email,
                subject="Test Email - Project Kessan",
                text_content=text_content,
            )

            if success:
                logger.info(f"Test email sent successfully to: {to_email}")
            else:
                logger.error(f"Failed to send test email to: {to_email}")

            return success

        except Exception as e:
            logger.error(f"Error sending test email to {to_email}: {e}")
            return False
