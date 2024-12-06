import json
import os
import traceback

import boto3

from helpers.controllers import (
    review_all_invitations,
    create_new_invitation,
    confirm_invitation,
    invalidate_invitation,
)
from helpers.utils import build_response

TABLE_NAME = os.environ["TABLE_NAME"]


def handler(event, context):
    print(event)
    print(context)

    try:
        res_ctx = event["requestContext"]["http"]
    except KeyError as e:
        print(
            f'Failed to get request context from event["requestContext"]["http"]. Err: {e}'
        )

    http_method = res_ctx["method"]
    # http_path = res_ctx["path"]

    query_params = event.get("queryStringParameters", {})
    request_body = json.loads(event.get("body", "{}"))

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(TABLE_NAME)

    try:
        if http_method == "GET":
            return review_all_invitations(table, query_params)

        if http_method == "POST":
            return create_new_invitation(table, request_body)

        if http_method == "PUT":
            return confirm_invitation(table, request_body)

        if http_method == "DELETE":
            return invalidate_invitation(table, request_body)

        raise NotImplementedError()

    except Exception as e:
        traceback.print_exc()

        message = f"Unknown error: {e}"
        print(message)

        return build_response(
            status_code=500,
            success=False,
            message=message,
        )
