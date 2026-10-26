"""Minimal AWS stack for the hybrid demo: Lambda + DynamoDB only (plus the log group Lambda needs).

The local app does the routing; this stack stores audit records and validated sensor readings.
Tables use PROVISIONED capacity small enough to stay inside the always-free allowance
(25 read / 25 write units across all tables); on-demand tables are not covered by it.
"""
from pathlib import Path

from aws_cdk import (
    CfnOutput, Duration, RemovalPolicy, Stack, Tags,
    aws_dynamodb as ddb, aws_lambda as _lambda, aws_logs as logs,
)
from constructs import Construct

SRC = Path(__file__).resolve().parents[1] / "src"


class PatosHybridStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("project", "patos-hybrid-demo")

        def table(name: str, key: str, rcu: int, wcu: int) -> ddb.Table:
            return ddb.Table(
                self, name,
                partition_key=ddb.Attribute(name=key, type=ddb.AttributeType.STRING),
                billing_mode=ddb.BillingMode.PROVISIONED, read_capacity=rcu, write_capacity=wcu,
                time_to_live_attribute="ttl", removal_policy=RemovalPolicy.DESTROY,
            )

        telemetry = table("TelemetryTable", "intersection_id", rcu=1, wcu=8)
        audit = table("AuditTable", "request_id", rcu=1, wcu=2)

        fn = _lambda.Function(
            self, "IngestBatchFn",
            runtime=_lambda.Runtime.PYTHON_3_12, architecture=_lambda.Architecture.ARM_64,
            handler="handlers.ingest_batch.handler",
            code=_lambda.Code.from_asset(str(SRC), exclude=["**/__pycache__", "*.pyc"]),
            memory_size=128, timeout=Duration.seconds(10),
            environment={"TELEMETRY_TABLE": telemetry.table_name},
            log_group=logs.LogGroup(self, "IngestBatchLogs", retention=logs.RetentionDays.ONE_DAY,
                                    removal_policy=RemovalPolicy.DESTROY),
        )
        telemetry.grant(fn, "dynamodb:PutItem")  # the only permission the function needs

        CfnOutput(self, "AuditTableName", value=audit.table_name)
        CfnOutput(self, "TelemetryTableName", value=telemetry.table_name)
        CfnOutput(self, "IngestFunctionName", value=fn.function_name)
