import os

from aws_cdk import (
    Duration,
    Stack,
    aws_dynamodb as dynamodb_,
    aws_lambda as lambda_,
    aws_apigatewayv2 as apigw_,
    aws_events as events_,
    aws_events_targets as events_targets_,
)
from aws_cdk.aws_apigatewayv2_integrations import HttpLambdaIntegration
from aws_cdk.aws_apigatewayv2_authorizers import (
    HttpLambdaAuthorizer,
    HttpLambdaResponseType,
)
from constructs import Construct
from dotenv import load_dotenv

load_dotenv()
print(os.environ)


TABLE_NAME = os.environ["TABLE_NAME"]
TABLE_GSI_NAME = os.environ["TABLE_GSI_NAME"]
ADMIN_API_KEY = os.environ["ADMIN_API_KEY"]
CRON_DURATION_MINUTES = int(os.environ["CRON_DURATION_MINUTES"] or 60)


class AppStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Table to store invitation info
        # with Secondary GSI for fast query on invite_status
        invitation_table = dynamodb_.Table(
            self,
            id="InvitationTable",
            table_name=TABLE_NAME,
            partition_key=dynamodb_.Attribute(
                name="email",
                type=dynamodb_.AttributeType.STRING,
            ),
            sort_key=dynamodb_.Attribute(
                name="code",
                type=dynamodb_.AttributeType.STRING,
            ),
        )
        invitation_table.add_global_secondary_index(
            index_name=TABLE_GSI_NAME,
            partition_key=dynamodb_.Attribute(
                name="invite_status",
                type=dynamodb_.AttributeType.STRING,
            ),
            sort_key=dynamodb_.Attribute(
                name="expiry_date",
                type=dynamodb_.AttributeType.STRING,
            ),
        )

        # main Lambda for logical processing
        invitation_fn = lambda_.Function(
            self,
            id="InvitationFn",
            function_name="InvitationService",
            runtime=lambda_.Runtime.PYTHON_3_10,
            code=lambda_.Code.from_asset("lambdas/invitation"),
            handler="index.handler",
            memory_size=256,
            timeout=Duration.seconds(60),
            environment={
                "TABLE_NAME": TABLE_NAME,
                "TABLE_GSI_NAME": TABLE_GSI_NAME,
            },
        )
        invitation_table.grant_read_write_data(invitation_fn)

        # API gateway that integrates with Lambda above
        # routes to different endpoint based on HTTP method
        http_api = apigw_.HttpApi(
            self,
            id="InvitationAPIGateway",
        )
        invitation_integration = HttpLambdaIntegration(
            id="InvitationIntegration",
            handler=invitation_fn,
        )

        # custom Lambda authorizer for invitation endpoints
        api_key_authorizer_fn = lambda_.Function(
            self,
            id="ApiKeyAuthorizerFn",
            function_name="ApiKeyAuthorizer",
            runtime=lambda_.Runtime.PYTHON_3_10,
            code=lambda_.Code.from_asset("lambdas/api_key_authorizer"),
            handler="index.handler",
            memory_size=256,
            timeout=Duration.seconds(60),
            environment={
                "ADMIN_API_KEY": ADMIN_API_KEY,
            },
        )
        api_key_authorizer = HttpLambdaAuthorizer(
            id="ApiKeyAuthorizer",
            handler=api_key_authorizer_fn,
            response_types=[HttpLambdaResponseType.SIMPLE],
        )

        # public endpoints
        http_api.add_routes(
            path="/invitation",
            methods=[
                apigw_.HttpMethod.PUT,
            ],
            integration=invitation_integration,
        )

        # protected endpoints
        http_api.add_routes(
            path="/invitation",
            methods=[
                apigw_.HttpMethod.GET,
                apigw_.HttpMethod.POST,
                apigw_.HttpMethod.DELETE,
            ],
            integration=invitation_integration,
            authorizer=api_key_authorizer,
        )

        # cron job Lambda that converts expired invitation status
        scheduler_fn = lambda_.Function(
            self,
            id="InvitationCronFn",
            function_name="InvitationCronService",
            runtime=lambda_.Runtime.PYTHON_3_10,
            code=lambda_.Code.from_asset("lambdas/scheduler"),
            handler="index.handler",
            memory_size=256,
            timeout=Duration.seconds(60),
            environment={
                "TABLE_NAME": TABLE_NAME,
                "TABLE_GSI_NAME": TABLE_GSI_NAME,
            },
        )
        invitation_table.grant_read_write_data(scheduler_fn)
        rule = events_.Rule(
            self,
            "InvitationCronServiceRule",
            schedule=events_.Schedule.rate(
                duration=Duration.minutes(CRON_DURATION_MINUTES)
            ),
        )
        rule.add_target(target=events_targets_.LambdaFunction(scheduler_fn))
