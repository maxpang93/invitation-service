import os
from datetime import datetime, timezone, timedelta

import boto3
import pytest
import moto
from dotenv import load_dotenv

from lambdas.invitation.helpers.utils import generate_invitation
from lambdas.invitation.helpers.schemas import Invitation, InvitationStatus


@pytest.fixture
def lambda_environment():
    load_dotenv()
    print(os.environ["TABLE_NAME"])
    print(os.environ["TABLE_GSI_NAME"])


@pytest.fixture
def create_table(lambda_environment):
    TABLE_NAME = os.environ["TABLE_NAME"]
    TABLE_GSI_NAME = os.environ["TABLE_GSI_NAME"]

    with moto.mock_dynamodb():
        client = boto3.client("dynamodb")
        client.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {"AttributeName": "email", "KeyType": "HASH"},
                {"AttributeName": "code", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "email", "AttributeType": "S"},
                {"AttributeName": "code", "AttributeType": "S"},
                {"AttributeName": "invite_status", "AttributeType": "S"},
                {"AttributeName": "expiry_date", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
            GlobalSecondaryIndexes=[
                {
                    "IndexName": TABLE_GSI_NAME,
                    "KeySchema": [
                        {"AttributeName": "invite_status", "KeyType": "HASH"},
                        {"AttributeName": "expiry_date", "KeyType": "RANGE"},
                    ],
                    "Projection": {
                        "ProjectionType": "ALL",
                    },
                }
            ],
        )

        yield boto3.resource("dynamodb").Table(TABLE_NAME)


@pytest.fixture
def empty_table(create_table):
    yield create_table


@pytest.fixture
def table_with_items(create_table):
    # newly created invitations
    new_invitations = [
        ("abc@gmail.com", "ABCD1234"),
        ("def@yahoo.com", "DEFG5678"),
    ]
    new_invitations = [
        generate_invitation(x[0], x[1]).__dict__ for x in new_invitations
    ]

    # existing invitations with various statuses
    def create_invitation_with_status(x: tuple):
        invitation = generate_invitation(x[0], x[1])
        invitation.invite_status = x[2]

        # artificially put expired datetime
        if x[2] == InvitationStatus.EXPIRED:
            invitation.expiry_date = generate_expiry_date()

        return invitation.__dict__

    existing_invitations = [
        ("invalid@gmail.com", "INVALID01", InvitationStatus.INVALIDATED),
        ("confirmed@gmail.com", "CONFIRM01", InvitationStatus.CONFIRMED),
        ("expired@gmail.com", "EXPIRED01", InvitationStatus.EXPIRED),
    ]
    existing_invitations = [
        create_invitation_with_status(x) for x in existing_invitations
    ]

    for invitation in new_invitations + existing_invitations:
        create_table.put_item(Item=invitation)

    # expired invitation but status still "unconfirmed"
    # old invite from same email above
    unconverted = generate_invitation("abc@gmail.com", "ABCD1200", -8)
    create_table.put_item(Item=unconverted.__dict__)

    yield create_table


def generate_expiry_date(days_before_now: int = 8) -> str:
    """
    Get datetime x days before now to simulate expired date.
    return datetime string of format: YYYY-MM-DDTHH:mm:ssZ
    """
    expired_date = datetime.now(timezone.utc) - timedelta(days=days_before_now)
    return expired_date.strftime("%Y-%m-%dT%H:%M:%SZ")
