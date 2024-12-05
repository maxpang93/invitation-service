from typing import Union, Generator

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .schemas import Invitation


# TODO table type hinting


def query_by_gsi(
    table,
    gsi_name: str,
    invite_status: str,
) -> Generator[Invitation, None, None]:
    start_key = None
    try:
        expr = Key("invite_status").eq(invite_status)
        resp = table.query(
            IndexName=gsi_name,
            KeyConditionExpression=expr,
        )
        yield resp["Items"]
        start_key = resp.get("LastEvaluatedKey")

        while start_key:
            resp = table.query(
                IndexName=gsi_name,
                KeyConditionExpression=expr,
                ExclusiveStartKey=start_key,
            )
            yield resp["Items"]
            start_key = resp.get("LastEvaluatedKey")

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
