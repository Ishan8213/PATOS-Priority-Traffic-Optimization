import pytest

pytest.importorskip("aws_cdk", reason="AWS CDK not installed (only needed for AWS deployment)")

import aws_cdk as cdk  # noqa: E402
from aws_cdk.assertions import Template  # noqa: E402

from infra.hybrid_stack import PatosHybridStack  # noqa: E402


@pytest.fixture(scope="module")
def t():
    return Template.from_stack(PatosHybridStack(cdk.App(), "H"))


def test_only_lambda_and_dynamodb(t):
    t.resource_count_is("AWS::Lambda::Function", 1)
    t.resource_count_is("AWS::DynamoDB::Table", 2)
    for absent in ("AWS::ApiGateway::RestApi", "AWS::Cognito::UserPool", "AWS::IoT::TopicRule", "AWS::S3::Bucket"):
        t.resource_count_is(absent, 0)


def test_tables_are_provisioned_within_free_allowance(t):
    tables = t.find_resources("AWS::DynamoDB::Table").values()
    rcu = sum(x["Properties"]["ProvisionedThroughput"]["ReadCapacityUnits"] for x in tables)
    wcu = sum(x["Properties"]["ProvisionedThroughput"]["WriteCapacityUnits"] for x in tables)
    assert rcu <= 25 and wcu <= 25
    assert all("BillingMode" not in x["Properties"] or x["Properties"]["BillingMode"] != "PAY_PER_REQUEST" for x in tables)


def test_lambda_may_only_put_items(t):
    actions = set()
    for p in t.find_resources("AWS::IAM::Policy").values():
        for st in p["Properties"]["PolicyDocument"]["Statement"]:
            a = st["Action"]
            actions.update([a] if isinstance(a, str) else a)
    assert actions == {"dynamodb:PutItem"}


def test_everything_is_deleted_with_the_stack(t):
    for r in list(t.find_resources("AWS::DynamoDB::Table").values()) + list(t.find_resources("AWS::Logs::LogGroup").values()):
        assert r["DeletionPolicy"] == "Delete"


def test_outputs_needed_by_the_local_app(t):
    outs = t.to_json()["Outputs"]
    assert {"AuditTableName", "IngestFunctionName", "TelemetryTableName"} <= set(outs)
