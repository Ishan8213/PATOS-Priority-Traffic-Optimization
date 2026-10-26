import pytest

pytest.importorskip("aws_cdk", reason="AWS CDK not installed (only needed for AWS deployment)")

import aws_cdk as cdk  # noqa: E402
from aws_cdk.assertions import Match, Template  # noqa: E402

from infra.patos_stack import PatosStack  # noqa: E402


def synth(context=None):
    app = cdk.App(context=context or {})
    return Template.from_stack(PatosStack(app, "T"))


def test_core_resources_exist():
    t = synth()
    t.resource_count_is("AWS::DynamoDB::Table", 2)
    t.resource_count_is("AWS::Lambda::Function", 2)
    t.resource_count_is("AWS::IoT::TopicRule", 1)
    t.resource_count_is("AWS::Cognito::UserPool", 1)
    t.resource_count_is("AWS::ApiGateway::RestApi", 1)


def test_api_method_requires_cognito():
    t = synth()
    t.has_resource_properties("AWS::ApiGateway::Method", {"HttpMethod": "POST", "AuthorizationType": "COGNITO_USER_POOLS"})


def test_signups_are_disabled():
    t = synth()
    t.has_resource_properties("AWS::Cognito::UserPool",
                              {"AdminCreateUserConfig": {"AllowAdminCreateUserOnly": True}})


def test_tables_are_on_demand_with_ttl():
    t = synth()
    t.has_resource_properties("AWS::DynamoDB::Table", {
        "BillingMode": "PAY_PER_REQUEST",
        "TimeToLiveSpecification": {"AttributeName": "ttl", "Enabled": True}})


def test_lambda_policies_are_scoped_to_specific_actions():
    t = synth()
    policies = t.find_resources("AWS::IAM::Policy")
    actions = set()
    for p in policies.values():
        for st in p["Properties"]["PolicyDocument"]["Statement"]:
            a = st["Action"]
            actions.update([a] if isinstance(a, str) else a)
    assert {"dynamodb:PutItem", "dynamodb:Scan"} <= actions
    assert not any(a == "*" or a.endswith(":*") for a in actions)


def test_iot_rule_may_invoke_only_from_that_rule():
    t = synth()
    t.has_resource_properties("AWS::Lambda::Permission", {
        "Principal": "iot.amazonaws.com", "SourceArn": Match.any_value(), "SourceAccount": Match.any_value()})


def test_budget_only_created_when_email_given():
    synth().resource_count_is("AWS::Budgets::Budget", 0)
    synth({"budget_email": "someone@example.com"}).resource_count_is("AWS::Budgets::Budget", 1)


def test_no_account_wide_api_gateway_setting_is_changed():
    synth().resource_count_is("AWS::ApiGateway::Account", 0)
