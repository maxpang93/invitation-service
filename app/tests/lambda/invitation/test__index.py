import json

import pytest

from lambdas.invitation.index import (
    create_new_invitation,
    confirm_invitation,
    review_all_invitations,
    # invalidate_invitation,
)
from lambdas.invitation.schemas import InvitationStatus


@pytest.mark.parametrize(
    "request_body, status_code, response_body",
    [
        # success case
        (
            {
                "email": "abc@gmail.com",
            },
            200,
            {
                "success": True,
                "message": "Invitation created!",
            },
        ),
        # missing email
        (
            {},
            422,
            {
                "success": False,
                "message": "Missing email.",
            },
        ),
    ],
)
def test_create_new_invitation(
    empty_table,
    request_body: dict,
    status_code: int,
    response_body: dict,
):
    resp = create_new_invitation(empty_table, request_body)
    body = json.loads(resp["body"])

    assert resp["statusCode"] == status_code
    assert body["success"] == response_body["success"]
    assert body["message"] == response_body["message"]


@pytest.mark.parametrize(
    "query_params, items_found",
    [
        # no filter (use scan)
        (
            {},
            6,
        ),
        # filter by email
        (
            {
                "email": "abc@gmail.com",
            },
            2,
        ),
        # filter by email, code
        (
            {
                "email": "abc@gmail.com",
                "code": "ABCD1234",
            },
            1,
        ),
        # filter by invite status
        (
            {
                "invite_status": "unconfirmed",
            },
            3,
        ),
        # filter by status, email
        (
            {
                "invite_status": "unconfirmed",
                "email": "def@yahoo.com",
            },
            1,
        ),
    ],
)
def test_review_all_invitations(
    table_with_items,
    query_params: dict,
    items_found: int,
):
    resp = review_all_invitations(table_with_items, query_params)
    body = json.loads(resp["body"])
    data = body["data"]
    assert isinstance(data, list)
    assert len(data) == items_found


@pytest.mark.parametrize(
    "request_body, status_code, message, invite_status",
    [
        # Missing request body key-value
        (
            {
                "code": "ABCD1234",
            },
            422,
            "Missing 'code' or 'email'.",
            None,
        ),
        # Code does not exist
        (
            {
                "email": "abc@gmail.com",
                "code": "DONTEXIST",
            },
            404,
            "Invite code: DONTEXIST is invalid or does not exist.",
            None,
        ),
        # Code expired
        (
            {
                "email": "expired@gmail.com",
                "code": "EXPIRED01",
            },
            200,
            "Invite code: EXPIRED01 already expired.",
            InvitationStatus.EXPIRED,
        ),
        # Code expired but status still "unconfirmed"
        (
            {
                "email": "abc@gmail.com",
                "code": "ABCD1200",
            },
            200,
            "Invite code: ABCD1200 already expired.",
            InvitationStatus.UNCONFIRMED,
        ),
        # Code already confirmed
        (
            {
                "email": "confirmed@gmail.com",
                "code": "CONFIRM01",
            },
            200,
            "Invite code: CONFIRM01 already confirmed.",
            InvitationStatus.CONFIRMED,
        ),
        # Code not in correct status (invalidated)
        (
            {
                "email": "invalid@gmail.com",
                "code": "INVALID01",
            },
            200,
            "Invite code: INVALID01 is invalidated.",
            InvitationStatus.INVALIDATED,
        ),
        # Invitation confirmed!
        (
            {
                "email": "abc@gmail.com",
                "code": "ABCD1234",
            },
            200,
            "Invitate code: ABCD1234 status changed to confirmed.",
            InvitationStatus.CONFIRMED,
        ),
    ],
)
def test_confirm_invitation(
    table_with_items,
    request_body: dict,
    status_code: int,
    message: str,
    invite_status: InvitationStatus,
):
    resp = confirm_invitation(table_with_items, request_body)
    assert resp["statusCode"] == status_code

    body = json.loads(resp["body"])
    assert body["message"] == message

    if invite_status is not None:
        assert body["data"]["invite_status"] == invite_status


# def test_invalid_http_method():
#     ...
