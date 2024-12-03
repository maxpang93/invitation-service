from datetime import datetime, timezone, timedelta
import random
import string

from .schemas import (
    Invitation,
    InvitationStatus,
)


def generate_code(length=8) -> str:
    return "".join(random.choices(string.ascii_letters, k=length))


def generate_invitation(
    email: str,
    code: str,
    valid_days: int = 7,
):
    now_utc = datetime.now(timezone.utc)
    return Invitation(
        code=code,
        email=email,
        invite_status=InvitationStatus.UNCONFIRMED,
        created_date=now_utc,
        expiry_date=now_utc + timedelta(days=valid_days),
    )
