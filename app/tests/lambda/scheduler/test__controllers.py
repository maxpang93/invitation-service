"""
Only testing controllers because queries etc. are similar to /lambdas/invitation/
"""
import os

from lambdas.scheduler.helpers.schemas import InvitationStatus

# import from 'invitation', reason: get ALL for items count validation
from lambdas.invitation.helpers.queries import (
    query_by_gsi,
)
from lambdas.scheduler.helpers.controllers import (
    process_expired_unconfirmed_invitations,
)


def test_convert_expired_unconfirmed_invitations(
    table_with_many_items,
):
    unconfirmed_before = query_by_gsi(
        table=table_with_many_items,
        gsi_name=os.environ["TABLE_GSI_NAME"],
        invite_status=InvitationStatus.UNCONFIRMED,
    )
    expired_before = query_by_gsi(
        table=table_with_many_items,
        gsi_name=os.environ["TABLE_GSI_NAME"],
        invite_status=InvitationStatus.EXPIRED,
    )

    process_expired_unconfirmed_invitations(
        table=table_with_many_items, gsi_name=os.environ["TABLE_GSI_NAME"]
    )

    unconfirmed_after = query_by_gsi(
        table=table_with_many_items,
        gsi_name=os.environ["TABLE_GSI_NAME"],
        invite_status=InvitationStatus.UNCONFIRMED,
    )
    expired_after = query_by_gsi(
        table=table_with_many_items,
        gsi_name=os.environ["TABLE_GSI_NAME"],
        invite_status=InvitationStatus.EXPIRED,
    )

    UNCONFIRMED_BUT_EXPIRED_COUNT = int(os.environ["UNCONFIRMED_BUT_EXPIRED_COUNT"])
    NEW_UNCONFIRMED_COUNT = int(os.environ["NEW_UNCONFIRMED_COUNT"])
    EXPIRED_COUNT = int(os.environ["EXPIRED_COUNT"])

    assert len(expired_before) == EXPIRED_COUNT
    assert (
        len(unconfirmed_before) == UNCONFIRMED_BUT_EXPIRED_COUNT + NEW_UNCONFIRMED_COUNT
    )
    assert len(expired_after) == EXPIRED_COUNT + UNCONFIRMED_BUT_EXPIRED_COUNT
    assert len(unconfirmed_after) == NEW_UNCONFIRMED_COUNT
