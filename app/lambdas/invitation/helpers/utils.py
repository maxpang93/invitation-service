from datetime import datetime, timezone, timedelta
import json
import random
import string
from typing import Any

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


def build_response(
    status_code: int,
    success: bool,
    message: str,
    data: Any = None,
):
    body = {
        "success": success,
        "message": message,
        "data": data,
    }
    response = {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET,PUT,DELETE",
            "Content-Type": "application/json",
        },
        "body": json.dumps(body),
    }
    return response
