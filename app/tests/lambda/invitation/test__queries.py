import os

import pytest

from lambdas.invitation.queries import (
    get_all,
    create,
    update,
    query,
    query_by_gsi,
)
from lambdas.invitation.utils import (
    generate_invitation,
    generate_code,
)
from lambdas.invitation.schemas import InvitationStatus


def test_get_all_from_empty_table(empty_table):
    data = get_all(empty_table)
    assert len(data) == 0


def test_get_all_from_table(table_with_items):
    data = get_all(table_with_items)
    assert len(data) == 6


@pytest.mark.parametrize(
    "invite_status, items_found",
    [
        ("unconfirmed", 3),
        ("confirmed", 1),
        ("invalidated", 1),
        ("expired", 1),
    ],
)
def test_query_by_status(
    table_with_items,
    invite_status: InvitationStatus,
    items_found: int,
):
    gsi_name = os.environ["TABLE_GSI_NAME"]
    data = query_by_gsi(table_with_items, gsi_name, invite_status)
    print(data)
    assert len(data) == items_found


# TODO validate email, resp is False if invalid email
def test_create(empty_table):
    code = generate_code()
    email = "peter88@gmail.com"

    invitation = generate_invitation(email, code)
    resp = create(empty_table, invitation)

    assert resp is not None
    assert resp is True


def test_update_success(table_with_items):
    email = "abc@gmail.com"
    code = "ABCD1234"
    data = update(
        table=table_with_items,
        email=email,
        code=code,
        payload={
            "invite_status": InvitationStatus.CONFIRMED,
        },
    )
    assert data is not None
    assert data["email"] == email
    assert data["code"] == code
    assert data["invite_status"] == InvitationStatus.CONFIRMED


def test_update_failed(table_with_items):
    data = update(
        table=table_with_items,
        email="def@gmail.com",
        code="ABCD1234",  # wrong code
        payload={
            "invite_status": InvitationStatus.CONFIRMED,
        },
    )
    assert data is None


def test_query_empty_table(empty_table):
    data = query(empty_table, "ABCD1234")
    assert isinstance(data, list)
    assert len(data) == 0


def test_query(table_with_items):
    data = query(table_with_items, "abc@gmail.com")
    assert isinstance(data, list)
    assert len(data) == 2
    # proper sorting (`code` is sort key)
    assert data[0]["code"] == "ABCD1200"
    assert data[1]["code"] == "ABCD1234"
