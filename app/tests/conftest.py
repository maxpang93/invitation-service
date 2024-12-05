from datetime import datetime, timezone, timedelta
import os

import boto3
import pytest
import moto
from dotenv import load_dotenv

from lambdas.invitation.helpers.utils import generate_invitation, generate_code
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


@pytest.fixture
def table_with_many_items(create_table):
    """
    Tune numbers to ~10k to test
    - pagination limit: able to get all items via multiple queries
    - long execution time: > 30s
    - possible API Gateway timeout: (see https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html#http-api-quotas)
    """
    UNCONFIRMED_BUT_EXPIRED_COUNT = 100
    NEW_UNCONFIRMED_COUNT = 50
    EXPIRED_COUNT = 50
    CONFIRMED_COUNT = 50
    INVALIDATED_COUNT = 50

    # status 'unconfirmed' but expired invitations
    for _ in range(UNCONFIRMED_BUT_EXPIRED_COUNT):
        create_expired_invitation(create_table)

    # new invitations
    for _ in range(NEW_UNCONFIRMED_COUNT):
        invitation = generate_invitation(
            email=generate_random_email(),
            code=generate_code(),
        )
        create_table.put_item(Item=invitation.__dict__)

    # status 'expired' invitations
    for _ in range(EXPIRED_COUNT):
        create_expired_invitation(create_table, InvitationStatus.EXPIRED)

    # other statuses
    for _ in range(CONFIRMED_COUNT):
        create_expired_invitation(create_table, InvitationStatus.CONFIRMED)

    for _ in range(INVALIDATED_COUNT):
        create_expired_invitation(create_table, InvitationStatus.INVALIDATED)

    # set env var for test functions use
    os.environ["UNCONFIRMED_BUT_EXPIRED_COUNT"] = str(UNCONFIRMED_BUT_EXPIRED_COUNT)
    os.environ["NEW_UNCONFIRMED_COUNT"] = str(NEW_UNCONFIRMED_COUNT)
    os.environ["EXPIRED_COUNT"] = str(EXPIRED_COUNT)
    os.environ["CONFIRMED_COUNT"] = str(CONFIRMED_COUNT)
    os.environ["INVALIDATED_COUNT"] = str(INVALIDATED_COUNT)

    yield create_table


def generate_random_email():
    return f"{generate_code(6)}@gmail.com"


def create_expired_invitation(create_table, invite_status: InvitationStatus = None):
    """Create invitations way past expiry_date"""
    invitation = generate_invitation(
        email=generate_random_email(),
        code=generate_code(),
        valid_days=-8,
    )
    if invite_status:
        invitation.invite_status = invite_status
    create_table.put_item(Item=invitation.__dict__)
