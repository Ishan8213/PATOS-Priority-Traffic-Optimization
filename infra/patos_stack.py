from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    Tags,
    aws_apigateway as apigw,
    aws_budgets as budgets,
    aws_cognito as cognito,
    aws_dynamodb as ddb,
    aws_iam as iam,
    aws_iot as iot,
    aws_lambda as _lambda,
    aws_logs as logs,
)
from constructs import Construct

SRC = Path(__file__).resolve().parents[1] / "src"
TELEMETRY_TOPIC_FILTER = "patos/telemetry/+"


class PatosStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("project", "patos-routing-demo")

        # ---------------- Data ----------------
        telemetry = ddb.Table(
            self, "TelemetryTable",
            partition_key=ddb.Attribute(name="intersection_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,  # demo: deleted with the stack
        )
        audit = ddb.Table(
            self, "AuditTable",
            partition_key=ddb.Attribute(name="request_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ---------------- Lambdas ----------------
        def make_fn(name: str, handler: str, timeout_s: int, env: dict) -> _lambda.Function:
            return _lambda.Function(
                self, name,
                runtime=_lambda.Runtime.PYTHON_3_12,
                architecture=_lambda.Architecture.ARM_64,
                handler=handler,
                code=_lambda.Code.from_asset(str(SRC), exclude=["**/__pycache__", "*.pyc"]),
                memory_size=256,
                timeout=Duration.seconds(timeout_s),
                environment=env,
                log_group=logs.LogGroup(
                    self, f"{name}Logs",
                    retention=logs.RetentionDays.ONE_WEEK,
                    removal_policy=RemovalPolicy.DESTROY,
                ),
            )

        ingest_fn = make_fn("IngestFn", "handlers.ingest.handler", 10,
                            {"TELEMETRY_TABLE": telemetry.table_name})
        route_fn = make_fn("RouteFn", "handlers.route.handler", 10,
                           {"TELEMETRY_TABLE": telemetry.table_name,
                            "AUDIT_TABLE": audit.table_name,
                            "STALE_AFTER_S": "300"})

        # Least privilege: only the specific actions each function needs.
        telemetry.grant(ingest_fn, "dynamodb:PutItem")
        telemetry.grant(route_fn, "dynamodb:Scan")
        audit.grant(route_fn, "dynamodb:PutItem")

        # ---------------- IoT Core -> ingest ----------------
        rule = iot.CfnTopicRule(
            self, "TelemetryRule",
            topic_rule_payload=iot.CfnTopicRule.TopicRulePayloadProperty(
                sql=f"SELECT *, topic(3) AS topic_intersection FROM '{TELEMETRY_TOPIC_FILTER}'",
                aws_iot_sql_version="2016-03-23",
                rule_disabled=False,
                actions=[iot.CfnTopicRule.ActionProperty(
                    lambda_=iot.CfnTopicRule.LambdaActionProperty(function_arn=ingest_fn.function_arn))],
            ),
        )
        ingest_fn.add_permission(
            "AllowIotRuleInvoke",
            principal=iam.ServicePrincipal("iot.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=rule.attr_arn,
            source_account=self.account,
        )

        # ---------------- Auth ----------------
        pool = cognito.UserPool(
            self, "UserPool",
            self_sign_up_enabled=False,  # accounts are created by an administrator
            sign_in_aliases=cognito.SignInAliases(username=True),
            password_policy=cognito.PasswordPolicy(
                min_length=12, require_lowercase=True, require_uppercase=True,
                require_digits=True, require_symbols=True),
            mfa=cognito.Mfa.OFF,  # demo only; enable MFA for anything beyond a demo
            account_recovery=cognito.AccountRecovery.NONE,
            removal_policy=RemovalPolicy.DESTROY,
        )
        for group in ("emergency_operator", "driver"):
            cognito.CfnUserPoolGroup(self, f"Group-{group}", user_pool_id=pool.user_pool_id,
                                     group_name=group)
        client = pool.add_client(
            "CliClient",
            generate_secret=False,
            auth_flows=cognito.AuthFlow(user_password=True),  # demo CLI; prefer SRP/hosted UI later
            id_token_validity=Duration.hours(1),
            access_token_validity=Duration.hours(1),
            prevent_user_existence_errors=True,
        )

        # ---------------- API ----------------
        api = apigw.RestApi(
            self, "Api",
            rest_api_name="patos-routing-demo",
            endpoint_types=[apigw.EndpointType.REGIONAL],
            cloud_watch_role=False,  # avoid changing an account-wide API Gateway logging setting
            deploy_options=apigw.StageOptions(
                stage_name="demo",
                throttling_rate_limit=5,    # requests/second, protects cost
                throttling_burst_limit=10,
                metrics_enabled=True,
            ),
        )
        authorizer = apigw.CognitoUserPoolsAuthorizer(self, "Authorizer", cognito_user_pools=[pool])
        api.root.add_resource("route").add_method(
            "POST",
            apigw.LambdaIntegration(route_fn),
            authorizer=authorizer,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # ---------------- Optional budget alert ----------------
        email = self.node.try_get_context("budget_email")
        if email:
            limit = float(self.node.try_get_context("monthly_budget_usd") or 20)
            budgets.CfnBudget(
                self, "MonthlyBudget",
                budget=budgets.CfnBudget.BudgetDataProperty(
                    budget_type="COST", time_unit="MONTHLY",
                    budget_limit=budgets.CfnBudget.SpendProperty(amount=limit, unit="USD")),
                notifications_with_subscribers=[
                    budgets.CfnBudget.NotificationWithSubscribersProperty(
                        notification=budgets.CfnBudget.NotificationProperty(
                            notification_type="ACTUAL", comparison_operator="GREATER_THAN",
                            threshold=80, threshold_type="PERCENTAGE"),
                        subscribers=[budgets.CfnBudget.SubscriberProperty(
                            subscription_type="EMAIL", address=email)])],
            )

        CfnOutput(self, "ApiUrl", value=api.url)
        CfnOutput(self, "UserPoolId", value=pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=client.user_pool_client_id)
        CfnOutput(self, "TelemetryTopicFilter", value=TELEMETRY_TOPIC_FILTER)
        CfnOutput(self, "TelemetryTableName", value=telemetry.table_name)
        CfnOutput(self, "AuditTableName", value=audit.table_name)
