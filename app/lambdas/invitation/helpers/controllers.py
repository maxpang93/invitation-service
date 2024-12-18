from datetime import datetime, timezone
import os
import traceback

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
    build_response,
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
            if email or code:
                data = [
                    d
                    for d in data
                    if (d["email"] == email if email else True)
                    and (d["code"] == code if code else True)
                ]
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
        create_sucess = create(table, data)
        message = "Invitation created!"
        print(message)

        return build_response(
            status_code=200,
            success=create_sucess,
            message=message,
            data=data.__dict__,
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


def invalidate_invitation(table, request_body: dict):
    print(f"{request_body=}")

    return build_response(
        status_code=200,
        success=True,
        message="Not implemented.",
    )
