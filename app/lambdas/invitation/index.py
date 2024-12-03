import json
import os
from datetime import datetime, timezone
import traceback
from typing import Any

import boto3

from .schemas import (
    Invitation,
    InvitationStatus,
)
from .queries import (
    get_all,
    query,
    query_by_gsi,
    update,
    create,
)
from .utils import (
    generate_code,
    generate_invitation,
)


TABLE_NAME = os.environ["TABLE_NAME"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


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


def review_all_invitations(table, query_params: dict):
    print(f"{query_params=}")
    invite_status = query_params.get("invite_status")
    email = query_params.get("email")
    code = query_params.get("code")

    try:
        if invite_status is not None:
            # fast query by invite status
            data = query_by_gsi(
                table=table,
                gsi_name=os.environ["TABLE_GSI_NAME"],
                invite_status=invite_status,
            )
            if email is not None:
                data = [d for d in data if d["email"] == email]
        elif email is not None:
            # if email is supplied, but no filter by invite_status
            data = query(
                table=table,
                email=email,
                code=code,
            )
        else:
            # slow scan-all if neither invite_status nor email is given
            data = get_all(table)

        return build_response(
            status_code=200,
            success=True,
            message=None,
            data=data,
        )

    except Exception as e:
        traceback.print_exc()

        message = f"Error querying invitations. Err: {e}"
        print(message)

        return build_response(
            status_code=500,
            success=False,
            message=message,
        )


def create_new_invitation(table, request_body: dict):
    print(f"{request_body=}")

    if "email" not in request_body:
        message = f"Missing email."
        return build_response(
            status_code=422,
            success=False,
            message=message,
        )

    # TODO email validation
    email = request_body["email"]
    data = generate_invitation(
        email=email,
        code=generate_code(),
    )
    print(f"new invitation data={data}")

    try:
        new_invitation = create(table, data)
        message = "Invitation created!"
        print(message)

        return build_response(
            status_code=200,
            success=True,
            message=message,
            data=new_invitation,
        )

    except Exception as e:
        traceback.print_exc()

        message = f"Error generating invitation. Err: {e}"
        print(message)

        return build_response(
            status_code=500,
            success=False,
            message=message,
            data=None,
        )


def confirm_invitation(table, request_body: dict):
    print(f"{request_body=}")

    try:
        code = request_body["code"]
        email = request_body["email"]
    except KeyError as e:
        message = "Missing 'code' or 'email'."
        return build_response(
            status_code=422,
            success=False,
            message=message,
        )

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status_code = 200

    try:
        data = query(table, email, code)
        invitation = Invitation(**data[0]) if len(data) > 0 else None
        if invitation is None or invitation.email != email:
            message = f"Invite code: {code} is invalid or does not exist."
            status_code = 404

        elif (
            invitation.expiry_date < now_utc
            or invitation.invite_status == InvitationStatus.EXPIRED
        ):
            message = f"Invite code: {code} already expired."

        elif invitation.invite_status == InvitationStatus.CONFIRMED:
            message = f"Invite code: {code} already confirmed."

        elif invitation.invite_status == InvitationStatus.INVALIDATED:
            message = f"Invite code: {code} is invalidated."

        elif invitation.invite_status == InvitationStatus.EXPIRED:
            message = f"Invite code: {code} already status."

        else:
            payload = {"invite_status": InvitationStatus.CONFIRMED}
            invitation = update(
                table=table,
                email=email,
                code=code,
                payload=payload,
            )
            message = f"Invitate code: {code} status changed to confirmed."

        if isinstance(invitation, Invitation):
            invitation = invitation.__dict__

        print(message)
        print(invitation)

        return build_response(
            status_code=status_code,
            success=True,
            message=message,
            data=invitation,
        )

    except Exception as e:
        traceback.print_exc()

        message = f"Error confirming invitation. Err: {e}"
        print(message)

        return build_response(
            status_code=500,
            success=False,
            message=message,
        )


def invalidate_invitation(request_body: dict):
    print(f"{request_body=}")

    return build_response(
        status_code=200,
        success=True,
        message="Not implemented.",
    )
