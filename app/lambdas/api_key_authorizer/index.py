import os

ADMIN_API_KEY = os.environ["ADMIN_API_KEY"]


def handler(event, context):
    print(event)
    print(context)

    is_authorized = False
    if event["headers"]["authorization"] == ADMIN_API_KEY:
        is_authorized = True

    return {
        "isAuthorized": is_authorized,
    }
