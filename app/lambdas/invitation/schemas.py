from datetime import datetime
from enum import Enum
from dataclasses import dataclass


class InvitationStatus(str, Enum):
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"


@dataclass
class Invitation:
    code: str
    email: str
    invite_status: InvitationStatus
    created_date: datetime
    expiry_date: datetime

    def __post_init__(self):
        # convert datetime to string
        if not isinstance(self.created_date, str):
            self.created_date = self.created_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        if not isinstance(self.expiry_date, str):
            self.expiry_date = self.expiry_date.strftime("%Y-%m-%dT%H:%M:%SZ")
