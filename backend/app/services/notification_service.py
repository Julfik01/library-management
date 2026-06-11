import logging

logger = logging.getLogger(__name__)


async def send_overdue_notification(db, loan, student_email: str | None = None):
    """Send overdue notification to student. Uses fastapi-mail if available; otherwise logs."""
    # student_email can be fetched from db if not provided — caller may supply.
    try:
        from fastapi_mail import FastMail, MessageSchema
        from app.config import settings

        message = MessageSchema(
            subject="Library: overdue notice",
            recipients=[student_email] if student_email else [],
            body=f"Your loan {loan.id} for book {loan.book_id} is overdue.",
        )
        fm = FastMail(settings.MAIL_CONFIG)  # settings.MAIL_CONFIG optional
        await fm.send_message(message)
    except Exception:
        # Fail silently in production job context; log for debugging in dev
        logger.info("(Notification fallback) Overdue notification for loan %s to %s", loan.id, student_email)
