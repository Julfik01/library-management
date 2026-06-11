import datetime
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loan import Loan
from app.models.user import User
from app.database import AsyncSessionLocal
from app.services.notification_service import send_overdue_notification

logger = logging.getLogger(__name__)


async def mark_overdue_once():
    """Idempotent job: mark active loans past due_date as 'overdue' and notify once.

    Uses overdue_notified_at sentinel on Loan to ensure single notification.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    async with AsyncSessionLocal() as db:  # create independent session for job
        # Select loans that are past due and still active
        stmt = select(Loan).where(Loan.due_date < now, Loan.status == 'active')
        res = await db.execute(stmt)
        loans = res.scalars().all()
        for loan in loans:
            # Double-check idempotency: if overdue_notified_at already set, we still transition status
            loan.status = 'overdue'
            if loan.overdue_notified_at is None:
                loan.overdue_notified_at = now
                # Try to fetch student email for notification
                student = await db.get(User, loan.student_id)
                email = getattr(student, 'email', None)
                await send_overdue_notification(db, loan, student_email=email)
        await db.commit()
    logger.info("Overdue job completed; processed %d loans", len(loans))
