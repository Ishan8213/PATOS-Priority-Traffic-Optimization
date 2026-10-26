g#!/usr/bin/env python3
"""Start the local PATOS demo (no AWS needed):  python run_local.py  ->  http://127.0.0.1:8000"""
import argparse
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from local.server import create_server  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-sim", action="store_true", help="start with the sensor simulator paused")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--aws", metavar="STACK", help="mirror audit + sensor data to the hybrid AWS stack, e.g. PatosHybridDemo")
    ap.add_argument("--region", help="AWS region (default: from your AWS CLI configuration)")
    ap.add_argument("--aws-interval", type=float, default=15.0, help="seconds between sensor uploads (default 15)")
    ap.add_argument("--aws-max-batches", type=int, default=120, help="stop uploading sensor data after this many batches (default 120)")
    args = ap.parse_args()
    aws = None
    if args.aws:
        try:
            from local.aws_sync import AwsSync
            aws = AwsSync.from_stack(args.aws, args.region, interval_s=args.aws_interval, max_batches=args.aws_max_batches)
        except ImportError:
            sys.exit("boto3 is not installed. Run: python -m pip install -r requirements-aws.txt")
        except Exception as e:
            sys.exit(f"Could not connect to AWS stack {args.aws!r}: {type(e).__name__}: {e}\nCheck `aws sts get-caller-identity`, the region, and that the stack is deployed.")
        print(f"AWS sync ON: stack {args.aws}, region {aws.region}, sensor upload every {args.aws_interval:g}s, max {args.aws_max_batches} batches")
    httpd, engine = create_server(args.port, simulate=not args.no_sim, aws=aws)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"PATOS local demo running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        engine.stop()
        httpd.server_close()


if __name__ == "__main__":
    main()
