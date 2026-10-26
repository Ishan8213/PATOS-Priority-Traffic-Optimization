# Hybrid AWS demo (Lambda + DynamoDB only) – deploy, use, and fully tear down

The app keeps running on your PC. With `--aws`, it also (1) writes every audit record to DynamoDB and
(2) sends the latest sensor readings to a Lambda function that validates and stores them.
If AWS is unreachable the local app keeps working and shows the error in the "AWS sync" line.

You run every command below yourself. Never paste passwords, access keys or tokens into a chat or
commit them.

## 0. Free-plan warning
Do **not** enable IAM Identity Center, create an AWS Organization, or set up Control Tower on a Free
plan account. AWS documents that creating an organization upgrades the account to the paid plan and
your free credits expire immediately.

## 1. One-time account preparation (Console)
1. Sign in as root and add **MFA** (account menu > Security credentials). Then stop using root.
2. Pick **one region** (top-right selector) and use it for everything.
3. Billing and Cost Management > Billing preferences: turn on **Free Tier alerts** (your email).
4. IAM > Users > Create user `patos-dev`, with console access (set the password in the console),
   attach `AdministratorAccess` (personal throw-away account; CDK must create roles), and add MFA.
5. On your PC (PowerShell) check: `aws --version` (2.32.0+), `node --version` (18+), `cdk --version`
   (install with `npm install -g aws-cdk` if missing).
6. `aws login` → choose your region → sign in as `patos-dev` in the browser. Then
   `aws sts get-caller-identity` should show your account and `patos-dev`.

## 2. Deploy
```powershell
python -m pip install -r requirements-aws.txt
python -m pytest                       # expect all tests to pass
cdk bootstrap                          # first time in this account + region only
cdk diff PatosHybridDemo               # review: 2 DynamoDB tables, 1 Lambda, its role and log group
cdk deploy PatosHybridDemo             # answer y when asked about IAM changes
```
Deployment creates: two DynamoDB tables (provisioned 1/8 and 1/2 read/write units, TTL on), one
Lambda function (`handlers.ingest_batch`) allowed only `dynamodb:PutItem` on the telemetry table, and
a one-day log group. Outputs: `AuditTableName`, `TelemetryTableName`, `IngestFunctionName`.

If `cdk` cannot find credentials after `aws login`, copy the exact error and ask for the
`credential_process` fallback.

## 3. Run the local app with AWS sync
```powershell
python run_local.py --aws PatosHybridDemo --region <your-region>
```
The terminal prints "AWS sync ON". In the page, the Live sensors card shows
"AWS sync ON (<region>): audit records sent N · sensor batches K/120". Find a few routes, including an
AMBULANCE as `emergency_operator`. Safety caps: sensor data is uploaded at most every 15 s and stops
after 120 batches (about 30 minutes; restart the app to resume); change with `--aws-interval` and
`--aws-max-batches`.

## 4. Evidence to capture for the review (Console, same region)
- CloudFormation > `PatosHybridDemo`: status CREATE_COMPLETE, Resources tab.
- DynamoDB > Tables > AuditTable > Explore items: your route requests (vehicle, role, ETA, priority).
- DynamoDB > TelemetryTable > Explore items: latest counts per intersection.
- Lambda > the IngestBatch function > Monitor: invocations. CloudWatch > Log groups: its log.
- The local page showing the "AWS sync ON" line, and Billing home showing Free plan credits.

## 5. Teardown (do it in this order, tomorrow night)
1. Stop the local app (Ctrl+C in its terminal).
2. `cdk destroy PatosHybridDemo` (answer y). In CloudFormation confirm the stack is gone.
3. CDK bootstrap leftovers: CloudFormation > delete the `CDKToolkit` stack. Then in **S3** and **ECR**
   look for names starting with `cdk-`: empty and delete any bucket, delete any repository that remains.
4. Confirm empty in the Console (same region): CloudFormation (no stacks), DynamoDB (no tables),
   Lambda (no functions), CloudWatch > Log groups (none for this project), S3, ECR.
5. IAM > Users > delete `patos-dev` (and its MFA device). Run `aws logout` on your PC.
6. Check Billing the next day and again after 2–3 days (cost data can lag). Credits remaining should
   barely move. The Free plan itself ends on its own date or when credits run out.
7. Optional: close the AWS account entirely (Billing > Account). That is permanent; read AWS's
   confirmation screen first.

## 6. Troubleshooting
- `ExpiredToken` / `Unable to locate credentials`: run `aws login` again.
- `Could not connect to AWS stack`: wrong region, or the stack is not deployed (`cdk deploy` first).
- `AccessDeniedException`: you are not signed in as `patos-dev`, or the policy was not attached.
- `ProvisionedThroughputExceededException` in the sync line: slow uploads with `--aws-interval 30`.
- Anything else: copy the error text (not any keys) and ask.
