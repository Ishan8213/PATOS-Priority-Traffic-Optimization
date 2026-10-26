#!/usr/bin/env python3
import aws_cdk as cdk

from infra.hybrid_stack import PatosHybridStack
from infra.patos_stack import PatosStack

app = cdk.App()
# No account/region is hardcoded: CDK uses the ones from your AWS CLI profile at deploy time.
# Deploy ONE of them by name, e.g.  cdk deploy PatosHybridDemo
PatosHybridStack(app, "PatosHybridDemo")   # Lambda + DynamoDB only (used with run_local.py --aws)
PatosStack(app, "PatosRoutingDemo")        # full serverless version (API Gateway, Cognito, IoT Core)
app.synth()
