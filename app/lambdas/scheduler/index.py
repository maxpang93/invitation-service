import os

import boto3

from helpers.controllers import process_expired_unconfirmed_invitations

TABLE_NAME = os.environ["TABLE_NAME"]
TABLE_GSI_NAME = os.environ["TABLE_GSI_NAME"]


def handler(event, context):
    print(event)
    print(context)

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    process_expired_unconfirmed_invitations(
        table=table,
        gsi_name=TABLE_GSI_NAME,
    )
