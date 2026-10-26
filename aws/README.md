# PATOS AWS demo

This repository can run its video pipeline on an EC2 Linux instance. The
pipeline performs inference locally on that instance; optional integrations
send the resulting telemetry to S3 and AWS IoT Core. This is a demonstration
setup, not a production service or a real traffic-signal controller.

No AWS resources are created by the code. S3 and IoT Core publishing are
disabled unless their configuration is supplied. The PostgreSQL-compatible
schema and generated SQL under `data/sql_ready/` are local artifacts; there is
no RDS connection or database insert implementation.

## Before starting

- An AWS account and a region in which you intend to run the demo.
- An Ubuntu EC2 instance with enough memory and CPU for YOLO inference. CPU
  inference can be slow; GPU instance types usually cost more.
- The input video and YOLO model file. Both are ignored by Git in this
  repository, so make sure to transfer them to the instance separately.
- A clone or copy of this repository containing the AWS integration files and
  your project changes.

AWS service prices, free-tier availability, and data-transfer charges depend
on account, region, and usage. Check current AWS pricing before creating
resources. Stop or terminate the EC2 instance when not using it, and remove
resources you no longer need.

## 1. Create and prepare the EC2 instance

In the AWS Console, launch an Ubuntu 24.04 EC2 instance in your chosen region.
For an initial CPU-only demo, use a general-purpose instance with enough
memory for PyTorch/YOLO; expect slower processing than on a GPU. Attach an
instance profile/IAM role instead of placing AWS access keys on the machine.

Keep the security group closed to inbound traffic unless you have a specific
need. The pipeline needs outbound HTTPS for S3 and outbound TLS on port 8883
for AWS IoT Core when those integrations are enabled.

Connect to the instance using your normal secure EC2 access method, then from
the repository directory:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The dependency file includes the vision/model dependencies, dashboard
dependency, AWS SDK, and MQTT client. Installing PyTorch/YOLO dependencies
downloads large packages and can take several minutes.

Transfer the video to `data/traffic.mp4` and model to `yolov8n.pt` in the
repository root, or set `PATOS_VIDEO_PATH` and `PATOS_YOLO_MODEL_PATH` to
their locations. Paths that are not absolute are resolved from the repository
root. Ensure your account is authorized to use the model and video.

## 2. Run locally on the instance (no AWS destinations)

The pipeline runs the video step headlessly by default on Linux without a
display. It preserves the windowed video view on Windows or when a display is
available; set `PATOS_DISPLAY_VIDEO=false` to force headless processing or
`PATOS_DISPLAY_VIDEO=true` to explicitly request a display.

```bash
source .venv/bin/activate
export PATOS_DISPLAY_VIDEO=false
python run_pipeline.py
```

The script prints errors and exits unsuccessfully if a required step fails.
Successful local processing writes JSON results to `data/`, and SQL-ready
files to `data/sql_ready/`. The local dashboard can be run separately from the
repository root with `streamlit run dashboard/app.py`. Do not expose the
dashboard publicly without adding appropriate authentication and network
controls.

## 3. Optional: upload telemetry to S3

Create a private S3 bucket in the same region. Keep S3 Block Public Access
enabled. Attach a least-privilege policy to the EC2 instance role allowing
`s3:PutObject` only on the bucket/prefix used for telemetry (by default,
`arn:aws:s3:::YOUR_BUCKET/traffic/*`). The pipeline does not need bucket-wide
listing or read access.

Set the bucket and region before running:

```bash
export AWS_REGION=us-east-1
export PATOS_S3_BUCKET=your-private-bucket-name
export PATOS_S3_OBJECT_KEY=traffic/traffic_telemetry.json
python run_pipeline.py
```

Without `PATOS_S3_BUCKET`, the script still prepares the local telemetry JSON
but skips the S3 upload. AWS SDK credentials are obtained from the standard
credential chain; on EC2, use the attached instance role.

## 4. Optional: publish telemetry to AWS IoT Core

In AWS IoT Core, create a Thing and activate a device certificate. Attach an
IoT policy restricted to the demo client ID and topic. The policy needs
`iot:Connect` for that client ID and `iot:Publish` for the selected topic; it
does not need subscribe/receive permissions for this publisher.

Download the certificate, private key, and Amazon Root CA to a protected
location on the instance. Do not put private keys in Git, the source bundle,
or chat. The repository `.gitignore` excludes PEM/key files, but that is not
a substitute for secure storage and file permissions.

Configure paths and the AWS IoT endpoint shown for your account:

```bash
export AWS_REGION=us-east-1
export PATOS_IOT_ENDPOINT=your-endpoint-ats.iot.us-east-1.amazonaws.com
export PATOS_IOT_CERTIFICATE=/secure/path/device-certificate.pem.crt
export PATOS_IOT_PRIVATE_KEY=/secure/path/device-private.pem.key
export PATOS_IOT_ROOT_CA=/secure/path/AmazonRootCA1.pem
export PATOS_IOT_TOPIC=patos/traffic/telemetry
export PATOS_DEVICE_ID=EdgeDevice01
python run_pipeline.py
```

IoT Core MQTT uses mutual TLS on port 8883. Ensure outbound access is allowed.
Without the endpoint, certificate, and private key, the script reports that
publishing was skipped.

## What this demo does not do

- It does not provision EC2, S3, IoT Core, or RDS resources.
- It does not connect to RDS or execute the generated SQL.
- It does not stream live roadside camera input; it processes a local video
  file.
- The congestion model inputs include prototype values, and priority
  decisions use `priority/priority_request.json`.
- It does not actuate real traffic lights or implement production
  authentication, monitoring, retries, or deployment automation.

Treat outputs as demo data only. Review the relevant AWS service charges and
delete any resources that are no longer needed after the demonstration.
