# Deploying PATOS-Cloud to AWS

Everything below is run by **you**, in your terminal or the AWS Console. Never paste access keys,
passwords or tokens into a chat or commit them. Nothing is deployed and no cost is incurred until
step 6.

## 0. What you need
- An AWS account and a region you will use for this demo.
- Python 3.10+, Node.js 18+, AWS CLI v2, and the CDK CLI: `npm install -g aws-cdk`
- Permissions to bootstrap CDK and create IAM roles, Lambda, DynamoDB, IoT, Cognito and API Gateway
  (an administrator in a sandbox account is simplest).

## 1. Put a spend alarm in place first
Either create a budget in the Console (Billing > Budgets), or let this project create one at deploy
time with `-c budget_email=you@example.com` (default limit 20 USD/month; change with
`-c monthly_budget_usd=...`). Budgets **alert**; they do not stop spending.

## 2. Sign in without long-lived keys
**On a Free plan account, do NOT enable IAM Identity Center or AWS Organizations**: AWS upgrades the
account to the paid plan and the free credits expire. Use an IAM user with MFA and short-term
credentials from the CLI instead (see docs/HYBRID_DEPLOY.md, section 1):
```bash
aws login                    # sign in as your IAM user in the browser
aws sts get-caller-identity  # confirms which account you are about to use
```
(The full serverless stack below is optional; the smaller hybrid stack in docs/HYBRID_DEPLOY.md is the recommended demo.)

## 3. Set up and test locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt -r requirements-aws.txt
pytest
```
Do not continue if tests fail.

## 4. Bootstrap CDK (once per account/region)
```bash
cdk bootstrap
```
This creates a `CDKToolkit` stack (a staging S3 bucket, an image repository and IAM roles) that CDK
uses to deploy. It has small ongoing storage cost and is not removed by `cdk destroy`.

## 5. Review what will be created
```bash
cdk synth > /dev/null && cdk diff -c budget_email=you@example.com
```
Expect: 2 DynamoDB tables (on-demand, TTL), 2 Lambda functions (ARM, Python 3.12) with 1-week log
retention, 1 IoT topic rule, 1 Cognito user pool (self sign-up off) with groups `emergency_operator`
and `driver`, and a client, 1 REST API with a Cognito authorizer (throttled to 5 req/s), and optionally
a budget. IAM policies are limited to `dynamodb:PutItem`/`dynamodb:Scan`.

## 6. Deploy
```bash
cdk deploy -c budget_email=you@example.com
```
Approve the IAM changes when prompted. Note the outputs: `ApiUrl`, `UserPoolId`,
`UserPoolClientId`, `TelemetryTableName`.

## 7. Create users (in your own terminal; the password never leaves it)
```bash
export REGION=<region>; export POOL=<UserPoolId>
read -s -p "Choose a password (12+ chars, upper, lower, digit, symbol): " PW; echo

aws cognito-idp admin-create-user --region $REGION --user-pool-id $POOL \
  --username demo_driver --message-action SUPPRESS
aws cognito-idp admin-set-user-password --region $REGION --user-pool-id $POOL \
  --username demo_driver --password "$PW" --permanent
aws cognito-idp admin-add-user-to-group --region $REGION --user-pool-id $POOL \
  --username demo_driver --group-name driver

# optional second user who may receive emergency-priority recommendations
aws cognito-idp admin-create-user --region $REGION --user-pool-id $POOL \
  --username demo_operator --message-action SUPPRESS
aws cognito-idp admin-set-user-password --region $REGION --user-pool-id $POOL \
  --username demo_operator --password "$PW" --permanent
aws cognito-idp admin-add-user-to-group --region $REGION --user-pool-id $POOL \
  --username demo_operator --group-name emergency_operator
```

## 8. Send simulated sensor data
The simulator publishes through the IoT data plane with your CLI credentials (no device certificates).
The identity you use needs this policy (replace REGION and ACCOUNT_ID):
```json
{"Version":"2012-10-17","Statement":[
 {"Effect":"Allow","Action":"iot:DescribeEndpoint","Resource":"*"},
 {"Effect":"Allow","Action":"iot:Publish",
  "Resource":"arn:aws:iot:REGION:ACCOUNT_ID:topic/patos/telemetry/*"}]}
```
```bash
python simulator/sensor_sim.py --region $REGION --rounds 3 --interval 5
```
Check it arrived:
```bash
aws dynamodb scan --region $REGION --table-name <TelemetryTableName> --max-items 3
```
If the table is empty, open CloudWatch Logs for the `IngestFn` log group, and check the IoT rule
in the Console. Telemetry older than 5 minutes is ignored by the router, so re-run the simulator
shortly before requesting routes.

## 9. Get a route
```bash
python client/get_route.py --region $REGION --client-id <UserPoolClientId> \
  --api-url <ApiUrl> --username demo_driver --from N_0_0 --to N_5_5 --vehicle CAR \
  --html route.html
```
It prompts for the password (or reads `PATOS_PASSWORD`). Open `route.html` for a simple map. Repeat
as `demo_operator` with `--vehicle AMBULANCE` to see priority recommendations. The API expects the
Cognito **ID token** in the `Authorization` header (the client does this).

## 10. Costs
All services are pay-per-use (API Gateway requests, Lambda invocations, DynamoDB on-demand reads and
writes, IoT messages, CloudWatch logs, Cognito active users). At demo volumes this should be small,
but I have not priced it for your region or account; check the current AWS pricing pages and your
free-tier eligibility. Do not leave the simulator running in a loop.

## 11. Tear down
```bash
cdk destroy
```
Tables, logs and the user pool are set to be deleted with the stack (demo setting). Then confirm in
the Console that no `PatosRoutingDemo` stack, tables, or Cognito pool remain, delete any budget you
created manually, and remove the `CDKToolkit` stack and its S3 bucket (empty it first) if you do not
use CDK for anything else.

## Security notes (demo-level choices to revisit before any real use)
- Cognito `USER_PASSWORD_AUTH` and MFA off keep the CLI simple; use SRP or the hosted UI and enable MFA.
- No WAF, custom domain or per-user quotas; throttling is a single stage-wide limit.
- The router `Scan`s the 16-row telemetry table; use queries/caching if the graph grows.
- Priority recommendations are advisory and audited, but are not a substitute for the traffic
  authority's own authorization and systems.
