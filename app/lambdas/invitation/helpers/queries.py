from typing import Union

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .schemas import Invitation


# TODO table type hinting


def get_all(table) -> list[Invitation]:
    data = []
    done = False
    start_key = None
    scan_kwargs = {}
    try:
        while not done:
            if start_key:
                scan_kwargs["ExclusiveStartKey"] = start_key
            response = table.scan(**scan_kwargs)
            data.extend(response.get("Items", []))
            start_key = response.get("LastEvaluatedKey", None)
            done = start_key is None

        return data

    except ClientError as e:
        print(f"Failed to scan table. Err: {e}")


def query(table, email: str, code: str = None) -> list[Invitation]:
    data = []
    start_key = None
    try:
        expr = Key("email").eq(email)
        if code is not None:
            expr &= Key("code").eq(code)

        resp = table.query(
            KeyConditionExpression=expr,
        )
        data.extend(resp["Items"])
        start_key = resp.get("LastEvaluatedKey")

        while start_key:
            resp = table.query(
                KeyConditionExpression=expr,
                ExclusiveStartKey=start_key,
            )
            data.extend(resp["Items"])
            start_key = resp.get("LastEvaluatedKey")

        return data

    except ClientError as e:
        print(f"Failed to query table. Err: {e}")


def query_by_gsi(table, gsi_name: str, invite_status: str) -> list[Invitation]:
    data = []
    start_key = None
    try:
        expr = Key("invite_status").eq(invite_status)
        resp = table.query(
            IndexName=gsi_name,
            KeyConditionExpression=expr,
        )
        data.extend(resp["Items"])
        start_key = resp.get("LastEvaluatedKey")

        while start_key:
            resp = table.query(
                IndexName=gsi_name,
                KeyConditionExpression=expr,
                ExclusiveStartKey=start_key,
            )
            data.extend(resp["Items"])
            start_key = resp.get("LastEvaluatedKey")

        return data

    except ClientError as e:
        print(f"Failed to query table. Err: {e}")


def update(table, email: str, code: str, payload: dict) -> Union[None, Invitation]:
    update_expr, expr_attr_value = __generate_update_expr(payload)

    try:
        resp = table.update_item(
            Key={"email": email, "code": code},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_attr_value,
            ReturnValues="ALL_NEW",
            ConditionExpression="attribute_exists(email) AND attribute_exists(code)",
        )
        #  TODO convert to `Invitation`?
        return resp["Attributes"]

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print(f"Item with {email=} and {code=} does not exist.")
            return None
        else:
            print(f"Failed to update table item. Err: {e}")


def create(table, payload: Invitation):
    try:
        resp = table.put_item(
            Item=payload.__dict__,
            ReturnValues="NONE",
        )
        return resp["ResponseMetadata"]["HTTPStatusCode"] == 200

    except ClientError as e:
        print(f"Failed to create new table item. Err: {e}")


def __generate_update_expr(payload: dict):
    """
    Given key-value pairs, generate UpdateExpression
    and ExpressionAttributeValues for DynamoDB update_item
    """
    update_expr_list = []
    expr_attr_value = {}
    for k, v in payload.items():
        update_expr_list.append(f"{k}=:{k}")
        expr_attr_value[f":{k}"] = v
    update_expr = "SET " + ", ".join(update_expr_list)
    return update_expr, expr_attr_value
